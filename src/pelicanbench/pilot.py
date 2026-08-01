"""Prospective pilot execution planning with explicit model qualification gates."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .io import content_hash, read_jsonl, write_json, write_jsonl
from .models import BenchmarkTask
from .registry import ModelRegistryEntry
from .timeutil import utc_now_iso


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PilotExecutionCell(StrictModel):
    cell_id: str = Field(pattern=r"^cell:[0-9a-f]{64}$")
    task_id: str
    scenario_id: str
    prompt_id: str
    condition_id: str
    model_id: str
    model_revision: str
    runtime_profile: str | None = None
    replicate: int = Field(ge=1)
    seed: int = Field(ge=0)
    status: Literal["ready", "qualification-required"]
    qualification_blockers: tuple[str, ...] = ()


class PilotExecutionPlan(StrictModel):
    schema_version: str = "1.0.0"
    generated_at: str
    task_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_registry_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    replicates: int = Field(ge=1)
    task_count: int = Field(ge=0)
    scenario_count: int = Field(ge=0)
    model_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)
    ready_cell_count: int = Field(ge=0)
    qualification_required_cell_count: int = Field(ge=0)
    status_counts: dict[str, int]
    model_status: dict[str, dict[str, object]]
    cells: tuple[PilotExecutionCell, ...]


def _trial_seed(base_seed: int, model_id: str, task_id: str, replicate: int) -> int:
    payload = f"{base_seed}\0{model_id}\0{task_id}\0{replicate}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**31 - 1)


def load_tasks(path: str | Path) -> list[BenchmarkTask]:
    return [BenchmarkTask.model_validate(item) for item in read_jsonl(path)]


def build_pilot_execution_plan(
    tasks: list[BenchmarkTask],
    models: list[ModelRegistryEntry],
    *,
    replicates: int = 3,
    base_seed: int = 20260801,
    include_candidate_models: bool = True,
) -> PilotExecutionPlan:
    if replicates < 1:
        raise ValueError("replicates must be at least one")
    if not tasks:
        raise ValueError("pilot tasks cannot be empty")
    selected = [
        model
        for model in models
        if model.status not in {"blocked", "retired"}
        and (model.eligible or include_candidate_models)
        and any(task.track in model.tracks for task in tasks)
    ]
    cells: list[PilotExecutionCell] = []
    model_status: dict[str, dict[str, object]] = {}
    for model in selected:
        blockers = model.eligibility_blockers
        model_status[model.model_id] = {
            "eligible": model.eligible,
            "revision": model.revision,
            "runtime_profile": model.runtime_profile,
            "blockers": list(blockers),
            "access_type": model.access_type,
        }
        for task in tasks:
            if task.track not in model.tracks:
                continue
            for replicate in range(1, replicates + 1):
                seed = _trial_seed(base_seed, model.model_id, task.task_id, replicate)
                identity = content_hash(
                    {
                        "task_id": task.task_id,
                        "model_id": model.model_id,
                        "model_revision": model.revision,
                        "replicate": replicate,
                        "seed": seed,
                    }
                )
                cells.append(
                    PilotExecutionCell(
                        cell_id=f"cell:{identity.split(':', 1)[1]}",
                        task_id=task.task_id,
                        scenario_id=task.scenario_id,
                        prompt_id=task.prompt_id,
                        condition_id=task.condition_id,
                        model_id=model.model_id,
                        model_revision=model.revision,
                        runtime_profile=model.runtime_profile,
                        replicate=replicate,
                        seed=seed,
                        status="ready" if model.eligible else "qualification-required",
                        qualification_blockers=blockers,
                    )
                )
    cells.sort(key=lambda item: (item.model_id, item.task_id, item.replicate))
    counts = Counter(item.status for item in cells)
    task_payload = [task.model_dump(mode="json") for task in tasks]
    model_payload = [model.model_dump(mode="json") for model in selected]
    return PilotExecutionPlan(
        generated_at=utc_now_iso(),
        task_set_hash=content_hash(task_payload),
        model_registry_hash=content_hash(model_payload),
        replicates=replicates,
        task_count=len(tasks),
        scenario_count=len({task.scenario_id for task in tasks}),
        model_count=len(selected),
        cell_count=len(cells),
        ready_cell_count=counts.get("ready", 0),
        qualification_required_cell_count=counts.get("qualification-required", 0),
        status_counts=dict(sorted(counts.items())),
        model_status=model_status,
        cells=tuple(cells),
    )


def write_pilot_execution_plan(
    plan: PilotExecutionPlan,
    output: str | Path,
) -> tuple[Path, Path]:
    path = Path(output)
    write_json(path, plan.model_dump(mode="json", exclude={"cells"}))
    cells_path = path.with_name(path.stem + "-cells.jsonl")
    write_jsonl(cells_path, [item.model_dump(mode="json") for item in plan.cells])
    return path, cells_path
