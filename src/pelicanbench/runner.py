"""Reproducible benchmark runner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .adapters import GenerationResult, ModelAdapter
from .io import atomic_write_text, content_hash, write_json
from .manifest import artifact_record, build_run_manifest
from .models import BenchmarkTask, RunManifest, ScoreCard
from .scoring import score_svg


@dataclass(frozen=True, slots=True)
class RunResult:
    manifest: RunManifest
    scorecards: tuple[ScoreCard, ...]
    output_directory: Path


def run_benchmark(
    tasks: Iterable[BenchmarkTask],
    adapter: ModelAdapter,
    *,
    output_directory: str | Path,
    seed: int,
    benchmark_commit: str,
    environment_digest: str,
) -> RunResult:
    task_values = list(tasks)
    if not task_values:
        raise ValueError("at least one task is required")
    release = task_values[0].benchmark_release
    if any(task.benchmark_release != release for task in task_values):
        raise ValueError("all tasks in a run must share a benchmark release")
    root = Path(output_directory)
    outputs_dir = root / "outputs"
    scores_dir = root / "scores"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    scores_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    scorecards: list[ScoreCard] = []
    raw_records: list[dict[str, object]] = []
    for index, task in enumerate(task_values):
        task_seed = seed + index
        generated: GenerationResult = adapter.generate(task, seed=task_seed)
        if generated.task_id != task.task_id:
            raise ValueError("adapter returned a mismatched task_id")
        if generated.media_type != "image/svg+xml":
            raise NotImplementedError("V1 runner currently scores SVG outputs only")
        safe_id = task.task_id.replace(":", "_")
        output_path = outputs_dir / f"{safe_id}.svg"
        atomic_write_text(output_path, generated.output)
        score = score_svg(task, generated.output, submission_id=content_hash(generated.output))
        score_path = scores_dir / f"{safe_id}.json"
        write_json(score_path, score.model_dump(mode="json"))
        artifacts.extend(
            (
                artifact_record(output_path, media_type=generated.media_type, relative_to=root),
                artifact_record(score_path, media_type="application/json", relative_to=root),
            )
        )
        scorecards.append(score)
        raw_records.append(
            {
                "task": task.model_dump(mode="json"),
                "generation": {
                    "media_type": generated.media_type,
                    "metadata": generated.metadata,
                    "raw_response_hash": content_hash(generated.raw_response or ""),
                },
                "scorecard": score.model_dump(mode="json"),
            }
        )
    results_path = root / "results.jsonl"
    atomic_write_text(
        results_path,
        "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in raw_records
        ),
    )
    artifacts.append(artifact_record(results_path, media_type="application/x-ndjson", relative_to=root))
    manifest = build_run_manifest(
        tasks=task_values,
        artifacts=artifacts,
        benchmark_release=release,
        benchmark_commit=benchmark_commit,
        model_id=adapter.model_id,
        model_revision=adapter.model_revision,
        adapter_id=adapter.adapter_id,
        environment_digest=environment_digest,
        seed=seed,
        configuration={"runner_version": "0.1.0", "task_count": len(task_values)},
    )
    write_json(root / "run-manifest.json", manifest.model_dump(mode="json"))
    return RunResult(manifest=manifest, scorecards=tuple(scorecards), output_directory=root)
