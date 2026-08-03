"""Deterministic qualification plans and evidence gates for models and visual judges."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .io import content_hash, read_json
from .models import BenchmarkTask
from .pilot import load_tasks

DEFAULT_MODEL_GATES: dict[str, float] = {
    "minimum_success_rate": 0.8,
    "minimum_secure_render_rate": 0.8,
    "minimum_first_attempt_rate": 0.5,
    "maximum_unretained_failure_rate": 0.0,
}


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _panel_id(task: BenchmarkTask) -> str:
    return str(task.metadata.get("panel_id", "unassigned"))


@dataclass(frozen=True, slots=True)
class ModelQualificationCell:
    cell_id: str
    model_id: str
    task_id: str
    panel_id: str
    seed: int
    status: str = "planned"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelQualificationOutcome:
    cell_id: str
    retained: bool
    eventual_success: bool
    valid_svg: bool
    secure_render: bool
    first_attempt_success: bool
    attempts: int = 1
    error_type: str | None = None

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be positive")
        if self.first_attempt_success and not self.eventual_success:
            raise ValueError("first-attempt success implies eventual success")
        if self.secure_render and not self.valid_svg:
            raise ValueError("secure rendering requires a valid SVG")


@dataclass(frozen=True, slots=True)
class ModelQualificationResult:
    model_id: str
    expected_cells: int
    retained_cells: int
    success_rate: float
    valid_svg_rate: float
    secure_render_rate: float
    first_attempt_rate: float
    unretained_failure_rate: float
    gate_results: dict[str, bool]
    qualified: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class JudgeQualificationCell:
    cell_id: str
    judge_id: str
    family: str
    role: str
    canary_id: str
    artifact_id: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class JudgeQualificationOutcome:
    cell_id: str
    schema_valid: bool
    output_complete: bool
    source_independent: bool
    prompt_leakage: bool
    task_correct: bool
    human_agreement: float | None = None

    def __post_init__(self) -> None:
        if self.human_agreement is not None and not 0.0 <= self.human_agreement <= 1.0:
            raise ValueError("human_agreement must be within [0,1]")


@dataclass(frozen=True, slots=True)
class JudgeQualificationResult:
    judge_id: str
    role: str
    expected_cells: int
    schema_valid_rate: float
    output_complete_rate: float
    source_independent_rate: float
    prompt_leakage_rate: float
    task_accuracy: float
    mean_human_agreement: float | None
    technical_gates_passed: bool
    empirical_gate_passed: bool
    evidence_status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def execution_model_ids(panel: Mapping[str, Any]) -> tuple[str, ...]:
    cohorts = {
        str(item["cohort_id"]): tuple(str(model) for model in item["models"])
        for item in panel["cohorts"]
    }
    used = {
        model for stage in panel["execution_stages"] for model in cohorts[str(stage["cohort_id"])]
    }
    return tuple(sorted(used))


def build_model_qualification_plan(
    tasks: Iterable[BenchmarkTask],
    panel: Mapping[str, Any],
    *,
    benchmark_release: str,
    base_seed: int = 20260802,
    gates: Mapping[str, float] = DEFAULT_MODEL_GATES,
) -> dict[str, Any]:
    values = sorted(tasks, key=lambda item: item.task_id)
    if not values:
        raise ValueError("qualification canary tasks cannot be empty")
    model_ids = execution_model_ids(panel)
    cells: list[ModelQualificationCell] = []
    for model_index, model_id in enumerate(model_ids):
        model_seed = base_seed + model_index * 10_000
        for task_index, task in enumerate(values):
            seed = model_seed + task_index
            cells.append(
                ModelQualificationCell(
                    cell_id=_stable_id("QCEL", model_id, task.task_id, str(seed)),
                    model_id=model_id,
                    task_id=task.task_id,
                    panel_id=_panel_id(task),
                    seed=seed,
                )
            )
    return {
        "schema_version": "1.0.0",
        "benchmark_release": benchmark_release,
        "models": list(model_ids),
        "tasks": [task.task_id for task in values],
        "gates": dict(gates),
        "cells": [cell.as_dict() for cell in cells],
    }


def evaluate_model_qualification(
    plan: Mapping[str, Any], outcomes: Iterable[ModelQualificationOutcome]
) -> tuple[ModelQualificationResult, ...]:
    cells = {str(item["cell_id"]): item for item in plan["cells"]}
    outcome_values = tuple(outcomes)
    outcome_ids = [item.cell_id for item in outcome_values]
    if len(outcome_ids) != len(set(outcome_ids)):
        raise ValueError("qualification outcomes must have unique cell identifiers")
    unknown = sorted(set(outcome_ids) - set(cells))
    if unknown:
        raise ValueError(f"outcomes reference unknown qualification cells: {unknown}")
    by_cell = {item.cell_id: item for item in outcome_values}
    by_model: dict[str, list[str]] = defaultdict(list)
    for cell_id, cell in cells.items():
        by_model[str(cell["model_id"])].append(cell_id)
    gates = plan["gates"]
    results: list[ModelQualificationResult] = []
    for model_id in sorted(by_model):
        expected_ids = by_model[model_id]
        expected = len(expected_ids)
        retained = [
            by_cell[cell_id]
            for cell_id in expected_ids
            if cell_id in by_cell and by_cell[cell_id].retained
        ]
        success_rate = sum(item.eventual_success for item in retained) / expected
        valid_svg_rate = sum(item.valid_svg for item in retained) / expected
        secure_render_rate = sum(item.secure_render for item in retained) / expected
        first_attempt_rate = sum(item.first_attempt_success for item in retained) / expected
        unretained_failure_rate = (expected - len(retained)) / expected
        gate_results = {
            "minimum_success_rate": success_rate >= float(gates["minimum_success_rate"]),
            "minimum_secure_render_rate": secure_render_rate
            >= float(gates["minimum_secure_render_rate"]),
            "minimum_first_attempt_rate": first_attempt_rate
            >= float(gates["minimum_first_attempt_rate"]),
            "maximum_unretained_failure_rate": unretained_failure_rate
            <= float(gates["maximum_unretained_failure_rate"]),
        }
        results.append(
            ModelQualificationResult(
                model_id=model_id,
                expected_cells=expected,
                retained_cells=len(retained),
                success_rate=success_rate,
                valid_svg_rate=valid_svg_rate,
                secure_render_rate=secure_render_rate,
                first_attempt_rate=first_attempt_rate,
                unretained_failure_rate=unretained_failure_rate,
                gate_results=gate_results,
                qualified=all(gate_results.values()),
            )
        )
    return tuple(results)


def build_judge_qualification_plan(
    panel: Mapping[str, Any], canary_manifest: Mapping[str, Any]
) -> tuple[dict[str, Any], tuple[JudgeQualificationCell, ...]]:
    judges = tuple(panel["judges"])
    canaries = tuple(canary_manifest["canaries"])
    cells: list[JudgeQualificationCell] = []
    role_counts: Counter[str] = Counter()
    families_by_role: dict[str, set[str]] = defaultdict(set)
    for judge in judges:
        judge_id = str(judge["judge_id"])
        family = str(judge["family"])
        for role in judge["roles"]:
            role_name = str(role)
            families_by_role[role_name].add(family)
            for canary in canaries:
                if role_name not in canary["applicable_roles"]:
                    continue
                cells.append(
                    JudgeQualificationCell(
                        cell_id=_stable_id("JCEL", judge_id, role_name, str(canary["canary_id"])),
                        judge_id=judge_id,
                        family=family,
                        role=role_name,
                        canary_id=str(canary["canary_id"]),
                        artifact_id=str(canary["artifact_id"]),
                    )
                )
                role_counts[role_name] += 1
    minimums = {str(key): int(value) for key, value in panel["minimum_families_by_role"].items()}
    family_counts = {role: len(families_by_role.get(role, set())) for role in sorted(minimums)}
    blockers = [
        f"{role}: requires {minimum}, found {family_counts[role]} families"
        for role, minimum in sorted(minimums.items())
        if family_counts[role] < minimum
    ]
    summary = {
        "schema_version": "1.0.0",
        "judge_count": len(judges),
        "family_count": len({str(item["family"]) for item in judges}),
        "canary_count": len(canaries),
        "cell_count": len(cells),
        "role_counts": dict(sorted(role_counts.items())),
        "family_counts_by_role": family_counts,
        "diversity_gates_satisfied": not blockers,
        "blockers": blockers,
        "panel_hash": content_hash(panel),
        "canary_hash": content_hash(canary_manifest),
    }
    return summary, tuple(cells)


def evaluate_judge_qualification(
    plan_cells: Iterable[JudgeQualificationCell],
    outcomes: Iterable[JudgeQualificationOutcome],
    gates: Mapping[str, float],
) -> tuple[JudgeQualificationResult, ...]:
    cells = {item.cell_id: item for item in plan_cells}
    outcome_values = tuple(outcomes)
    outcome_ids = [item.cell_id for item in outcome_values]
    if len(outcome_ids) != len(set(outcome_ids)):
        raise ValueError("judge outcomes must have unique cell identifiers")
    unknown = sorted(set(outcome_ids) - set(cells))
    if unknown:
        raise ValueError(f"outcomes reference unknown judge cells: {unknown}")
    by_cell = {item.cell_id: item for item in outcome_values}
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for cell in cells.values():
        grouped[(cell.judge_id, cell.role)].append(cell.cell_id)
    results: list[JudgeQualificationResult] = []
    for (judge_id, role), cell_ids in sorted(grouped.items()):
        expected = len(cell_ids)
        values = [by_cell[cell_id] for cell_id in cell_ids if cell_id in by_cell]
        schema_rate = sum(item.schema_valid for item in values) / expected
        complete_rate = sum(item.output_complete for item in values) / expected
        independent_rate = sum(item.source_independent for item in values) / expected
        leakage_rate = sum(item.prompt_leakage for item in values) / expected
        accuracy = sum(item.task_correct for item in values) / expected
        agreements = [item.human_agreement for item in values if item.human_agreement is not None]
        mean_agreement = sum(agreements) / len(agreements) if agreements else None
        technical = (
            schema_rate >= float(gates["minimum_schema_valid_rate"])
            and complete_rate >= float(gates["minimum_output_complete_rate"])
            and independent_rate >= float(gates["minimum_source_independent_rate"])
            and leakage_rate <= float(gates["maximum_prompt_leakage_rate"])
            and accuracy >= float(gates["minimum_task_accuracy"])
        )
        empirical = mean_agreement is not None and mean_agreement >= float(
            gates["minimum_human_agreement"]
        )
        results.append(
            JudgeQualificationResult(
                judge_id=judge_id,
                role=role,
                expected_cells=expected,
                schema_valid_rate=schema_rate,
                output_complete_rate=complete_rate,
                source_independent_rate=independent_rate,
                prompt_leakage_rate=leakage_rate,
                task_accuracy=accuracy,
                mean_human_agreement=mean_agreement,
                technical_gates_passed=technical,
                empirical_gate_passed=empirical,
                evidence_status=(
                    "E3-human-calibrated"
                    if technical and empirical
                    else "E2-technical-qualified-human-calibration-required"
                    if technical
                    else "qualification-failed"
                ),
            )
        )
    return tuple(results)


def load_default_model_qualification_plan(root: str | Path) -> dict[str, Any]:
    project = Path(root)
    tasks = load_tasks(project / "benchmark/tasks/v1-candidate-canary.jsonl")
    panel = read_json(project / "benchmark/models/prospective-panel.json")
    release = str(read_json(project / "benchmark/tasks/v1-candidate-design.json")["release"])
    return build_model_qualification_plan(tasks, panel, benchmark_release=release)


def load_default_judge_qualification_plan(
    root: str | Path,
) -> tuple[dict[str, Any], tuple[JudgeQualificationCell, ...]]:
    project = Path(root)
    return build_judge_qualification_plan(
        read_json(project / "benchmark/judges/prospective-panel.json"),
        read_json(project / "benchmark/judges/canary-manifest.json"),
    )


__all__ = [
    "JudgeQualificationCell",
    "JudgeQualificationOutcome",
    "JudgeQualificationResult",
    "ModelQualificationCell",
    "ModelQualificationOutcome",
    "ModelQualificationResult",
    "build_judge_qualification_plan",
    "build_model_qualification_plan",
    "evaluate_judge_qualification",
    "evaluate_model_qualification",
    "execution_model_ids",
    "load_default_judge_qualification_plan",
    "load_default_model_qualification_plan",
]
