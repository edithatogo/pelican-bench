"""Repository contract validation used by local and CI harnesses."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from .assurance import EVIDENCE_ORDER, evaluate_release_readiness
from .candidate import validate_candidate
from .conductor_docs import generated_documents
from .ecosystem import EcosystemRegistry, audit_ecosystem, load_ecosystem_registry
from .interoperability import (
    OntologyInteroperabilityProfile,
    load_ontology_interoperability_profile,
)
from .models import (
    BenchmarkTask,
    EvaluationRecord,
    HistoricalObservation,
    RunManifest,
    ScoreCard,
    SemanticAssessment,
    SourceRecord,
    TrialRecord,
)
from .ontology import Ontology, evaluate_competency_cases
from .pilot import PilotExecutionPlan
from .publication import PublicationBundleManifest, PublicationPlan, default_publication_plan
from .release_records import ReleasePackageReceipt
from .registry import RuntimeProfileRegistry, load_registry, load_runtime_profiles, runtime_profile_for_model
from .taskgen import load_grammar, task_set_commitment
from .workgraph import build_issue_manifest


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    path: str | None = None


REQUIRED_PATHS = (
    "README.md",
    "pyproject.toml",
    "constraints/reference-environment.txt",
    "conductor/index.md",
    "conductor/product.md",
    "conductor/tech-stack.md",
    "conductor/workflow.md",
    "conductor/tracks.md",
    "conductor/status.md",
    "conductor/release-blockers.json",
    ".agents/plugins/conductor/plugin.json",
    ".agents/skills/conductor-setup/SKILL.md",
    ".entire/settings.json",
    ".github/issues/manifest.json",
    "scripts/generate_issue_manifest.py",
    "scripts/generate_conductor_docs.py",
    "scripts/generate_release_manifest.py",
    "scripts/generate_verification_receipt.py",
    "scripts/build_publication_bundle.py",
    "scripts/package_release.py",
    "scripts/verify_clean_clone.sh",
    "src/pelicanbench/release_manifest.py",
    "src/pelicanbench/conductor_docs.py",
    "src/pelicanbench/workgraph.py",
    "src/pelicanbench/metamorphic.py",
    "src/pelicanbench/fuzzing.py",
    "src/pelicanbench/calibration.py",
    "src/pelicanbench/ecosystem.py",
    "src/pelicanbench/verification.py",
    "src/pelicanbench/publication.py",
    "src/pelicanbench/release_packaging.py",
    "src/pelicanbench/release_records.py",
    "src/pelicanbench/pilot.py",
    "src/pelicanbench/interoperability.py",
    "benchmark/assurance-case.json",
    "benchmark/integrations/ecosystem-registry.json",
    "benchmark/ontologies/interoperability-profile.json",
    "benchmark/schemas/repository-verification-receipt.schema.json",
    "benchmark/schemas/release-package-receipt.schema.json",
    "hf/runtime-profiles.json",
    "benchmark/scorer-challenges/known-exploits.json",
    "benchmark/tasks/grammar.json",
    "benchmark/tasks/public-anchor.jsonl",
    "benchmark/tasks/v1-pilot-design.json",
    "benchmark/tasks/v1-pilot.jsonl",
    "benchmark/tasks/v1-pilot-commitment.json",
    "benchmark/ontology-tests/competency-cases.json",
    "docs/source-render-semantic-contract.md",
    "docs/reproducible-environments.md",
    "docs/v1-pilot-analysis-plan.md",
    "benchmark/tasks/v1-candidate-design.json",
    "benchmark/tasks/v1-candidate.jsonl",
    "benchmark/tasks/v1-candidate-canary.jsonl",
    "benchmark/tasks/v1-candidate-commitment.json",
    "benchmark/contracts/openai-compatible-chat.json",
    "benchmark/contracts/pelican-canvas-openenv.json",
    "benchmark/contracts/human-rating-exchange.json",
    "src/pelicanbench/candidate.py",
    "src/pelicanbench/empirical_nlp.py",
    "src/pelicanbench/human_study.py",
    "src/pelicanbench/qualification.py",
    "src/pelicanbench/simon_corpus.py",
    "scripts/static_audit.py",
    "scripts/prose_audit.py",
    "scripts/toolchain_preflight.py",
    "scripts/run_test_matrix.py",
    "scripts/mutation_smoke.py",
    "scripts/quality_gate.py",
    ".github/workflows/quality.yml",
    ".github/workflows/test-taxonomy.yml",
    ".github/workflows/mutation.yml",
    ".github/workflows/renovate.yml",
    "codecov.yml",
    "renovate.json",
    ".vale.ini",
)

SCHEMA_MODELS = {
    "benchmark-task.schema.json": BenchmarkTask,
    "run-manifest.schema.json": RunManifest,
    "scorecard.schema.json": ScoreCard,
    "semantic-assessment.schema.json": SemanticAssessment,
    "trial-record.schema.json": TrialRecord,
    "evaluation-record.schema.json": EvaluationRecord,
    "source-record.schema.json": SourceRecord,
    "historical-observation.schema.json": HistoricalObservation,
    "ecosystem-registry.schema.json": EcosystemRegistry,
    "runtime-profile-registry.schema.json": RuntimeProfileRegistry,
    "pilot-execution-plan.schema.json": PilotExecutionPlan,
    "publication-plan.schema.json": PublicationPlan,
    "publication-bundle-manifest.schema.json": PublicationBundleManifest,
    "release-package-receipt.schema.json": ReleasePackageReceipt,
    "ontology-interoperability-profile.schema.json": OntologyInteroperabilityProfile,
}
ALLOWED_PHASE_STATUS = {"complete", "partial", "blocked", "planned", "reopened"}
ALLOWED_BLOCKER_STATUS = ALLOWED_PHASE_STATUS


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number} must contain a JSON object")
        output.append(value)
    return output


def _check_evidence_paths(root: Path, status_text: str) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    non_paths = {
        "complete",
        "partial",
        "blocked",
        "planned",
        "reopened",
        "validated",
        "prototype",
        "contract",
    }
    for value in re.findall(r"`([^`]+)`", status_text):
        if value in non_paths or value.startswith(("http://", "https://")):
            continue
        if "/" not in value and not value.startswith(".") and Path(value).suffix == "":
            continue
        candidate = root / value
        if not candidate.exists():
            findings.append(
                ValidationFinding(
                    "error",
                    "missing-evidence",
                    f"status evidence does not exist: {value}",
                    value,
                )
            )
    return findings


def _validate_schema_snapshots(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for filename, model in SCHEMA_MODELS.items():
        path = project / "benchmark/schemas" / filename
        if not path.exists():
            findings.append(
                ValidationFinding("error", "missing-schema", filename, _relative(project, path))
            )
            continue
        actual = json.loads(path.read_text(encoding="utf-8"))
        expected = model.model_json_schema()
        if actual != expected:
            findings.append(
                ValidationFinding(
                    "error",
                    "stale-schema",
                    f"{filename} does not match the current Pydantic model",
                    _relative(project, path),
                )
            )
    return findings


def _validate_task_files(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    parsed: dict[str, list[BenchmarkTask]] = {}
    for relative in ("benchmark/tasks/public-anchor.jsonl", "benchmark/tasks/v1-pilot.jsonl"):
        path = project / relative
        if not path.exists():
            continue
        try:
            tasks = [BenchmarkTask.model_validate(value) for value in _load_jsonl(path)]
        except (TypeError, json.JSONDecodeError, ValidationError) as exc:
            findings.append(ValidationFinding("error", "invalid-task-file", str(exc), relative))
            continue
        if len({task.task_id for task in tasks}) != len(tasks):
            findings.append(
                ValidationFinding("error", "duplicate-task-id", "task IDs must be unique", relative)
            )
        parsed[relative] = tasks

    pilot = parsed.get("benchmark/tasks/v1-pilot.jsonl")
    commitment_path = project / "benchmark/tasks/v1-pilot-commitment.json"
    if pilot is not None and commitment_path.exists():
        value = _load_object(commitment_path)
        expected = task_set_commitment(pilot)
        if value.get("commitment") != expected:
            findings.append(
                ValidationFinding(
                    "error",
                    "pilot-commitment-mismatch",
                    "pilot task-set commitment does not match the current JSONL",
                    _relative(project, commitment_path),
                )
            )
        expected_counts = {
            "task_count": len(pilot),
            "scenario_count": len({task.scenario_id for task in pilot}),
            "prompt_count": len({task.prompt_id for task in pilot}),
        }
        for key, expected_count in expected_counts.items():
            if value.get(key) != expected_count:
                findings.append(
                    ValidationFinding(
                        "error",
                        "pilot-count-mismatch",
                        f"{key} should be {expected_count}",
                        _relative(project, commitment_path),
                    )
                )
    return findings


def _validate_track_graph(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    metadata_paths = sorted((project / "conductor/tracks").glob("*/metadata.json"))
    if len(metadata_paths) != 22:
        findings.append(
            ValidationFinding(
                "error",
                "track-metadata-count",
                f"expected 22 track metadata files, found {len(metadata_paths)}",
                "conductor/tracks",
            )
        )
    track_ids: set[str] = set()
    for path in metadata_paths:
        value = _load_object(path)
        track_id = str(value.get("track_id", ""))
        if not track_id or track_id in track_ids:
            findings.append(
                ValidationFinding(
                    "error",
                    "duplicate-track-id",
                    f"invalid or duplicate track ID {track_id!r}",
                    _relative(project, path),
                )
            )
        track_ids.add(track_id)
        level = str(value.get("evidence_level", ""))
        if level not in EVIDENCE_ORDER:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-evidence-level",
                    f"unknown evidence level {level!r}",
                    _relative(project, path),
                )
            )
        phase_status = value.get("phase_status", {})
        if set(phase_status) != {"P0", "P1", "P2", "P3"}:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-phase-set",
                    "phase status must contain P0 through P3",
                    _relative(project, path),
                )
            )
        for phase, status in phase_status.items():
            if status not in ALLOWED_PHASE_STATUS:
                findings.append(
                    ValidationFinding(
                        "error",
                        "invalid-phase-status",
                        f"{phase} has invalid status {status!r}",
                        _relative(project, path),
                    )
                )
        for evidence in value.get("evidence", []):
            if not (project / str(evidence)).exists():
                findings.append(
                    ValidationFinding(
                        "error",
                        "missing-track-evidence",
                        f"track evidence does not exist: {evidence}",
                        _relative(project, path),
                    )
                )

    manifest_path = project / ".github/issues/manifest.json"
    if manifest_path.exists():
        manifest = _load_object(manifest_path)
        tracks = manifest.get("tracks", [])
        if len(tracks) != 22:
            findings.append(
                ValidationFinding(
                    "error",
                    "track-count",
                    f"expected 22 tracks, found {len(tracks)}",
                    _relative(project, manifest_path),
                )
            )
        phase_count = sum(len(track.get("phases", [])) for track in tracks)
        if phase_count != 88:
            findings.append(
                ValidationFinding(
                    "error",
                    "phase-count",
                    f"expected 88 phases, found {phase_count}",
                    _relative(project, manifest_path),
                )
            )
        release_blockers = manifest.get("release_blockers", [])
        if len(release_blockers) != 5:
            findings.append(
                ValidationFinding(
                    "error",
                    "release-blocker-count",
                    f"expected 5 release blockers, found {len(release_blockers)}",
                    _relative(project, manifest_path),
                )
            )
        try:
            expected = build_issue_manifest(
                project,
                generated_at=str(manifest.get("generated_at", "")) or None,
                preserve_numbers=True,
            )
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-work-graph",
                    str(exc),
                    _relative(project, manifest_path),
                )
            )
        else:
            if manifest != expected:
                findings.append(
                    ValidationFinding(
                        "error",
                        "stale-issue-manifest",
                        "GitHub issue manifest does not match Conductor source records",
                        _relative(project, manifest_path),
                    )
                )
    return findings


def _validate_assurance(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    blockers_path = project / "conductor/release-blockers.json"
    assurance_path = project / "benchmark/assurance-case.json"
    if not blockers_path.exists() or not assurance_path.exists():
        return findings
    blockers = _load_object(blockers_path).get("blockers", [])
    blocker_ids = [str(item.get("id", "")) for item in blockers]
    if len(blocker_ids) != 5 or len(set(blocker_ids)) != 5:
        findings.append(
            ValidationFinding(
                "error",
                "invalid-release-blockers",
                "release blockers require five unique identifiers",
                _relative(project, blockers_path),
            )
        )
    known_track_ids = {
        str(_load_object(path).get("track_id", ""))
        for path in (project / "conductor/tracks").glob("*/metadata.json")
    }
    criterion_ids: set[str] = set()
    for item in blockers:
        blocker_id = str(item.get("id", ""))
        level = str(item.get("evidence_level", ""))
        status = str(item.get("status", "planned"))
        if level not in EVIDENCE_ORDER:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-blocker-evidence-level",
                    f"{blocker_id} has unknown evidence level {level!r}",
                    _relative(project, blockers_path),
                )
            )
        if status not in ALLOWED_BLOCKER_STATUS:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-blocker-status",
                    f"{blocker_id} has invalid status {status!r}",
                    _relative(project, blockers_path),
                )
            )
        unknown_tracks = set(map(str, item.get("linked_tracks", []))) - known_track_ids
        if unknown_tracks:
            findings.append(
                ValidationFinding(
                    "error",
                    "unknown-linked-track",
                    f"{blocker_id} references {sorted(unknown_tracks)}",
                    _relative(project, blockers_path),
                )
            )
        for evidence in item.get("evidence", []):
            if not (project / str(evidence)).exists():
                findings.append(
                    ValidationFinding(
                        "error",
                        "missing-blocker-evidence",
                        f"release-blocker evidence does not exist: {evidence}",
                        _relative(project, blockers_path),
                    )
                )
        criteria = item.get("closure_criteria", [])
        if not isinstance(criteria, list) or not criteria:
            findings.append(
                ValidationFinding(
                    "error",
                    "missing-blocker-criteria",
                    f"{blocker_id} requires structured closure criteria",
                    _relative(project, blockers_path),
                )
            )
            continue
        criterion_statuses: list[str] = []
        for criterion in criteria:
            if not isinstance(criterion, dict):
                findings.append(
                    ValidationFinding(
                        "error",
                        "invalid-blocker-criterion",
                        f"{blocker_id} closure criteria must be objects",
                        _relative(project, blockers_path),
                    )
                )
                continue
            criterion_id = str(criterion.get("id", ""))
            criterion_status = str(criterion.get("status", "planned"))
            criterion_statuses.append(criterion_status)
            if not criterion_id or criterion_id in criterion_ids:
                findings.append(
                    ValidationFinding(
                        "error",
                        "duplicate-blocker-criterion",
                        f"invalid or duplicate closure criterion {criterion_id!r}",
                        _relative(project, blockers_path),
                    )
                )
            criterion_ids.add(criterion_id)
            if not str(criterion.get("text", "")).strip():
                findings.append(
                    ValidationFinding(
                        "error",
                        "missing-criterion-text",
                        f"{criterion_id or blocker_id} requires criterion text",
                        _relative(project, blockers_path),
                    )
                )
            if criterion_status not in ALLOWED_BLOCKER_STATUS:
                findings.append(
                    ValidationFinding(
                        "error",
                        "invalid-criterion-status",
                        f"{criterion_id} has invalid status {criterion_status!r}",
                        _relative(project, blockers_path),
                    )
                )
            for evidence in criterion.get("evidence", []):
                if not (project / str(evidence)).exists():
                    findings.append(
                        ValidationFinding(
                            "error",
                            "missing-criterion-evidence",
                            f"criterion evidence does not exist: {evidence}",
                            _relative(project, blockers_path),
                        )
                    )
        all_complete = bool(criterion_statuses) and all(
            value == "complete" for value in criterion_statuses
        )
        any_progress = any(value in {"complete", "partial"} for value in criterion_statuses)
        if (status == "complete") != all_complete:
            findings.append(
                ValidationFinding(
                    "error",
                    "inconsistent-blocker-status",
                    f"{blocker_id} status {status!r} is inconsistent with its criteria",
                    _relative(project, blockers_path),
                )
            )
        if status == "planned" and any_progress:
            findings.append(
                ValidationFinding(
                    "error",
                    "inconsistent-planned-blocker",
                    f"{blocker_id} has completed or partial criteria but remains planned",
                    _relative(project, blockers_path),
                )
            )

    assurance = _load_object(assurance_path)
    profile_ids = set(map(str, assurance.get("release_profiles", {})))
    for item in blockers:
        unknown_profiles = set(map(str, item.get("blocks_profiles", []))) - profile_ids
        if unknown_profiles:
            findings.append(
                ValidationFinding(
                    "error",
                    "unknown-blocked-profile",
                    f"{item.get('id')} references {sorted(unknown_profiles)}",
                    _relative(project, blockers_path),
                )
            )
    claims = assurance.get("claims", [])
    claim_ids = [str(item.get("id", "")) for item in claims]
    if not claim_ids or len(claim_ids) != len(set(claim_ids)):
        findings.append(
            ValidationFinding(
                "error",
                "invalid-assurance-claims",
                "assurance claims require unique non-empty identifiers",
                _relative(project, assurance_path),
            )
        )
    for item in claims:
        level = str(item.get("evidence_level", ""))
        if level not in EVIDENCE_ORDER:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-claim-evidence-level",
                    f"{item.get('id')} has unknown evidence level {level!r}",
                    _relative(project, assurance_path),
                )
            )
        unknown = set(map(str, item.get("linked_blockers", []))) - set(blocker_ids)
        if unknown:
            findings.append(
                ValidationFinding(
                    "error",
                    "unknown-linked-blocker",
                    f"{item.get('id')} references {sorted(unknown)}",
                    _relative(project, assurance_path),
                )
            )
        for evidence in item.get("evidence", []):
            if not (project / str(evidence)).exists():
                findings.append(
                    ValidationFinding(
                        "error",
                        "missing-claim-evidence",
                        f"assurance evidence does not exist: {evidence}",
                        _relative(project, assurance_path),
                    )
                )

    for profile in ("v0.2-alpha", "v0.3-alpha", "v0.4-alpha"):
        try:
            alpha = evaluate_release_readiness(project, profile=profile)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-assurance-profile",
                    str(exc),
                    _relative(project, assurance_path),
                )
            )
        else:
            if not alpha.ready:
                findings.append(
                    ValidationFinding(
                        "error",
                        "alpha-assurance-not-ready",
                        json.dumps(alpha.as_dict(), sort_keys=True),
                        _relative(project, assurance_path),
                    )
                )
    return findings


def _validate_ontology_cases(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    path = project / "benchmark/ontology-tests/competency-cases.json"
    if not path.exists():
        return findings
    try:
        cases = _load_object(path).get("cases", [])
        results = evaluate_competency_cases(
            Ontology.load(project / "benchmark/ontologies/animal.json"),
            Ontology.load(project / "benchmark/ontologies/mobile-object.json"),
            Ontology.load(project / "benchmark/ontologies/interface.json"),
            cases,
        )
    except (KeyError, TypeError, ValueError) as exc:
        findings.append(
            ValidationFinding(
                "error", "invalid-competency-cases", str(exc), _relative(project, path)
            )
        )
        return findings
    failed = [item.case_id for item in results if not item.passed]
    if failed:
        findings.append(
            ValidationFinding(
                "error",
                "competency-case-failure",
                "ontology competency cases failed: " + ", ".join(failed),
                _relative(project, path),
            )
        )
    return findings


def _validate_conductor_views(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    try:
        documents = generated_documents(project)
    except (KeyError, TypeError, ValueError) as exc:
        return [
            ValidationFinding(
                "error", "invalid-conductor-view", str(exc), "conductor"
            )
        ]
    for path, expected in documents.items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            findings.append(
                ValidationFinding(
                    "error",
                    "stale-conductor-view",
                    "generated Conductor view does not match source metadata",
                    _relative(project, path),
                )
            )
    return findings


def _validate_known_exploits(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    path = project / "benchmark/scorer-challenges/known-exploits.json"
    if not path.exists():
        return findings
    try:
        exploits = _load_object(path).get("exploits", [])
    except (TypeError, json.JSONDecodeError) as exc:
        return [
            ValidationFinding(
                "error", "invalid-exploit-registry", str(exc), _relative(project, path)
            )
        ]
    exploit_ids: set[str] = set()
    for exploit in exploits:
        if not isinstance(exploit, dict):
            findings.append(
                ValidationFinding(
                    "error",
                    "invalid-exploit-record",
                    "exploit records must be objects",
                    _relative(project, path),
                )
            )
            continue
        exploit_id = str(exploit.get("id", ""))
        if not exploit_id or exploit_id in exploit_ids:
            findings.append(
                ValidationFinding(
                    "error",
                    "duplicate-exploit-id",
                    f"invalid or duplicate exploit ID {exploit_id!r}",
                    _relative(project, path),
                )
            )
        exploit_ids.add(exploit_id)
        fixture = str(exploit.get("fixture", ""))
        if not fixture or not (project / fixture).exists():
            findings.append(
                ValidationFinding(
                    "error",
                    "missing-exploit-fixture",
                    f"{exploit_id} fixture does not exist: {fixture}",
                    _relative(project, path),
                )
            )
        regression_tests = exploit.get("regression_tests", [])
        if not isinstance(regression_tests, list) or not regression_tests:
            findings.append(
                ValidationFinding(
                    "error",
                    "missing-exploit-regression",
                    f"{exploit_id} requires at least one regression test",
                    _relative(project, path),
                )
            )
            continue
        for reference in map(str, regression_tests):
            test_path_text, separator, test_name = reference.partition("::")
            test_path = project / test_path_text
            if not separator or not test_name or not test_path.exists():
                findings.append(
                    ValidationFinding(
                        "error",
                        "invalid-exploit-regression",
                        f"{exploit_id} regression reference is invalid: {reference}",
                        _relative(project, path),
                    )
                )
                continue
            text = test_path.read_text(encoding="utf-8")
            if re.search(rf"^def\s+{re.escape(test_name)}\s*\(", text, re.MULTILINE) is None:
                findings.append(
                    ValidationFinding(
                        "error",
                        "missing-exploit-test",
                        f"{exploit_id} regression function does not exist: {reference}",
                        _relative(project, path),
                    )
                )
    return findings



def _validate_workflow_action_pins(root: Path) -> list[ValidationFinding]:
    """Require every third-party workflow action to use an immutable commit SHA."""

    findings: list[ValidationFinding] = []
    workflows = root / ".github/workflows"
    if not workflows.exists():
        return findings
    pattern = re.compile(r"^\s*(?:-\s*)?uses:\s*([^#\s]+)", re.MULTILINE)
    for path in sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml"))):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            target = match.group(1)
            if target.startswith("./"):
                continue
            if target.startswith("docker://"):
                image = target.removeprefix("docker://")
                if "@sha256:" not in image:
                    findings.append(
                        ValidationFinding(
                            "error",
                            "unpinned-workflow-container",
                            f"workflow container use must be digest-pinned: {target}",
                            _relative(root, path),
                        )
                    )
                continue
            _, separator, reference = target.rpartition("@")
            if not separator or re.fullmatch(r"[0-9a-f]{40}", reference) is None:
                findings.append(
                    ValidationFinding(
                        "error",
                        "unpinned-workflow-action",
                        f"workflow action must use a 40-character commit SHA: {target}",
                        _relative(root, path),
                    )
                )
    return findings


def _validate_ecosystem_contract(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    registry_path = project / "benchmark/integrations/ecosystem-registry.json"
    if not registry_path.exists():
        return findings
    try:
        registry = load_ecosystem_registry(registry_path)
        report = audit_ecosystem(project, registry)
    except (TypeError, ValueError, ValidationError) as exc:
        return [
            ValidationFinding(
                "error",
                "invalid-ecosystem-registry",
                str(exc),
                _relative(project, registry_path),
            )
        ]
    for item in report.findings:
        if item.severity != "error":
            continue
        findings.append(
            ValidationFinding(
                "error",
                item.code,
                item.message,
                item.path or _relative(project, registry_path),
            )
        )
    direct_names = {item.name for item in registry.assets if item.relevance == "direct"}
    required = {
        "edithatogo/repository-standards",
        "edithatogo/sourceright",
        "edithatogo/authentext",
        "edithatogo/osf-cli-go",
        "edithatogo/substack-cli-ts",
        "edithatogo/arxiv-paper-template",
        "edithatogo/hermes-training",
        "edithatogo/krita-cli",
        "edithatogo/pelican-bench",
        "edithatogo/pelican-bench-explorer",
        "edithatogo/pelican-bench-openenv",
    }
    missing = sorted(required - direct_names)
    if missing:
        findings.append(
            ValidationFinding(
                "error",
                "missing-direct-ecosystem-assets",
                ", ".join(missing),
                _relative(project, registry_path),
            )
        )
    all_names = {item.name for item in registry.assets}
    required_dispositions = {
        "edithatogo/UOGTO",
        "edithatogo/codev",
        "edithatogo/ralph-codex",
        "edithatogo/fyi-cli",
        "edithatogo/fyi-archive",
        "edithatogo/postiz-agent",
        "edithatogo/w3id.org",
        "edithatogo/mcp-registry",
    }
    missing_dispositions = sorted(required_dispositions - all_names)
    if missing_dispositions:
        findings.append(
            ValidationFinding(
                "error",
                "missing-ecosystem-dispositions",
                ", ".join(missing_dispositions),
                _relative(project, registry_path),
            )
        )
    return findings


def _validate_runtime_registry(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    model_path = project / "hf/model-eligibility.json"
    profile_path = project / "hf/runtime-profiles.json"
    if not model_path.exists() or not profile_path.exists():
        return findings
    try:
        models = load_registry(model_path)
        profiles = load_runtime_profiles(profile_path)
    except (TypeError, ValueError, ValidationError) as exc:
        return [
            ValidationFinding(
                "error",
                "invalid-model-runtime-registry",
                str(exc),
                _relative(project, profile_path),
            )
        ]
    profile_ids = {item.profile_id for item in profiles.profiles}
    for model in models:
        if model.runtime_profile and model.runtime_profile not in profile_ids:
            findings.append(
                ValidationFinding(
                    "error",
                    "unknown-runtime-profile",
                    f"{model.model_id} references {model.runtime_profile}",
                    _relative(project, model_path),
                )
            )
        try:
            matched = runtime_profile_for_model(profiles, model.model_id)
        except ValueError as exc:
            findings.append(
                ValidationFinding(
                    "error",
                    "ambiguous-runtime-profile",
                    str(exc),
                    _relative(project, profile_path),
                )
            )
            continue
        if model.runtime_profile and (matched is None or matched.profile_id != model.runtime_profile):
            findings.append(
                ValidationFinding(
                    "error",
                    "runtime-profile-model-mismatch",
                    f"{model.model_id} is not listed by {model.runtime_profile}",
                    _relative(project, profile_path),
                )
            )
    return findings


def _validate_publication_contract(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    plan = default_publication_plan()
    identifiers = [item.action_id for item in plan.actions]
    if len(identifiers) != len(set(identifiers)):
        findings.append(
            ValidationFinding(
                "error",
                "duplicate-publication-action",
                "publication action identifiers must be unique",
                "src/pelicanbench/publication.py",
            )
        )
    for action in plan.actions:
        if action.writes_external and (
            action.mode != "manual-write" or not action.approval_required
        ):
            findings.append(
                ValidationFinding(
                    "error",
                    "unsafe-publication-action",
                    f"{action.action_id} writes externally without manual approval",
                    "src/pelicanbench/publication.py",
                )
            )
    return findings


def _validate_repository_standards_schema(project: Path) -> list[ValidationFinding]:
    path = project / "benchmark/schemas/repository-verification-receipt.schema.json"
    if not path.exists():
        return []
    value = _load_object(path)
    expected_id = "https://github.com/edithatogo/repository-standards/schemas/verification-receipt.schema.json"
    findings: list[ValidationFinding] = []
    if value.get("$id") != expected_id or value.get("properties", {}).get("schema_version", {}).get("const") != 1:
        findings.append(
            ValidationFinding(
                "error",
                "invalid-repository-standards-schema",
                "verification receipt contract must remain pinned to repository-standards v1",
                _relative(project, path),
            )
        )
    return findings


def _validate_ontology_interoperability(project: Path) -> list[ValidationFinding]:
    """Validate ontology exchange surfaces without claiming external publication.

    The profile records UOGTO/HPO as design or validation references and w3id as a
    future namespace host.  These checks deliberately fail if the repository's
    JSON-LD context, SHACL namespace, or competency-question path drifts from the
    declared local contract.
    """

    profile_path = project / "benchmark/ontologies/interoperability-profile.json"
    if not profile_path.exists():
        return []
    try:
        profile = load_ontology_interoperability_profile(profile_path)
    except (TypeError, ValueError, ValidationError) as exc:
        return [
            ValidationFinding(
                "error",
                "invalid-ontology-interoperability-profile",
                str(exc),
                _relative(project, profile_path),
            )
        ]

    findings: list[ValidationFinding] = []
    for relative in profile.validation_surfaces:
        if not (project / relative).exists():
            findings.append(
                ValidationFinding(
                    "error",
                    "missing-ontology-validation-surface",
                    relative,
                    _relative(project, profile_path),
                )
            )

    context_path = project / "benchmark/ontologies/context.jsonld"
    if context_path.exists():
        context = _load_object(context_path).get("@context", {})
        if not isinstance(context, dict) or context.get("pb") != profile.namespace:
            findings.append(
                ValidationFinding(
                    "error",
                    "ontology-namespace-context-drift",
                    f"context pb namespace must equal {profile.namespace}",
                    _relative(project, context_path),
                )
            )

    shapes_path = project / "benchmark/ontologies/shapes.ttl"
    if shapes_path.exists() and f"<{profile.namespace}>" not in shapes_path.read_text(
        encoding="utf-8"
    ):
        findings.append(
            ValidationFinding(
                "error",
                "ontology-namespace-shacl-drift",
                f"SHACL prefix must use {profile.namespace}",
                _relative(project, shapes_path),
            )
        )

    competency_path = project / profile.competency_question_surface
    if not competency_path.exists():
        findings.append(
            ValidationFinding(
                "error",
                "missing-ontology-competency-surface",
                profile.competency_question_surface,
                _relative(project, profile_path),
            )
        )

    if profile.namespace_status != "published" and profile.registration_evidence:
        findings.append(
            ValidationFinding(
                "error",
                "premature-ontology-registration-evidence",
                "registration evidence is only valid after the namespace is published",
                _relative(project, profile_path),
            )
        )
    return findings


def _validate_quality_configuration(project: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    pyproject_path = project / "pyproject.toml"
    if pyproject_path.exists():
        try:
            config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            findings.append(
                ValidationFinding("error", "invalid-pyproject", str(exc), "pyproject.toml")
            )
        else:
            tool = config.get("tool", {})
            coverage = tool.get("coverage", {})
            coverage_run = coverage.get("run", {})
            coverage_report = coverage.get("report", {})
            if coverage_run.get("branch") is not True:
                findings.append(
                    ValidationFinding(
                        "error", "coverage-branch-disabled", "branch coverage must be enabled", "pyproject.toml"
                    )
                )
            if float(coverage_report.get("fail_under", 0)) < 90:
                findings.append(
                    ValidationFinding(
                        "error", "coverage-threshold-low", "coverage fail_under must be at least 90", "pyproject.toml"
                    )
                )
            if tool.get("mypy", {}).get("strict") is not True:
                findings.append(
                    ValidationFinding("error", "mypy-not-strict", "mypy strict mode is required", "pyproject.toml")
                )
            if tool.get("pyright", {}).get("typeCheckingMode") != "strict":
                findings.append(
                    ValidationFinding(
                        "error", "pyright-not-strict", "Pyright strict mode is required", "pyproject.toml"
                    )
                )
            required_markers = {
                "unit", "integration", "e2e", "property", "mutation", "edge",
                "dst", "contract", "metamorphic", "agent", "autonomous",
            }
            marker_values = tool.get("pytest", {}).get("ini_options", {}).get("markers", [])
            present_markers = {str(item).split(":", 1)[0].strip() for item in marker_values}
            missing_markers = sorted(required_markers - present_markers)
            if missing_markers:
                findings.append(
                    ValidationFinding(
                        "error",
                        "test-taxonomy-incomplete",
                        "missing pytest markers: " + ", ".join(missing_markers),
                        "pyproject.toml",
                    )
                )

    required_fragments = {
        ".github/workflows/quality.yml": (
            "ruff check", "ruff format --check", "mypy", "pyright", "vale-action",
        ),
        ".github/workflows/ci.yml": ("codecov/codecov-action@", "use_oidc: true", "fail_ci_if_error: true"),
        ".github/workflows/test-taxonomy.yml": (
            "unit", "integration", "e2e", "property", "mutation", "dst", "autonomous",
        ),
        ".github/workflows/mutation.yml": ("mutation_smoke.py", "mutmut"),
        ".github/workflows/renovate.yml": ("renovatebot/github-action@",),
    }
    for relative, fragments in required_fragments.items():
        path = project / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in text]
        if missing:
            findings.append(
                ValidationFinding(
                    "error",
                    "quality-workflow-incomplete",
                    "missing required workflow fragments: " + ", ".join(missing),
                    relative,
                )
            )

    codecov_path = project / "codecov.yml"
    if codecov_path.exists():
        text = codecov_path.read_text(encoding="utf-8")
        if "target: 90%" not in text or "patch:" not in text:
            findings.append(
                ValidationFinding(
                    "error", "codecov-threshold-incomplete", "project and patch 90% targets are required", "codecov.yml"
                )
            )
    renovate_path = project / "renovate.json"
    if renovate_path.exists():
        try:
            renovate = json.loads(renovate_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
        else:
            if renovate.get("enabled") is False or renovate.get("dependencyDashboard") is not True:
                findings.append(
                    ValidationFinding(
                        "error",
                        "renovate-disabled",
                        "Renovate and its dependency dashboard must be enabled",
                        "renovate.json",
                    )
                )
    return findings

def validate_repository(root: str | Path) -> list[ValidationFinding]:
    project = Path(root)
    findings: list[ValidationFinding] = []
    for relative in REQUIRED_PATHS:
        if not (project / relative).exists():
            findings.append(
                ValidationFinding("error", "missing-required-path", relative, relative)
            )

    for pattern in ("*.json", "*.jsonld"):
        for path in project.rglob(pattern):
            if ".git" in path.parts:
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                findings.append(
                    ValidationFinding(
                        "error",
                        "invalid-json",
                        str(exc),
                        _relative(project, path),
                    )
                )

    grammar_path = project / "benchmark/tasks/grammar.json"
    if grammar_path.exists():
        try:
            load_grammar(grammar_path)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(
                ValidationFinding(
                    "error", "invalid-grammar", str(exc), _relative(project, grammar_path)
                )
            )

    ontology_root = project / "benchmark/ontologies"
    for path in ontology_root.glob("*.json") if ontology_root.exists() else ():
        if path.name == "interoperability-profile.json":
            continue
        try:
            Ontology.load(path)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(
                ValidationFinding(
                    "error", "invalid-ontology", str(exc), _relative(project, path)
                )
            )

    findings.extend(_validate_schema_snapshots(project))
    findings.extend(_validate_task_files(project))
    candidate_path = project / "benchmark/tasks/v1-candidate.jsonl"
    if candidate_path.exists():
        try:
            candidate_report = validate_candidate(project)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(
                ValidationFinding(
                    "error",
                    "candidate-validation-failed",
                    str(exc),
                    _relative(project, candidate_path),
                )
            )
        else:
            findings.extend(
                ValidationFinding(
                    item.severity,
                    "candidate-" + item.code,
                    item.message,
                    _relative(project, candidate_path),
                )
                for item in candidate_report.findings
            )
    findings.extend(_validate_track_graph(project))
    findings.extend(_validate_conductor_views(project))
    findings.extend(_validate_assurance(project))
    findings.extend(_validate_ontology_cases(project))
    findings.extend(_validate_known_exploits(project))
    findings.extend(_validate_workflow_action_pins(project))
    findings.extend(_validate_ecosystem_contract(project))
    findings.extend(_validate_runtime_registry(project))
    findings.extend(_validate_publication_contract(project))
    findings.extend(_validate_repository_standards_schema(project))
    findings.extend(_validate_ontology_interoperability(project))
    findings.extend(_validate_quality_configuration(project))

    status_path = project / "conductor/status.md"
    if status_path.exists():
        findings.extend(_check_evidence_paths(project, status_path.read_text(encoding="utf-8")))

    for path in project.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or path.suffix in {".png", ".jpg", ".jpeg", ".webp", ".pyc"}
            or "__pycache__" in path.parts
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        placeholder_marker = "TODO" + ": placeholder"
        implement_marker = "IMPLEMENT" + " ME"
        if placeholder_marker in text or implement_marker in text:
            findings.append(
                ValidationFinding(
                    "error",
                    "placeholder",
                    "unresolved implementation placeholder",
                    _relative(project, path),
                )
            )
        if path.name == "Dockerfile":
            first_instruction = next(
                (
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                    and not line.lstrip().startswith("#")
                    and not line.startswith("ARG ")
                ),
                "",
            )
            if (
                first_instruction.startswith("FROM ")
                and "${PYTHON_IMAGE}" not in first_instruction
                and "@sha256:" not in first_instruction
            ):
                findings.append(
                    ValidationFinding(
                        "error",
                        "unpinned-container-base",
                        "Dockerfile base must be supplied as an immutable digest",
                        _relative(project, path),
                    )
                )
    return findings


def validation_exit_code(findings: Iterable[ValidationFinding]) -> int:
    return 1 if any(item.severity == "error" for item in findings) else 0
