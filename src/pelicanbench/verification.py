"""Repository-standards compatible verification receipts.

The receipt is an evidence summary, not a substitute for the underlying logs.  It uses the
v1 schema maintained in ``edithatogo/repository-standards`` and records skipped checks
rather than turning unavailable tools into false passes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field

from .assurance import evaluate_release_readiness
from .ecosystem import audit_ecosystem, load_ecosystem_registry
from .io import read_json
from .timeutil import utc_now_iso
from .validation import validate_repository

CheckResult = Literal["pass", "fail", "skip"]
ReceiptResult = Literal["pass", "fail", "partial"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VerificationCheck(StrictModel):
    name: str = Field(min_length=1)
    result: CheckResult
    duration_seconds: float | None = Field(default=None, ge=0)
    evidence: str | None = None
    reason: str | None = None


class VerificationArtifact(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class VerificationQualityMetrics(StrictModel):
    line_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    branch_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    patch_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    mutation_score_percent: float | None = Field(default=None, ge=0, le=100)
    property_examples: int | None = Field(default=None, ge=0)
    metamorphic_relations: int | None = Field(default=None, ge=0)
    deterministic_simulation_scenarios: int | None = Field(default=None, ge=0)
    contract_tests: int | None = Field(default=None, ge=0)
    quarantined_tests: int | None = Field(default=None, ge=0)
    oldest_quarantine_days: int | None = Field(default=None, ge=0)
    benchmark_regressions: int | None = Field(default=None, ge=0)


class RepositoryVerificationReceipt(StrictModel):
    schema_version: Literal[1] = 1
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    revision: str = Field(min_length=7)
    generated_at: str
    seed: int | str | None = None
    result: ReceiptResult
    checks: tuple[VerificationCheck, ...] = Field(min_length=1)
    artifacts: tuple[VerificationArtifact, ...] = ()
    quality_metrics: VerificationQualityMetrics | None = None


def _git_revision(root: Path) -> str:
    completed = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and len(value) >= 7 else "working-tree"


def _plain_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(root: Path, path: Path) -> VerificationArtifact:
    resolved = path if path.is_absolute() else root / path
    try:
        display = resolved.relative_to(root).as_posix()
    except ValueError:
        display = resolved.name
    return VerificationArtifact(path=display, sha256=_plain_sha256(resolved))


def coverage_metrics(path: str | Path) -> VerificationQualityMetrics:
    root = ET.parse(Path(path)).getroot()  # nosec B314
    line_rate = float(root.attrib.get("line-rate", "0")) * 100
    branch_rate = float(root.attrib.get("branch-rate", "0")) * 100
    return VerificationQualityMetrics(
        line_coverage_percent=round(line_rate, 4),
        branch_coverage_percent=round(branch_rate, 4),
    )


def _json_boolean_check(
    path: Path,
    *,
    name: str,
    field: str,
    missing_reason: str,
) -> VerificationCheck:
    if not path.exists():
        return VerificationCheck(name=name, result="skip", reason=missing_reason)
    raw_data = read_json(path)
    if isinstance(raw_data, dict):
        raw_dict: dict[str, Any] = cast("dict[str, Any]", raw_data)
        passed = bool(raw_dict.get(field))
    else:
        passed = False
    return VerificationCheck(
        name=name,
        result="pass" if passed else "fail",
        evidence=path.as_posix(),
        reason=None if passed else f"{field} was false or missing",
    )


def build_repository_verification_receipt(
    root: str | Path,
    *,
    profile: str = "v0.4-alpha",
    repository: str = "edithatogo/pelican-bench",
    revision: str | None = None,
    seed: int | str | None = 20260801,
    artifact_paths: tuple[str | Path, ...] = (),
    coverage_path: str | Path = "coverage.xml",
) -> RepositoryVerificationReceipt:
    project = Path(root).resolve()
    checks: list[VerificationCheck] = []

    findings = validate_repository(project)
    checks.append(
        VerificationCheck(
            name="repository-contract",
            result="pass" if not findings else "fail",
            evidence="scripts/validate_repo.py",
            reason=None if not findings else f"{len(findings)} validation finding(s)",
        )
    )

    readiness = evaluate_release_readiness(project, profile=profile)
    checks.append(
        VerificationCheck(
            name=f"release-readiness:{profile}",
            result="pass" if readiness.ready else "fail",
            evidence="benchmark/assurance-case.json",
            reason=None if readiness.ready else "assurance profile is not ready",
        )
    )

    registry_path = project / "benchmark/integrations/ecosystem-registry.json"
    if registry_path.exists():
        ecosystem = audit_ecosystem(project, load_ecosystem_registry(registry_path))
        checks.append(
            VerificationCheck(
                name="ecosystem-integration-contract",
                result="pass" if ecosystem.passed else "fail",
                evidence="benchmark/integrations/ecosystem-registry.json",
                reason=None if ecosystem.passed else "integration evidence errors were found",
            )
        )
    else:
        checks.append(
            VerificationCheck(
                name="ecosystem-integration-contract",
                result="skip",
                reason="ecosystem registry is absent",
            )
        )

    coverage_file = Path(coverage_path)
    if not coverage_file.is_absolute():
        coverage_file = project / coverage_file
    quality: VerificationQualityMetrics | None = None
    if coverage_file.exists():
        quality = coverage_metrics(coverage_file)
        coverage_passed = (quality.line_coverage_percent or 0) >= 90
        try:
            coverage_evidence = coverage_file.relative_to(project).as_posix()
        except ValueError:
            coverage_evidence = coverage_file.as_posix()
        checks.append(
            VerificationCheck(
                name="python-coverage-threshold",
                result="pass" if coverage_passed else "fail",
                evidence=coverage_evidence,
                reason=None if coverage_passed else "line coverage is below 90 percent",
            )
        )
    else:
        checks.append(
            VerificationCheck(
                name="python-coverage-threshold",
                result="skip",
                reason="coverage.xml has not been generated",
            )
        )

    checks.extend(
        [
            _json_boolean_check(
                project / "artifacts/scorer-challenge-report.json",
                name="scorer-metamorphic-challenges",
                field="passed",
                missing_reason="scorer challenge report has not been generated",
            ),
            _json_boolean_check(
                project / "artifacts/svg-fuzz-report.json",
                name="bounded-svg-fuzzing",
                field="passed",
                missing_reason="SVG fuzz report has not been generated",
            ),
        ]
    )

    artifacts: list[VerificationArtifact] = []
    candidates = [Path(value) for value in artifact_paths]
    if coverage_file.exists():
        candidates.append(coverage_file)
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate if candidate.is_absolute() else project / candidate
        resolved = resolved.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        artifacts.append(_artifact(project, resolved))

    results = {item.result for item in checks}
    overall: ReceiptResult
    if "fail" in results:
        overall = "fail"
    elif "skip" in results:
        overall = "partial"
    else:
        overall = "pass"

    return RepositoryVerificationReceipt(
        repository=repository,
        revision=revision or _git_revision(project),
        generated_at=utc_now_iso(),
        seed=seed,
        result=overall,
        checks=tuple(checks),
        artifacts=tuple(sorted(artifacts, key=lambda item: item.path)),
        quality_metrics=quality,
    )


def validate_repository_verification_receipt(
    receipt: RepositoryVerificationReceipt | dict[str, object],
    schema_path: str | Path,
) -> None:
    value = (
        receipt.model_dump(mode="json", exclude_none=True)
        if isinstance(receipt, RepositoryVerificationReceipt)
        else receipt
    )
    schema = cast("dict[str, Any]", json.loads(Path(schema_path).read_text(encoding="utf-8")))
    Draft202012Validator(schema, format_checker=None).validate(value)  # pyright: ignore[reportUnknownMemberType]
