"""Deterministic sampling and pairing for human calibration studies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import random
from collections import defaultdict
from itertools import combinations
from typing import Iterable


@dataclass(frozen=True, slots=True)
class CalibrationCandidate:
    artifact_id: str
    task_id: str
    scenario_id: str
    model_id: str
    interface_stratum: str
    automatic_score: float
    judge_disagreement: float
    valid: bool = True

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.task_id or not self.model_id:
            raise ValueError("artifact, task and model identifiers are required")
        if not 0.0 <= self.automatic_score <= 1.0:
            raise ValueError("automatic_score must be within [0,1]")
        if not 0.0 <= self.judge_disagreement <= 1.0:
            raise ValueError("judge_disagreement must be within [0,1]")


@dataclass(frozen=True, slots=True)
class CalibrationSelection:
    selection_id: str
    candidate: CalibrationCandidate
    score_band: str
    disagreement_band: str
    sampling_cell: str
    selection_order: int


@dataclass(frozen=True, slots=True)
class PairwiseCalibrationTask:
    pair_id: str
    task_id: str
    left_artifact_id: str
    right_artifact_id: str
    left_model_id: str
    right_model_id: str
    criterion: str
    presentation_order_seed: int


@dataclass(frozen=True, slots=True)
class CalibrationDesign:
    schema_version: str
    seed: int
    requested_artifacts: int
    selected_artifacts: int
    selections: tuple[CalibrationSelection, ...]
    pairs: tuple[PairwiseCalibrationTask, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def score_band(score: float, *, lower_boundary: float = 0.4, upper_boundary: float = 0.7) -> str:
    if not 0.0 <= score <= 1.0:
        raise ValueError("score must be within [0,1]")
    if lower_boundary <= 0 or upper_boundary >= 1 or lower_boundary >= upper_boundary:
        raise ValueError("invalid score boundaries")
    if score < lower_boundary:
        return "low"
    if score <= upper_boundary:
        return "decision-boundary"
    return "high"


def disagreement_band(disagreement: float, *, high_threshold: float = 0.2) -> str:
    if not 0.0 <= disagreement <= 1.0:
        raise ValueError("disagreement must be within [0,1]")
    if not 0.0 < high_threshold < 1.0:
        raise ValueError("high_threshold must be within (0,1)")
    return "high-disagreement" if disagreement >= high_threshold else "low-disagreement"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def select_calibration_sample(
    candidates: Iterable[CalibrationCandidate],
    *,
    target: int,
    seed: int = 20260801,
) -> tuple[CalibrationSelection, ...]:
    """Select a deterministic, cell-balanced calibration sample.

    Cells cross interface stratum, model, score band and judge-disagreement band.
    Round-robin selection prevents a large model or easy task family from dominating the
    sample. Invalid artifacts are retained as a dedicated validity stratum so failure
    handling can also be calibrated.
    """

    values = list(candidates)
    if target < 1:
        raise ValueError("target must be positive")
    artifact_ids = [item.artifact_id for item in values]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("candidate artifact identifiers must be unique")
    if not values:
        raise ValueError("at least one candidate is required")

    grouped: dict[str, list[tuple[CalibrationCandidate, str, str]]] = defaultdict(list)
    for candidate in values:
        score_value = score_band(candidate.automatic_score) if candidate.valid else "invalid"
        disagreement_value = disagreement_band(candidate.judge_disagreement)
        cell = "|".join(
            (
                candidate.interface_stratum,
                candidate.model_id,
                score_value,
                disagreement_value,
            )
        )
        grouped[cell].append((candidate, score_value, disagreement_value))

    rng = random.Random(seed)
    for cell, rows in grouped.items():
        # A stable pre-sort makes seeded shuffling reproducible even when input order changes.
        rows.sort(key=lambda item: item[0].artifact_id)
        cell_rng = random.Random(seed ^ int(hashlib.sha256(cell.encode()).hexdigest()[:16], 16))
        cell_rng.shuffle(rows)

    cell_order = sorted(grouped)
    rng.shuffle(cell_order)
    selected: list[CalibrationSelection] = []
    cursor = 0
    limit = min(target, len(values))
    while len(selected) < limit:
        progressed = False
        for cell in cell_order:
            rows = grouped[cell]
            if cursor >= len(rows):
                continue
            candidate, score_value, disagreement_value = rows[cursor]
            selected.append(
                CalibrationSelection(
                    selection_id=_stable_id(
                        "CAL",
                        str(seed),
                        candidate.artifact_id,
                        str(len(selected)),
                    ),
                    candidate=candidate,
                    score_band=score_value,
                    disagreement_band=disagreement_value,
                    sampling_cell=cell,
                    selection_order=len(selected) + 1,
                )
            )
            progressed = True
            if len(selected) >= limit:
                break
        if not progressed:
            break
        cursor += 1
    return tuple(selected)


def build_pairwise_calibration_tasks(
    selections: Iterable[CalibrationSelection],
    *,
    seed: int = 20260801,
    criteria: tuple[str, ...] = (
        "entity-recognisability",
        "animal-anatomy",
        "object-mechanics",
        "interaction-correctness",
        "overall-preference",
    ),
    maximum_pairs_per_task: int = 6,
) -> tuple[PairwiseCalibrationTask, ...]:
    """Create blinded within-task cross-model pairs with deterministic orientation."""

    if maximum_pairs_per_task < 1:
        raise ValueError("maximum_pairs_per_task must be positive")
    if not criteria or any(not item for item in criteria):
        raise ValueError("at least one non-empty criterion is required")
    by_task: dict[str, list[CalibrationCandidate]] = defaultdict(list)
    for selection in selections:
        by_task[selection.candidate.task_id].append(selection.candidate)

    output: list[PairwiseCalibrationTask] = []
    for task_id in sorted(by_task):
        # Avoid comparing multiple artifacts from the same model within the primary design.
        by_model: dict[str, CalibrationCandidate] = {}
        for candidate in sorted(by_task[task_id], key=lambda item: item.artifact_id):
            by_model.setdefault(candidate.model_id, candidate)
        combinations_for_task = list(combinations(sorted(by_model), 2))
        task_rng = random.Random(
            seed ^ int(hashlib.sha256(task_id.encode()).hexdigest()[:16], 16)
        )
        task_rng.shuffle(combinations_for_task)
        for model_a, model_b in combinations_for_task[:maximum_pairs_per_task]:
            left_model, right_model = model_a, model_b
            if task_rng.random() < 0.5:
                left_model, right_model = right_model, left_model
            left = by_model[left_model]
            right = by_model[right_model]
            for criterion in criteria:
                order_seed = task_rng.randrange(0, 2**31)
                output.append(
                    PairwiseCalibrationTask(
                        pair_id=_stable_id(
                            "PAIR",
                            task_id,
                            left.artifact_id,
                            right.artifact_id,
                            criterion,
                            str(seed),
                        ),
                        task_id=task_id,
                        left_artifact_id=left.artifact_id,
                        right_artifact_id=right.artifact_id,
                        left_model_id=left.model_id,
                        right_model_id=right.model_id,
                        criterion=criterion,
                        presentation_order_seed=order_seed,
                    )
                )
    return tuple(output)


def build_calibration_design(
    candidates: Iterable[CalibrationCandidate],
    *,
    target: int,
    seed: int = 20260801,
) -> CalibrationDesign:
    selections = select_calibration_sample(candidates, target=target, seed=seed)
    pairs = build_pairwise_calibration_tasks(selections, seed=seed)
    return CalibrationDesign(
        schema_version="1.0.0",
        seed=seed,
        requested_artifacts=target,
        selected_artifacts=len(selections),
        selections=selections,
        pairs=pairs,
    )
