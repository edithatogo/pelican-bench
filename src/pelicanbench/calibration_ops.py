"""Adjudication queues and fail-closed stopping rules for human calibration."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .io import content_hash


@dataclass(frozen=True, slots=True)
class AdjudicationItem:
    item_id: str
    artifact_id: str
    task_id: str
    stage: str
    field: str
    value_counts: dict[str, int]
    modal_share: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CalibrationStoppingReport:
    schema_version: str
    ready_to_stop: bool
    gates: dict[str, bool]
    failures: tuple[str, ...]
    valid_by_stage: dict[str, int]
    invalid_fraction: float

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["failures"] = list(self.failures)
        return value


def _normalise(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("_", "-").split())


def build_adjudication_queue(
    rows: Iterable[Mapping[str, Any]],
    *,
    minimum_modal_share: float = 2 / 3,
    low_confidence_threshold: float = 50.0,
    criterion_range_threshold: float = 2.0,
) -> tuple[AdjudicationItem, ...]:
    if not 0.5 <= minimum_modal_share <= 1:
        raise ValueError("minimum_modal_share must be within [0.5,1]")
    if not 0 <= low_confidence_threshold <= 100:
        raise ValueError("low_confidence_threshold must be within [0,100]")
    if criterion_range_threshold < 0:
        raise ValueError("criterion_range_threshold cannot be negative")

    values = [dict(item) for item in rows]
    queue: list[AdjudicationItem] = []
    recognition_fields = (
        "animal_open_text",
        "mobile_object_open_text",
        "relation_open_text",
    )
    criterion_fields = (
        "animal_rating_1_to_5",
        "object_rating_1_to_5",
        "interaction_rating_1_to_5",
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in values:
        artifact_id = str(row.get("artifact_id", ""))
        stage = str(row.get("stage", ""))
        response = row.get("response", row)
        if artifact_id and isinstance(response, Mapping):
            merged = dict(row)
            merged["response"] = dict(response)
            grouped[(artifact_id, stage)].append(merged)

    for (artifact_id, stage), group in sorted(grouped.items()):
        task_id = str(next((item.get("task_id") for item in group if item.get("task_id")), ""))
        fields = recognition_fields if stage == "blind-recognition" else criterion_fields
        for field in fields:
            raw = [item["response"].get(field) for item in group if field in item["response"]]
            if len(raw) < 2:
                continue
            if stage == "blind-recognition":
                counts = Counter(_normalise(item) for item in raw)
                modal_share = max(counts.values()) / len(raw)
                reason = "inter-rater-label-disagreement"
                needs_review = modal_share < minimum_modal_share
            else:
                numeric = [float(item) for item in raw]
                counts = Counter(str(int(item)) if item.is_integer() else str(item) for item in numeric)
                modal_share = max(counts.values()) / len(raw)
                reason = "criterion-rating-range"
                needs_review = max(numeric) - min(numeric) >= criterion_range_threshold
            if needs_review:
                payload = {
                    "artifact_id": artifact_id,
                    "task_id": task_id,
                    "stage": stage,
                    "field": field,
                    "counts": dict(sorted(counts.items())),
                    "reason": reason,
                }
                queue.append(
                    AdjudicationItem(
                        item_id="ADJ-" + content_hash(payload).split(":", 1)[1][:20],
                        artifact_id=artifact_id,
                        task_id=task_id,
                        stage=stage,
                        field=field,
                        value_counts=dict(sorted(counts.items())),
                        modal_share=round(modal_share, 6),
                        reason=reason,
                    )
                )

        if stage == "blind-recognition":
            confidences = [
                float(item["response"]["recognition_confidence"])
                for item in group
                if "recognition_confidence" in item["response"]
            ]
            if confidences and sum(confidences) / len(confidences) < low_confidence_threshold:
                payload = {
                    "artifact_id": artifact_id,
                    "task_id": task_id,
                    "stage": stage,
                    "field": "recognition_confidence",
                    "reason": "low-mean-recognition-confidence",
                }
                queue.append(
                    AdjudicationItem(
                        item_id="ADJ-" + content_hash(payload).split(":", 1)[1][:20],
                        artifact_id=artifact_id,
                        task_id=task_id,
                        stage=stage,
                        field="recognition_confidence",
                        value_counts={"observations": len(confidences)},
                        modal_share=round(sum(confidences) / (100 * len(confidences)), 6),
                        reason="low-mean-recognition-confidence",
                    )
                )
    queue.sort(key=lambda item: (item.artifact_id, item.stage, item.field, item.item_id))
    return tuple(queue)


def evaluate_calibration_stopping(
    analysis: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> CalibrationStoppingReport:
    received = int(analysis.get("responses_received", 0))
    invalid = int(analysis.get("invalid_responses", 0))
    invalid_fraction = invalid / received if received else 1.0
    valid_by_stage = {
        str(key): int(value) for key, value in dict(analysis.get("valid_by_stage", {})).items()
    }
    gates: dict[str, bool] = {}
    for stage, minimum in dict(policy["minimum_valid_by_stage"]).items():
        gates[f"stage:{stage}"] = valid_by_stage.get(str(stage), 0) >= int(minimum)
    gates["invalid-fraction"] = invalid_fraction <= float(policy["maximum_invalid_fraction"])
    gates["brier-score"] = float(analysis.get("recognition_brier_score", 1.0)) <= float(
        policy["maximum_recognition_brier"]
    )

    alphas = dict(analysis.get("nominal_alpha_by_field", {}))
    for field in policy["required_alpha_fields"]:
        gates[f"alpha:{field}"] = float(alphas.get(str(field), -1.0)) >= float(
            policy["minimum_nominal_alpha"]
        )
    duplicate = dict(analysis.get("duplicate_consistency_by_field", {}))
    for field in policy["required_duplicate_fields"]:
        gates[f"duplicate:{field}"] = float(duplicate.get(str(field), -1.0)) >= float(
            policy["minimum_duplicate_consistency"]
        )

    failures = tuple(sorted(name for name, passed in gates.items() if not passed))
    return CalibrationStoppingReport(
        schema_version="1.0.0",
        ready_to_stop=not failures,
        gates=dict(sorted(gates.items())),
        failures=failures,
        valid_by_stage=dict(sorted(valid_by_stage.items())),
        invalid_fraction=round(invalid_fraction, 6),
    )


__all__ = [
    "AdjudicationItem",
    "CalibrationStoppingReport",
    "build_adjudication_queue",
    "evaluate_calibration_stopping",
]
