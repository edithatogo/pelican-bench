"""Content-addressed evaluation run manifests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from .io import content_hash, file_hash
from .models import (
    ArtifactRecord,
    BenchmarkTask,
    EvaluationRecord,
    RunManifest,
    TrialRecord,
)
from .timeutil import utc_now_iso


def artifact_record(
    path: str | Path,
    *,
    media_type: str,
    relative_to: str | Path | None = None,
) -> ArtifactRecord:
    target = Path(path)
    recorded_path = target
    if relative_to is not None:
        recorded_path = target.relative_to(Path(relative_to))
    return ArtifactRecord(
        path=recorded_path.as_posix(),
        media_type=media_type,
        sha256=file_hash(target),
        bytes=target.stat().st_size,
    )


def build_run_manifest(
    *,
    tasks: Iterable[BenchmarkTask],
    artifacts: Iterable[ArtifactRecord],
    benchmark_release: str,
    benchmark_commit: str,
    model_id: str,
    model_revision: str,
    adapter_id: str,
    environment_digest: str,
    seed: int,
    configuration: dict[str, Any],
    costs: dict[str, float] | None = None,
    trials: Iterable[TrialRecord] = (),
    evaluations: Iterable[EvaluationRecord] = (),
) -> RunManifest:
    task_values = list(tasks)
    artifact_values = tuple(artifacts)
    trial_values = tuple(trials)
    evaluation_values = tuple(evaluations)
    prompt_hashes = {task.prompt_id: content_hash(task.prompt) for task in task_values}
    result_payload = {
        "tasks": [task.task_id for task in task_values],
        "trials": [trial.trial_id for trial in trial_values],
        "evaluations": [evaluation.evaluation_id for evaluation in evaluation_values],
        "artifacts": [artifact.model_dump() for artifact in artifact_values],
        "configuration": configuration,
        "costs": costs or {},
    }
    run_payload = {
        "release": benchmark_release,
        "commit": benchmark_commit,
        "model": model_id,
        "revision": model_revision,
        "adapter": adapter_id,
        "seed": seed,
        "result": content_hash(result_payload),
    }
    return RunManifest(
        run_id="run:" + content_hash(run_payload).split(":", 1)[1][:20],
        created_at=utc_now_iso(),
        benchmark_release=benchmark_release,
        benchmark_commit=benchmark_commit,
        model_id=model_id,
        model_revision=model_revision,
        adapter_id=adapter_id,
        environment_digest=environment_digest,
        seed=seed,
        task_ids=tuple(task.task_id for task in task_values),
        scenario_ids=tuple(dict.fromkeys(task.scenario_id for task in task_values)),
        prompt_ids=tuple(dict.fromkeys(task.prompt_id for task in task_values)),
        condition_ids=tuple(dict.fromkeys(task.condition_id for task in task_values)),
        trial_ids=tuple(trial.trial_id for trial in trial_values),
        evaluation_ids=tuple(evaluation.evaluation_id for evaluation in evaluation_values),
        prompt_hashes=prompt_hashes,
        configuration={**configuration, "source_date_epoch": os.getenv("SOURCE_DATE_EPOCH")},
        costs=costs or {},
        artifacts=artifact_values,
        result_hash=content_hash(result_payload),
    )
