"""Staged prospective multi-model pilot planning.

The planner expands the candidate task panels against named model cohorts while retaining
qualification status, stable replicate seeds, and stage-specific denominators. It performs
no external calls and is therefore safe to run during local validation and CI.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .io import content_hash
from .models import BenchmarkTask
from .timeutil import utc_now_iso


@dataclass(frozen=True, slots=True)
class ProspectiveCell:
    cell_id: str
    stage_id: str
    cohort_id: str
    task_panel_id: str
    task_id: str
    scenario_id: str
    prompt_id: str
    model_id: str
    replicate: int
    seed: int
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProspectiveStage:
    stage_id: str
    cohort_id: str
    task_panel_id: str
    task_count: int
    model_count: int
    cell_count: int
    ready_cell_count: int
    qualification_required_cell_count: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProspectivePilotPlan:
    schema_version: str
    generated_at: str
    task_identity_commitment: str
    task_set_hash: str
    model_registry_hash: str
    replicates: int
    task_count: int
    model_count: int
    cell_count: int
    ready_cell_count: int
    qualification_required_cell_count: int
    stages: tuple[ProspectiveStage, ...]
    cells: tuple[ProspectiveCell, ...]

    def summary(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("cells")
        value["stages"] = [item.as_dict() for item in self.stages]
        return value


def _stable_seed(base_seed: int, stage_id: str, model_id: str, task_id: str, replicate: int) -> int:
    payload = f"{base_seed}\x1f{stage_id}\x1f{model_id}\x1f{task_id}\x1f{replicate}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**31 - 1)


def _stable_cell_id(
    stage_id: str, model_id: str, task_id: str, replicate: int, seed: int
) -> str:
    payload = "\x1f".join((stage_id, model_id, task_id, str(replicate), str(seed)))
    return "PCEL-" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def build_prospective_pilot_plan(
    tasks: Iterable[BenchmarkTask],
    model_panel: Mapping[str, Any],
    *,
    task_identity_commitment: str,
    replicates: int = 3,
    base_seed: int = 20260802,
    model_qualification: Mapping[str, bool] | None = None,
) -> ProspectivePilotPlan:
    if replicates < 1:
        raise ValueError("replicates must be positive")
    task_values = tuple(tasks)
    if not task_values:
        raise ValueError("candidate tasks cannot be empty")
    if not task_identity_commitment.startswith("sha256:"):
        raise ValueError("task identity commitment must be a prefixed SHA-256 digest")
    cohorts = {
        str(item["cohort_id"]): tuple(str(model) for model in item["models"])
        for item in model_panel["cohorts"]
    }
    qualification = dict(model_qualification or {})
    cells: list[ProspectiveCell] = []
    stages: list[ProspectiveStage] = []
    all_models: set[str] = set()
    for stage_value in model_panel["execution_stages"]:
        stage_id = str(stage_value["stage_id"])
        cohort_id = str(stage_value["cohort_id"])
        panel_id = str(stage_value["task_panel_id"])
        if cohort_id not in cohorts:
            raise ValueError(f"stage references unknown model cohort: {cohort_id}")
        stage_tasks = sorted(
            (task for task in task_values if str(task.metadata.get("panel_id")) == panel_id),
            key=lambda item: item.task_id,
        )
        if not stage_tasks:
            raise ValueError(f"stage references an empty task panel: {panel_id}")
        models = cohorts[cohort_id]
        all_models.update(models)
        stage_cells: list[ProspectiveCell] = []
        for model_id in models:
            status = "ready" if qualification.get(model_id, False) else "qualification-required"
            for task in stage_tasks:
                for replicate in range(1, replicates + 1):
                    seed = _stable_seed(base_seed, stage_id, model_id, task.task_id, replicate)
                    stage_cells.append(
                        ProspectiveCell(
                            cell_id=_stable_cell_id(stage_id, model_id, task.task_id, replicate, seed),
                            stage_id=stage_id,
                            cohort_id=cohort_id,
                            task_panel_id=panel_id,
                            task_id=task.task_id,
                            scenario_id=task.scenario_id,
                            prompt_id=task.prompt_id,
                            model_id=model_id,
                            replicate=replicate,
                            seed=seed,
                            status=status,
                        )
                    )
        cells.extend(stage_cells)
        counts = Counter(item.status for item in stage_cells)
        stages.append(
            ProspectiveStage(
                stage_id=stage_id,
                cohort_id=cohort_id,
                task_panel_id=panel_id,
                task_count=len(stage_tasks),
                model_count=len(models),
                cell_count=len(stage_cells),
                ready_cell_count=counts.get("ready", 0),
                qualification_required_cell_count=counts.get("qualification-required", 0),
            )
        )
    identifiers = [item.cell_id for item in cells]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("prospective execution cell identifiers must be unique")
    overall = Counter(item.status for item in cells)
    return ProspectivePilotPlan(
        schema_version="1.0.0",
        generated_at=utc_now_iso(),
        task_identity_commitment=task_identity_commitment,
        task_set_hash=content_hash([task.model_dump(mode="json") for task in task_values]),
        model_registry_hash=content_hash(model_panel),
        replicates=replicates,
        task_count=len(task_values),
        model_count=len(all_models),
        cell_count=len(cells),
        ready_cell_count=overall.get("ready", 0),
        qualification_required_cell_count=overall.get("qualification-required", 0),
        stages=tuple(stages),
        cells=tuple(cells),
    )


__all__ = [
    "ProspectiveCell",
    "ProspectivePilotPlan",
    "ProspectiveStage",
    "build_prospective_pilot_plan",
]
