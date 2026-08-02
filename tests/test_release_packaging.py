from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pelicanbench.release_packaging import (
    create_deterministic_tar_gz,
    create_deterministic_zip,
)
from pelicanbench.release_records import PackagedArtifact, ReleasePackageReceipt


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_deterministic_archive_helpers(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1785542400")
    root = tmp_path / "root"
    root.mkdir()
    first = root / "a.txt"
    second = root / "nested/b.txt"
    second.parent.mkdir()
    first.write_text("alpha\n", encoding="utf-8")
    second.write_text("beta\n", encoding="utf-8")
    paths = [first, second]

    zip_a = create_deterministic_zip(root, tmp_path / "a.zip", paths, prefix="bundle")
    zip_b = create_deterministic_zip(root, tmp_path / "b.zip", reversed(paths), prefix="bundle")
    tar_a = create_deterministic_tar_gz(root, tmp_path / "a.tar.gz", paths, prefix="bundle")
    tar_b = create_deterministic_tar_gz(root, tmp_path / "b.tar.gz", reversed(paths), prefix="bundle")
    assert _digest(zip_a) == _digest(zip_b)
    assert _digest(tar_a) == _digest(tar_b)


def test_release_package_receipt_schema_shape(root: Path):
    artifact = PackagedArtifact(path="a.zip", sha256="a" * 64, size_bytes=1, role="source")
    receipt = ReleasePackageReceipt(
        generated_at="2026-08-01T00:00:00Z",
        version="0.3.0-alpha.1",
        profile="v0.3-alpha",
        tag="v0.3.0-alpha.1",
        commit="b" * 40,
        tree="c" * 40,
        git_clean=True,
        tag_points_at_head=True,
        assurance_ready=True,
        ecosystem_audit_passed=True,
        verification_result="pass",
        clean_clone_result="HARNESS_OK",
        pilot_cells=297,
        pilot_ready_cells=99,
        pilot_qualification_required_cells=198,
        publication_bundle_hash="sha256:" + "d" * 64,
        artifacts=(artifact,),
        package_hash="sha256:" + "e" * 64,
        limitations=("fixture",),
    )
    schema = json.loads(
        (root / "benchmark/schemas/release-package-receipt.schema.json").read_text()
    )
    assert schema["title"] == "ReleasePackageReceipt"
    assert receipt.external_writes_executed is False


def test_archive_helpers_preserve_symlinks_and_reject_outside_paths(tmp_path: Path, monkeypatch):
    import tarfile
    import zipfile

    from pelicanbench.release_packaging import _archive_path

    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    root = tmp_path / "root"
    root.mkdir()
    target = root / "target.txt"
    target.write_text("target\n", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to("target.txt")

    zip_path = create_deterministic_zip(root, tmp_path / "links.zip", [link], prefix="bundle")
    with zipfile.ZipFile(zip_path) as archive:
        info = archive.getinfo("bundle/link.txt")
        assert info.create_system == 3
        assert archive.read(info) == b"target.txt"
        assert info.compress_type == zipfile.ZIP_DEFLATED

    tar_path = create_deterministic_tar_gz(root, tmp_path / "links.tar.gz", [link], prefix="bundle")
    with tarfile.open(tar_path, "r:gz") as archive:
        info = archive.getmember("bundle/link.txt")
        assert info.issym()
        assert info.linkname == "target.txt"

    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        _archive_path(root.resolve(), outside)
    except ValueError:
        pass
    else:  # pragma: no cover - assertion guard
        raise AssertionError("outside paths must be rejected")


def test_history_paths_and_copy_evidence(tmp_path: Path, monkeypatch):
    from pelicanbench import release_packaging as rp

    root = tmp_path / "repo"
    root.mkdir()
    tracked = root / "tracked.txt"
    tracked.write_text("tracked", encoding="utf-8")
    git_file = root / ".git/objects/aa/object"
    git_file.parent.mkdir(parents=True)
    git_file.write_text("object", encoding="utf-8")
    monkeypatch.setattr(rp, "_tracked_paths", lambda _root: [tracked])
    assert rp._history_paths(root) == [git_file, tracked]

    destination = tmp_path / "evidence"
    destination.mkdir()
    copied = rp._copy_evidence(root, destination, "tracked.txt")
    assert copied is not None and copied.read_text(encoding="utf-8") == "tracked"
    assert rp._copy_evidence(root, destination, "absent.json") is None


def test_release_package_guards(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    import pytest

    from pelicanbench import release_packaging as rp

    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "delivery"
    output.mkdir()
    (output / "existing").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        rp.build_release_package(root, output, version="x", tag="vX")

    output = tmp_path / "empty"
    monkeypatch.setattr(rp, "_run", lambda _root, *args: "dirty" if args[1] == "status" else "")
    with pytest.raises(RuntimeError, match="clean Git"):
        rp.build_release_package(root, output, version="x", tag="vX")

    def mismatch(_root: Path, *args: str) -> str:
        command = " ".join(args)
        if "status" in command:
            return ""
        if "HEAD^{tree}" in command:
            return "b" * 40
        if "rev-list" in command:
            return "c" * 40
        return "a" * 40

    monkeypatch.setattr(rp, "_run", mismatch)
    with pytest.raises(RuntimeError, match="does not point at HEAD"):
        rp.build_release_package(root, output, version="x", tag="vX")

    def clean(_root: Path, *args: str) -> str:
        command = " ".join(args)
        if "status" in command:
            return ""
        if "HEAD^{tree}" in command:
            return "b" * 40
        return "a" * 40

    monkeypatch.setattr(rp, "_run", clean)
    monkeypatch.setattr(rp, "evaluate_release_readiness", lambda *_args, **_kwargs: SimpleNamespace(ready=False))
    with pytest.raises(RuntimeError, match="not ready"):
        rp.build_release_package(root, output, version="x", tag="vX")


def test_build_release_package_happy_path(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    from pelicanbench import release_packaging as rp
    from pelicanbench.verification import RepositoryVerificationReceipt, VerificationCheck

    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1785542400")
    root = tmp_path / "repo"
    root.mkdir()
    tracked = root / "README.md"
    tracked.write_text("# fixture\n", encoding="utf-8")
    link = root / "README-link.md"
    link.symlink_to("README.md")
    git_marker = root / ".git/objects/fixture"
    git_marker.parent.mkdir(parents=True)
    git_marker.write_text("history", encoding="utf-8")
    artifacts = root / "artifacts"
    artifacts.mkdir()
    (artifacts / "scorer-challenge-report.json").write_text('{"passed":true}\n', encoding="utf-8")
    # Leave the fuzz report absent to exercise optional evidence handling.
    (artifacts / "renderer-bridge.json").write_text('{"passed":true}\n', encoding="utf-8")
    clean_receipt = artifacts / "clean-clone-receipt.json"
    clean_receipt.write_text('{"harness_result":"HARNESS_OK"}\n', encoding="utf-8")
    (root / "coverage.xml").write_text(
        '<?xml version="1.0"?><coverage line-rate="0.95" branch-rate="0.91"/>',
        encoding="utf-8",
    )

    commit = "a" * 40
    tree = "b" * 40

    def fake_run(_root: Path, *args: str) -> str:
        command = " ".join(args)
        if "status" in command:
            return ""
        if "HEAD^{tree}" in command:
            return tree
        return commit

    monkeypatch.setattr(rp, "_run", fake_run)
    monkeypatch.setattr(rp, "_tracked_paths", lambda _root: [tracked, link])
    monkeypatch.setattr(rp, "_history_paths", lambda _root: [tracked, link, git_marker])
    monkeypatch.setattr(
        rp,
        "evaluate_release_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(rp, "load_ecosystem_registry", lambda _path: object())

    class DummyEcosystem:
        passed = True

        @staticmethod
        def as_dict() -> dict[str, object]:
            return {"passed": True, "asset_count": 1}

    monkeypatch.setattr(rp, "audit_ecosystem", lambda *_args, **_kwargs: DummyEcosystem())
    pilot = SimpleNamespace(
        cell_count=3,
        ready_cell_count=1,
        qualification_required_cell_count=2,
    )
    monkeypatch.setattr(rp, "_build_release_pilot_plan", lambda _root: pilot)

    def write_pilot(_plan: object, output: Path):
        rp.write_json(output, {"cell_count": 3})
        cells = output.with_name(output.stem + "-cells.jsonl")
        cells.write_text('{"cell_id":"cell:fixture"}\n', encoding="utf-8")
        return output, cells

    monkeypatch.setattr(rp, "_write_release_pilot_plan", write_pilot)
    candidate_report = SimpleNamespace(passed=True, as_dict=lambda: {"passed": True})
    monkeypatch.setattr(rp, "validate_candidate", lambda _root: candidate_report)

    publication_hash = "sha256:" + "d" * 64

    def build_publication(_root: Path, destination: Path, *, include_artifacts: tuple[Path, ...]):
        destination.mkdir(parents=True)
        (destination / "README.md").write_text("publication\n", encoding="utf-8")
        (destination / "inputs.json").write_text(
            json.dumps([path.name for path in include_artifacts]) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(bundle_hash=publication_hash, external_writes_executed=False)

    monkeypatch.setattr(rp, "build_publication_bundle", build_publication)

    def fake_subprocess_run(args, **kwargs):
        if args[:3] == ["git", "bundle", "create"]:
            Path(args[3]).write_bytes(b"bundle")
        elif len(args) >= 2 and args[1] == "scripts/generate_sbom.py":
            output_arg = Path(args[args.index("--output") + 1])
            output_arg.write_text('{"spdxVersion":"SPDX-2.3"}\n', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(rp.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(
        rp,
        "build_release_manifest",
        lambda *_args, **_kwargs: {"schema_version": "fixture", "profile": "v0.3-alpha"},
    )
    verification = RepositoryVerificationReceipt(
        repository="edithatogo/pelican-bench",
        revision=commit,
        generated_at="2026-08-01T00:00:00Z",
        result="pass",
        checks=(VerificationCheck(name="fixture", result="pass"),),
    )
    monkeypatch.setattr(rp, "build_repository_verification_receipt", lambda *_args, **_kwargs: verification)
    monkeypatch.setattr(rp, "validate_repository_verification_receipt", lambda *_args, **_kwargs: None)

    output = tmp_path / "delivery"
    output.mkdir()
    (output / "stale").write_text("replace me", encoding="utf-8")
    receipt = rp.build_release_package(
        root,
        output,
        version="0.3.0-alpha.1",
        tag="v0.3.0-alpha.1",
        clean_clone_receipt=clean_receipt,
        overwrite=True,
    )

    assert receipt.commit == commit
    assert receipt.tree == tree
    assert receipt.clean_clone_result == "HARNESS_OK"
    assert receipt.pilot_cells == 3
    assert receipt.publication_bundle_hash == publication_hash
    assert receipt.external_writes_executed is False
    assert (output / "release-qa-receipt.json").is_file()
    assert (output / "SHA256SUMS").is_file()
    assert (output / "pelican-bench-0.3.0-alpha.1.bundle").read_bytes() == b"bundle"
    assert "release-qa-receipt.json" in (output / "SHA256SUMS").read_text(encoding="utf-8")
