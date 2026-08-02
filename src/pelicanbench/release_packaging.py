"""Deterministic, evidence-rich release packaging for PelicanBench."""

from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .assurance import evaluate_release_readiness
from .candidate import validate_candidate
from .ecosystem import audit_ecosystem, load_ecosystem_registry
from .io import content_hash, read_json, write_json, write_jsonl
from .pilot import load_tasks
from .publication import build_publication_bundle
from .prospective import ProspectivePilotPlan, build_prospective_pilot_plan
from .release_records import PackagedArtifact, ReleasePackageReceipt
from .release_manifest import build_release_manifest
from .timeutil import utc_now_iso
from .verification import (
    build_repository_verification_receipt,
    validate_repository_verification_receipt,
)


def _run(root: Path, *args: str) -> str:
    completed = subprocess.run(
        list(args),
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _epoch() -> int:
    return int(os.environ.get("SOURCE_DATE_EPOCH", "1785628800"))


def _zip_datetime() -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(max(_epoch(), 315532800), tz=timezone.utc)
    # ZIP timestamps have two-second resolution.
    return value.year, value.month, value.day, value.hour, value.minute, value.second // 2 * 2


def _tracked_paths(root: Path) -> list[Path]:
    output = _run(root, "git", "ls-files", "-z")
    return [root / value for value in output.split("\0") if value]


def _history_paths(root: Path) -> list[Path]:
    values = _tracked_paths(root)
    values.extend(path for path in (root / ".git").rglob("*") if path.is_file() or path.is_symlink())
    return sorted(set(values), key=lambda path: path.relative_to(root).as_posix())


def _archive_bytes(path: Path) -> bytes:
    if path.is_symlink():
        return os.readlink(path).encode("utf-8")
    return path.read_bytes()


def _archive_path(project: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project / path
    # ``absolute`` deliberately avoids resolving symlinks: archive identity must
    # preserve the tracked link rather than silently embedding its target.
    path = path.absolute()
    path.relative_to(project)
    return path


def create_deterministic_zip(
    root: str | Path,
    output: str | Path,
    paths: Iterable[str | Path],
    *,
    prefix: str,
) -> Path:
    project = Path(root).resolve()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _zip_datetime()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive_paths = sorted(
            (_archive_path(project, item) for item in paths),
            key=lambda item: item.relative_to(project).as_posix(),
        )
        for value in archive_paths:
            relative = value.relative_to(project).as_posix()
            info = zipfile.ZipInfo(f"{prefix.rstrip('/')}/{relative}", date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o120777 if value.is_symlink() else stat.S_IMODE(value.stat().st_mode)
            info.external_attr = (mode & 0xFFFF) << 16
            if value.is_symlink():
                info.create_system = 3
            archive.writestr(info, _archive_bytes(value))
    return destination


def create_deterministic_tar_gz(
    root: str | Path,
    output: str | Path,
    paths: Iterable[str | Path],
    *,
    prefix: str,
) -> Path:
    project = Path(root).resolve()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    epoch = _epoch()
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                archive_paths = sorted(
                    (_archive_path(project, item) for item in paths),
                    key=lambda item: item.relative_to(project).as_posix(),
                )
                for value in archive_paths:
                    relative = value.relative_to(project).as_posix()
                    info = archive.gettarinfo(value, arcname=f"{prefix.rstrip('/')}/{relative}")
                    info.mtime = epoch
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    if value.is_symlink():
                        archive.addfile(info)
                    else:
                        with value.open("rb") as handle:
                            archive.addfile(info, handle)
    return destination


def _record(directory: Path, path: Path, role: str) -> PackagedArtifact:
    return PackagedArtifact(
        path=path.relative_to(directory).as_posix(),
        sha256=_sha256(path),
        size_bytes=path.stat().st_size,
        role=role,
    )


def _copy_evidence(project: Path, destination: Path, relative: str) -> Path | None:
    source = project / relative
    if not source.is_file():
        return None
    target = destination / Path(relative).name
    shutil.copy2(source, target)
    return target


def _build_release_pilot_plan(project: Path) -> ProspectivePilotPlan:
    tasks = load_tasks(project / "benchmark/tasks/v1-candidate.jsonl")
    panel = read_json(project / "benchmark/models/prospective-panel.json")
    commitment = read_json(project / "benchmark/tasks/v1-candidate-commitment.json")
    return build_prospective_pilot_plan(
        tasks,
        panel,
        task_identity_commitment=str(commitment["commitment"]),
        replicates=3,
        base_seed=20260802,
    )


def _write_release_pilot_plan(
    plan: ProspectivePilotPlan,
    output: Path,
) -> tuple[Path, Path]:
    write_json(output, plan.summary())
    cells = output.with_name(output.stem + "-cells.jsonl")
    write_jsonl(cells, [item.as_dict() for item in plan.cells])
    return output, cells


def build_release_package(
    root: str | Path,
    output_directory: str | Path,
    *,
    version: str,
    tag: str,
    profile: str = "v0.4-alpha",
    clean_clone_receipt: str | Path = "artifacts/clean-clone-receipt.json",
    overwrite: bool = False,
) -> ReleasePackageReceipt:
    project = Path(root).resolve()
    output = Path(output_directory).resolve()
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise FileExistsError(f"release destination is not empty: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    status = _run(project, "git", "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise RuntimeError("release packaging requires a clean Git working tree")
    commit = _run(project, "git", "rev-parse", "HEAD")
    tree = _run(project, "git", "rev-parse", "HEAD^{tree}")
    tag_commit = _run(project, "git", "rev-list", "-n", "1", tag)
    if tag_commit != commit:
        raise RuntimeError(f"tag {tag} does not point at HEAD")
    readiness = evaluate_release_readiness(project, profile=profile)
    if not readiness.ready:
        raise RuntimeError(f"release profile is not ready: {profile}")

    prefix = f"pelican-bench-{version}"
    tracked = _tracked_paths(project)
    history = _history_paths(project)
    source_zip = create_deterministic_zip(project, output / f"{prefix}-source.zip", tracked, prefix=prefix)
    source_tar = create_deterministic_tar_gz(project, output / f"{prefix}-source.tar.gz", tracked, prefix=prefix)
    history_zip = create_deterministic_zip(project, output / f"{prefix}-with-git.zip", history, prefix=prefix)
    history_tar = create_deterministic_tar_gz(project, output / f"{prefix}-with-git.tar.gz", history, prefix=prefix)
    bundle = output / f"{prefix}.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=project, check=True)
    subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        cwd=project,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    ecosystem_path = output / "ecosystem-audit.json"
    ecosystem = audit_ecosystem(
        project,
        load_ecosystem_registry(project / "benchmark/integrations/ecosystem-registry.json"),
    )
    write_json(ecosystem_path, ecosystem.as_dict())

    pilot_path = output / "v1-candidate-execution-plan.json"
    pilot = _build_release_pilot_plan(project)
    _, pilot_cells_path = _write_release_pilot_plan(pilot, pilot_path)

    candidate_validation_path = output / "v1-candidate-validation.json"
    candidate_validation = validate_candidate(project)
    if not candidate_validation.passed:
        raise RuntimeError("candidate benchmark validation failed during release packaging")
    write_json(candidate_validation_path, candidate_validation.as_dict())

    evidence_directory = output / "evidence"
    evidence_directory.mkdir(parents=True, exist_ok=True)
    evidence_files: list[Path] = []
    for relative in (
        "artifacts/scorer-challenge-report.json",
        "artifacts/svg-fuzz-report.json",
        "artifacts/renderer-bridge.json",
        "artifacts/quality-gate.json",
        "artifacts/test-taxonomy.json",
        "artifacts/mutation-smoke.json",
        "artifacts/static-audit.json",
        "artifacts/prose-audit.json",
        "artifacts/toolchain-preflight.json",
        "coverage.xml",
        "benchmark/evidence/snapshots/castillo-2026-empirical-nlp-report.json",
        "benchmark/evidence/snapshots/castillo-2026-design-coverage.json",
        "benchmark/evidence/snapshots/model-qualification-plan.json",
        "benchmark/evidence/snapshots/judge-qualification-plan.json",
        "benchmark/human-calibration/study-spec.json",
    ):
        copied = _copy_evidence(project, evidence_directory, relative)
        if copied is not None:
            evidence_files.append(copied)

    clean_source = Path(clean_clone_receipt)
    if not clean_source.is_absolute():
        clean_source = project / clean_source
    if not clean_source.is_file():
        raise FileNotFoundError(clean_source)
    clean_target = output / "clean-clone-receipt.json"
    shutil.copy2(clean_source, clean_target)
    clean_value = read_json(clean_target)

    # Build the publication hand-off before the release manifest so its content hash is
    # included as release evidence.
    publication_directory = output / "publication-bundle"
    publication = build_publication_bundle(
        project,
        publication_directory,
        include_artifacts=tuple(evidence_files) + (clean_target,),
    )
    publication_paths = [path for path in publication_directory.rglob("*") if path.is_file()]
    publication_zip = create_deterministic_zip(
        publication_directory,
        output / f"{prefix}-publication-bundle.zip",
        publication_paths,
        prefix=f"{prefix}-publication-bundle",
    )

    # Generate the dependency-aware SBOM through the repository's single source of truth.
    sbom_path = output / f"{prefix}.spdx.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(project / "src")
    subprocess.run(
        [sys.executable, "scripts/generate_sbom.py", "--output", str(sbom_path)],
        cwd=project,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    manifest_path = output / "release-manifest.json"
    manifest = build_release_manifest(
        project,
        profile=profile,
        tag=tag,
        artifacts=(
            sbom_path,
            ecosystem_path,
            candidate_validation_path,
            pilot_path,
            pilot_cells_path,
            publication_zip,
            clean_target,
            *evidence_files,
        ),
    )
    write_json(manifest_path, manifest)

    verification_path = output / "repository-verification-receipt.json"
    receipt = build_repository_verification_receipt(
        project,
        profile=profile,
        revision=commit,
        coverage_path=project / "coverage.xml",
        artifact_paths=(
            manifest_path,
            sbom_path,
            ecosystem_path,
            publication_zip,
            clean_target,
            *evidence_files,
        ),
    )
    validate_repository_verification_receipt(
        receipt,
        project / "benchmark/schemas/repository-verification-receipt.schema.json",
    )
    write_json(verification_path, receipt.model_dump(mode="json", exclude_none=True))

    artifacts = (
        _record(output, source_zip, "source-archive"),
        _record(output, source_tar, "source-archive"),
        _record(output, history_zip, "full-history-archive"),
        _record(output, history_tar, "full-history-archive"),
        _record(output, bundle, "git-bundle"),
        _record(output, publication_zip, "publication-bundle"),
        _record(output, sbom_path, "sbom"),
        _record(output, manifest_path, "release-manifest"),
        _record(output, verification_path, "verification-receipt"),
        _record(output, ecosystem_path, "ecosystem-audit"),
        _record(output, candidate_validation_path, "candidate-validation"),
        _record(output, pilot_path, "prospective-pilot-plan"),
        _record(output, pilot_cells_path, "prospective-pilot-cells"),
        _record(output, clean_target, "clean-clone-receipt"),
        *tuple(_record(output, item, "validation-evidence") for item in evidence_files),
    )
    package_hash = content_hash([item.model_dump(mode="json") for item in artifacts])
    qa = ReleasePackageReceipt(
        generated_at=utc_now_iso(),
        version=version,
        profile=profile,
        tag=tag,
        commit=commit,
        tree=tree,
        git_clean=True,
        tag_points_at_head=True,
        assurance_ready=True,
        ecosystem_audit_passed=ecosystem.passed,
        verification_result=receipt.result,
        clean_clone_result=str(clean_value.get("harness_result", "unknown")),
        pilot_cells=pilot.cell_count,
        pilot_ready_cells=pilot.ready_cell_count,
        pilot_qualification_required_cells=pilot.qualification_required_cell_count,
        publication_bundle_hash=publication.bundle_hash,
        external_writes_executed=publication.external_writes_executed,
        artifacts=tuple(artifacts),
        package_hash=package_hash,
        limitations=(
            "No GitHub or Hugging Face remote write is implied by local packaging.",
            "The clean-clone verification used the same execution environment and remains E2 evidence.",
            (
                "First-party candidate models remain qualification-required "
                "and no prospective benchmark result is included."
            ),
            "No human participant data have been collected.",
        ),
    )
    qa_path = output / "release-qa-receipt.json"
    write_json(qa_path, qa.model_dump(mode="json"))

    checksum_paths = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (output / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(path)}  {path.relative_to(output).as_posix()}" for path in checksum_paths)
        + "\n",
        encoding="utf-8",
    )
    return qa
