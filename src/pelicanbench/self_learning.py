"""Governed learning ledger and heuristic proposal workflow."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .io import content_hash, read_jsonl
from .timeutil import utc_now_iso

VALID_STATUSES = {"proposed", "validated", "promoted", "rejected", "expired"}


@dataclass(frozen=True, slots=True)
class LearningRecord:
    track: str
    phase: str
    observation: str
    evidence: tuple[str, ...]
    strategy: str
    result: str
    proposed_heuristic: str
    confidence: float
    scope: str
    review_trigger: str
    contamination_risk: str = "low"
    status: str = "proposed"

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be within [0,1]")
        if self.status not in VALID_STATUSES:
            raise ValueError("invalid learning status")
        if self.contamination_risk not in {"none", "low", "medium", "high"}:
            raise ValueError("invalid contamination risk")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["recorded_at"] = utc_now_iso()
        value["learning_id"] = "learn:" + content_hash(value)[7:19]
        return value


def append_record(path: str | Path, record: LearningRecord) -> dict[str, Any]:
    value = record.to_dict()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    return value


def load_records(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    return read_jsonl(target) if target.exists() and target.stat().st_size else []


def eligible_for_review(record: LearningRecord, *, independent_evidence_items: int) -> bool:
    return (
        record.status in {"proposed", "validated"}
        and record.confidence >= 0.7
        and independent_evidence_items >= 2
        and record.contamination_risk in {"none", "low"}
    )


def can_auto_promote(record: LearningRecord) -> bool:
    """Protected benchmark heuristics are never auto-promoted."""
    return False


def summarise_learning(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(records)
    return {
        "records": len(values),
        "by_status": {
            status: sum(item.get("status") == status for item in values)
            for status in sorted(VALID_STATUSES)
        },
        "high_contamination_risk": sum(item.get("contamination_risk") == "high" for item in values),
    }
