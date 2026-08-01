"""Repository contract validation used by local and CI harnesses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .ontology import Ontology
from .taskgen import load_grammar


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    path: str | None = None


REQUIRED_PATHS = (
    "README.md",
    "pyproject.toml",
    "conductor/index.md",
    "conductor/product.md",
    "conductor/tech-stack.md",
    "conductor/workflow.md",
    "conductor/tracks.md",
    ".agents/plugins/conductor/plugin.json",
    ".agents/skills/conductor-setup/SKILL.md",
    ".entire/settings.json",
    ".github/issues/manifest.json",
    "benchmark/tasks/grammar.json",
)


def _check_evidence_paths(root: Path, status_text: str) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    non_paths = {"complete", "partial", "blocked", "planned", "validated", "prototype", "contract"}
    for value in re.findall(r"`([^`]+)`", status_text):
        if value in non_paths or value.startswith(("http://", "https://")):
            continue
        if "/" not in value and not value.startswith(".") and Path(value).suffix == "":
            continue
        candidate = root / value
        if not candidate.exists():
            findings.append(
                ValidationFinding("error", "missing-evidence", f"status evidence does not exist: {value}", value)
            )
    return findings


def validate_repository(root: str | Path) -> list[ValidationFinding]:
    project = Path(root)
    findings: list[ValidationFinding] = []
    for relative in REQUIRED_PATHS:
        if not (project / relative).exists():
            findings.append(ValidationFinding("error", "missing-required-path", relative, relative))

    for path in project.rglob("*.json"):
        if ".git" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(ValidationFinding("error", "invalid-json", str(exc), path.relative_to(project).as_posix()))

    grammar_path = project / "benchmark/tasks/grammar.json"
    if grammar_path.exists():
        try:
            load_grammar(grammar_path)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(ValidationFinding("error", "invalid-grammar", str(exc), grammar_path.as_posix()))

    for path in (project / "benchmark/ontologies").glob("*.json") if (project / "benchmark/ontologies").exists() else ():
        try:
            Ontology.load(path)
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(ValidationFinding("error", "invalid-ontology", str(exc), path.relative_to(project).as_posix()))

    manifest_path = project / ".github/issues/manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tracks = manifest.get("tracks", [])
        if len(tracks) != 22:
            findings.append(ValidationFinding("error", "track-count", f"expected 22 tracks, found {len(tracks)}", manifest_path.as_posix()))
        phase_count = sum(len(track.get("phases", [])) for track in tracks)
        if phase_count != 88:
            findings.append(ValidationFinding("error", "phase-count", f"expected 88 phases, found {phase_count}", manifest_path.as_posix()))

    status_path = project / "conductor/status.md"
    if status_path.exists():
        findings.extend(_check_evidence_paths(project, status_path.read_text(encoding="utf-8")))

    for path in project.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        placeholder_marker = "TODO" + ": placeholder"
        implement_marker = "IMPLEMENT" + " ME"
        if placeholder_marker in text or implement_marker in text:
            findings.append(ValidationFinding("error", "placeholder", "unresolved implementation placeholder", path.relative_to(project).as_posix()))
        if path.name == "Dockerfile":
            first_instruction = next(
                (line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#") and not line.startswith("ARG ")),
                "",
            )
            if first_instruction.startswith("FROM ") and "${PYTHON_IMAGE}" not in first_instruction and "@sha256:" not in first_instruction:
                findings.append(
                    ValidationFinding(
                        "error",
                        "unpinned-container-base",
                        "Dockerfile base must be supplied as an immutable digest",
                        path.relative_to(project).as_posix(),
                    )
                )
    return findings


def validation_exit_code(findings: Iterable[ValidationFinding]) -> int:
    return 1 if any(item.severity == "error" for item in findings) else 0
