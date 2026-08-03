"""Privacy-minimised, stage-gated human-calibration responses and analysis.

The module is independent of any survey platform. It enforces the blind-before-prompt
sequence, validates categorical/rating responses, rejects direct identifiers, produces
content-addressed receipts, and calculates transparent calibration summaries.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any

STAGE_ORDER = ("blind-recognition", "prompt-aware-criteria", "pairwise-preference")
SENSITIVE_FIELDS = frozenset(
    {
        "name",
        "email",
        "phone",
        "address",
        "ip",
        "ip_address",
        "user_agent",
        "participant_name",
        "participant_id",
    }
)

STAGE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "blind-recognition": (
        "animal_open_text",
        "mobile_object_open_text",
        "relation_open_text",
        "recognition_confidence",
    ),
    "prompt-aware-criteria": (
        "animal_defects",
        "object_defects",
        "interaction_defects",
        "animal_rating_1_to_5",
        "object_rating_1_to_5",
        "interaction_rating_1_to_5",
        "criterion_confidence",
    ),
    "pairwise-preference": ("pairwise_winner",),
}


@dataclass(frozen=True, slots=True)
class ResponseValidation:
    stage: str
    missing_fields: tuple[str, ...]
    invalid_fields: tuple[str, ...]
    prohibited_fields: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not (self.missing_fields or self.invalid_fields or self.prohibited_fields)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        return value


@dataclass(frozen=True, slots=True)
class StageReceipt:
    schema_version: str
    assignment_id: str
    artifact_id: str
    stage: str
    response_hash: str
    previous_receipt_hash: str | None
    receipt_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CalibrationSession:
    assignment_id: str
    artifact_id: str
    permitted_stages: tuple[str, ...] = STAGE_ORDER
    _responses: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _receipts: list[StageReceipt] = field(default_factory=list, init=False, repr=False)

    @property
    def completed_stages(self) -> tuple[str, ...]:
        return tuple(self._responses)

    @property
    def next_stage(self) -> str | None:
        for stage in self.permitted_stages:
            if stage not in self._responses:
                return stage
        return None

    @property
    def prompt_disclosure_permitted(self) -> bool:
        return "blind-recognition" in self._responses

    def submit(self, stage: str, response: Mapping[str, Any]) -> StageReceipt:
        if stage not in self.permitted_stages:
            raise ValueError(f"stage is not part of this assignment: {stage}")
        if stage in self._responses:
            raise ValueError(f"stage is already locked: {stage}")
        if stage != self.next_stage:
            raise ValueError(f"stage must be completed in order; expected {self.next_stage}")
        validation = validate_calibration_response(stage, response)
        if not validation.valid:
            raise ValueError(json.dumps(validation.as_dict(), sort_keys=True))
        canonical_response = json.dumps(
            dict(response), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        response_hash = "sha256:" + hashlib.sha256(canonical_response.encode("utf-8")).hexdigest()
        previous = self._receipts[-1].receipt_hash if self._receipts else None
        receipt_payload = {
            "assignment_id": self.assignment_id,
            "artifact_id": self.artifact_id,
            "stage": stage,
            "response_hash": response_hash,
            "previous_receipt_hash": previous,
        }
        receipt_hash = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(receipt_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        )
        receipt = StageReceipt(
            schema_version="1.0.0",
            assignment_id=self.assignment_id,
            artifact_id=self.artifact_id,
            stage=stage,
            response_hash=response_hash,
            previous_receipt_hash=previous,
            receipt_hash=receipt_hash,
        )
        self._responses[stage] = dict(response)
        self._receipts.append(receipt)
        return receipt

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "assignment_id": self.assignment_id,
            "artifact_id": self.artifact_id,
            "completed_stages": list(self.completed_stages),
            "responses": dict(self._responses),
            "receipts": [item.as_dict() for item in self._receipts],
        }


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def validate_calibration_response(stage: str, response: Mapping[str, Any]) -> ResponseValidation:
    if stage not in STAGE_REQUIRED_FIELDS:
        raise ValueError(f"unknown calibration stage: {stage}")
    normalized_keys = {str(key).strip().lower() for key in response}
    prohibited = tuple(sorted(normalized_keys & SENSITIVE_FIELDS))
    required = STAGE_REQUIRED_FIELDS[stage]
    missing = tuple(field for field in required if _missing(response.get(field)))
    invalid: list[str] = []

    confidence_field = {
        "blind-recognition": "recognition_confidence",
        "prompt-aware-criteria": "criterion_confidence",
    }.get(stage)
    if confidence_field is not None and not _missing(response.get(confidence_field)):
        value = _number(response.get(confidence_field))
        if value is None or not 0 <= value <= 100:
            invalid.append(confidence_field)

    if stage == "prompt-aware-criteria":
        for field_name in (
            "animal_rating_1_to_5",
            "object_rating_1_to_5",
            "interaction_rating_1_to_5",
        ):
            if _missing(response.get(field_name)):
                continue
            value = _number(response.get(field_name))
            if value is None or not 1 <= value <= 5 or not value.is_integer():
                invalid.append(field_name)
    elif stage == "pairwise-preference" and str(
        response.get("pairwise_winner", "")
    ).strip().lower() not in {"a", "b", "tie"}:
        invalid.append("pairwise_winner")

    return ResponseValidation(
        stage=stage,
        missing_fields=missing,
        invalid_fields=tuple(sorted(set(invalid))),
        prohibited_fields=prohibited,
    )


def _normalise_label(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("_", "-").split())


def _nominal_alpha(groups: Iterable[list[str]]) -> float | None:
    values = [group for group in groups if len(group) >= 2]
    if not values:
        return None
    category_counts: Counter[str] = Counter(value for group in values for value in group)
    total = sum(category_counts.values())
    if total < 2:
        return None
    observed_pairs = 0
    observed_disagreements = 0
    for group in values:
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                observed_pairs += 1
                observed_disagreements += int(left != right)
    if observed_pairs == 0:
        return None
    observed = observed_disagreements / observed_pairs
    expected = 1.0 - sum(count * (count - 1) for count in category_counts.values()) / (
        total * (total - 1)
    )
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1.0 - observed / expected


def analyse_calibration_responses(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = [dict(row) for row in rows]
    valid: list[dict[str, Any]] = []
    invalid_count = 0
    stage_counts: Counter[str] = Counter()
    for row in values:
        stage = str(row.get("stage", ""))
        response = row.get("response", row)
        if not isinstance(response, Mapping):
            invalid_count += 1
            continue
        try:
            validation = validate_calibration_response(stage, response)
        except ValueError:
            invalid_count += 1
            continue
        if not validation.valid:
            invalid_count += 1
            continue
        merged = dict(row)
        merged["response"] = dict(response)
        valid.append(merged)
        stage_counts[stage] += 1

    blind_rows = [item for item in valid if item["stage"] == "blind-recognition"]
    criterion_rows = [item for item in valid if item["stage"] == "prompt-aware-criteria"]
    pairwise_rows = [item for item in valid if item["stage"] == "pairwise-preference"]

    fields = (
        ("animal_open_text", "expected_animal"),
        ("mobile_object_open_text", "expected_mobile_object"),
        ("relation_open_text", "expected_relation"),
    )
    accuracies: dict[str, float] = {}
    for response_field, expected_field in fields:
        comparable = [item for item in blind_rows if item.get(expected_field) is not None]
        accuracies[response_field] = (
            sum(
                _normalise_label(item["response"][response_field])
                == _normalise_label(item[expected_field])
                for item in comparable
            )
            / len(comparable)
            if comparable
            else 0.0
        )
    comparable_scene = [
        item for item in blind_rows if all(item.get(expected) is not None for _, expected in fields)
    ]
    scene_correct: dict[int, bool] = {}
    for item in comparable_scene:
        scene_correct[id(item)] = all(
            _normalise_label(item["response"][response]) == _normalise_label(item[expected])
            for response, expected in fields
        )
    scene_accuracy = (
        sum(scene_correct.values()) / len(comparable_scene) if comparable_scene else 0.0
    )
    brier = (
        sum(
            (
                float(item["response"]["recognition_confidence"]) / 100.0
                - float(scene_correct[id(item)])
            )
            ** 2
            for item in comparable_scene
        )
        / len(comparable_scene)
        if comparable_scene
        else 0.0
    )

    criterion_fields = (
        "animal_rating_1_to_5",
        "object_rating_1_to_5",
        "interaction_rating_1_to_5",
    )
    criterion_means = {
        field_name: sum(float(item["response"][field_name]) for item in criterion_rows)
        / len(criterion_rows)
        for field_name in criterion_fields
        if criterion_rows
    }

    duplicate_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in blind_rows:
        group_id = item.get("duplicate_group_id")
        if group_id:
            duplicate_groups[str(group_id)].append(item)
    duplicate_consistency: dict[str, float] = {}
    for response_field, _ in fields:
        comparisons: list[bool] = []
        for group in duplicate_groups.values():
            labels = [_normalise_label(item["response"][response_field]) for item in group]
            for index, left in enumerate(labels):
                comparisons.extend(left == right for right in labels[index + 1 :])
        if comparisons:
            duplicate_consistency[response_field] = sum(comparisons) / len(comparisons)

    alpha_by_field: dict[str, float] = {}
    for response_field, _ in fields:
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in blind_rows:
            artifact_id = str(item.get("artifact_id", ""))
            if artifact_id:
                grouped[artifact_id].append(_normalise_label(item["response"][response_field]))
        alpha = _nominal_alpha(grouped.values())
        if alpha is not None:
            alpha_by_field[response_field] = alpha

    limitations: list[str] = []
    if not alpha_by_field:
        limitations.append("inter-rater-alpha-unavailable")
    return {
        "schema_version": "1.0.0",
        "responses_received": len(values),
        "valid_responses": len(valid),
        "invalid_responses": invalid_count,
        "valid_by_stage": dict(sorted(stage_counts.items())),
        "blind_animal_accuracy": accuracies["animal_open_text"],
        "blind_mobile_object_accuracy": accuracies["mobile_object_open_text"],
        "blind_relation_accuracy": accuracies["relation_open_text"],
        "blind_scene_accuracy": scene_accuracy,
        "recognition_brier_score": brier,
        "mean_criterion_ratings": criterion_means,
        "pairwise_winner_counts": dict(
            sorted(
                Counter(str(item["response"]["pairwise_winner"]) for item in pairwise_rows).items()
            )
        ),
        "duplicate_consistency_by_field": duplicate_consistency,
        "nominal_alpha_by_field": alpha_by_field,
        "limitations": limitations,
    }


__all__ = [
    "CalibrationSession",
    "ResponseValidation",
    "StageReceipt",
    "analyse_calibration_responses",
    "validate_calibration_response",
]
