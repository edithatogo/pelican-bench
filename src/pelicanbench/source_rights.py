"""Rights-traceability of committed sourced and derived data artifacts.

Every ``source_id`` referenced by a committed JSONL artifact under ``data/fixtures/``
or ``data/derived/`` must resolve to an explicit decision in
``data/sources/rights-ledger.json`` or be declared project-original on the record
itself. This keeps sourcing fail-closed: new sourced data cannot be added without
recording a compatible rights decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PROJECT_ORIGINAL_PREFIX = "project-original"
SOURCED_DATA_GLOBS = ("data/fixtures/*.jsonl", "data/derived/*.jsonl")
RIGHTS_LEDGER_PATH = "data/sources/rights-ledger.json"


@dataclass(frozen=True, slots=True)
class SourceRightsFinding:
    severity: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SourceRightsReport:
    passed: bool
    findings: tuple[SourceRightsFinding, ...] = ()
    artifact_count: int = 0


def _ledger_source_ids(project: Path) -> set[str]:
    ledger: dict[str, object] = json.loads(
        (project / RIGHTS_LEDGER_PATH).read_text(encoding="utf-8")
    )
    raw_decisions = ledger.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError(f"{RIGHTS_LEDGER_PATH} must contain a decisions list")
    source_ids: set[str] = set()
    decision_items = cast(list[object], raw_decisions)
    for raw_item in decision_items:
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, object], raw_item)
        value = item.get("source_id")
        if isinstance(value, str):
            source_ids.add(value)
    return source_ids


def _data_artifacts(project: Path) -> list[Path]:
    artifacts: list[Path] = []
    for pattern in SOURCED_DATA_GLOBS:
        artifacts.extend(sorted(project.glob(pattern)))
    return artifacts


def audit_sourced_artifacts(project: str | Path) -> SourceRightsReport:
    root = Path(project)
    decisions = _ledger_source_ids(root)
    findings: list[SourceRightsFinding] = []
    record_count = 0
    for path in _data_artifacts(root):
        relative = path.relative_to(root).as_posix()
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            record_raw: object = json.loads(raw)
            if not isinstance(record_raw, dict):
                raise ValueError(f"{relative}:{line_number} is not a JSON object")
            record = cast(dict[str, object], record_raw)
            record_count += 1
            source_id: object = record.get("source_id")
            rights_status: object = record.get("rights_status", "")
            if not isinstance(source_id, str):
                findings.append(
                    SourceRightsFinding(
                        "error",
                        "missing-source-id",
                        f"{relative}:{line_number} record has no string source_id",
                    )
                )
                continue
            if source_id in decisions:
                continue
            if isinstance(rights_status, str) and rights_status.startswith(PROJECT_ORIGINAL_PREFIX):
                continue
            findings.append(
                SourceRightsFinding(
                    "error",
                    "unregistered-source",
                    f"{relative}:{line_number} source '{source_id}' has no rights decision "
                    "and is not declared project-original",
                )
            )
    return SourceRightsReport(
        passed=not any(item.severity == "error" for item in findings),
        findings=tuple(findings),
        artifact_count=record_count,
    )
