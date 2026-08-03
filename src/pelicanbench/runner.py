"""Reproducible benchmark runner with separated task, trial and evaluation identities."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .adapters import GenerationResult, ModelAdapter
from .io import atomic_write_bytes, atomic_write_text, content_hash, write_json, write_jsonl
from .judge_firewall import JudgeFirewallPolicy, evaluate_judge_input
from .manifest import artifact_record, build_run_manifest
from .models import (
    BenchmarkTask,
    EvaluationRecord,
    RunManifest,
    ScoreCard,
    TrialRecord,
)
from .provenance import build_prov_jsonld, build_ro_crate, reproduction_script
from .render import SVGRenderError, render_svg
from .scoring import score_svg
from .semantic import SemanticAssessor
from .svg import inspect_svg


@dataclass(frozen=True, slots=True)
class RunResult:
    manifest: RunManifest
    scorecards: tuple[ScoreCard, ...]
    trials: tuple[TrialRecord, ...]
    evaluations: tuple[EvaluationRecord, ...]
    failures: tuple[TrialRecord, ...]
    output_directory: Path


def _safe_id(value: str) -> str:
    return value.replace(":", "_").replace("/", "_")


def run_benchmark(
    tasks: Iterable[BenchmarkTask],
    adapter: ModelAdapter,
    *,
    output_directory: str | Path,
    seed: int,
    benchmark_commit: str,
    environment_digest: str,
    semantic_assessor: SemanticAssessor | None = None,
    judge_policy: JudgeFirewallPolicy | None = None,
    continue_on_error: bool = False,
) -> RunResult:
    task_values = list(tasks)
    if not task_values:
        raise ValueError("at least one task is required")
    release = task_values[0].benchmark_release
    if any(task.benchmark_release != release for task in task_values):
        raise ValueError("all tasks in a run must share a benchmark release")

    root = Path(output_directory)
    outputs_dir = root / "outputs"
    renders_dir = root / "renders"
    scores_dir = root / "scores"
    semantics_dir = root / "semantic-assessments"
    for directory in (outputs_dir, renders_dir, scores_dir, semantics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifacts = []
    scorecards: list[ScoreCard] = []
    trials: list[TrialRecord] = []
    evaluations: list[EvaluationRecord] = []
    failures: list[TrialRecord] = []
    raw_records: list[dict[str, object]] = []

    scorer_manifest_path = root / "scorer-manifest.json"
    scorer_manifest = {
        "schema_version": "1.0.0",
        "scorer_version": "svg-multilayer/0.2.0",
        "semantic_assessor": (
            {
                "id": semantic_assessor.assessor_id,
                "revision": semantic_assessor.assessor_revision,
            }
            if semantic_assessor
            else None
        ),
        "contract": (
            "source labels are diagnostic only; semantic dimensions require a matching "
            "source-independent assessment of the canonical render"
        ),
    }
    write_json(scorer_manifest_path, scorer_manifest)
    artifacts.append(
        artifact_record(scorer_manifest_path, media_type="application/json", relative_to=root)
    )

    for index, task in enumerate(task_values):
        trial_seed = seed + index
        trial_payload = {
            "task_id": task.task_id,
            "model_id": adapter.model_id,
            "model_revision": adapter.model_revision,
            "adapter_id": adapter.adapter_id,
            "seed": trial_seed,
        }
        trial_id = "trial:" + content_hash(trial_payload).split(":", 1)[1][:24]
        safe_id = _safe_id(trial_id)
        try:
            generated: GenerationResult = adapter.generate(task, seed=trial_seed)
            if generated.task_id != task.task_id:
                raise ValueError("adapter returned a mismatched task_id")
            if generated.media_type != "image/svg+xml":
                raise NotImplementedError("V1 runner currently scores SVG outputs only")
        except Exception as exc:
            attempts = max(1, int(getattr(exc, "attempts", 1)))
            failure = TrialRecord(
                trial_id=trial_id,
                task_id=task.task_id,
                scenario_id=task.scenario_id,
                prompt_id=task.prompt_id,
                condition_id=task.condition_id,
                model_id=adapter.model_id,
                model_revision=adapter.model_revision,
                adapter_id=adapter.adapter_id,
                seed=trial_seed,
                status="generation-failed",
                attempts=attempts,
                error_type=type(exc).__name__,
                error_message=str(exc)[-4000:],
                metadata={"retry_errors": list(getattr(exc, "errors", ()))},
            )
            trials.append(failure)
            failures.append(failure)
            raw_records.append(
                {
                    "task": task.model_dump(mode="json"),
                    "trial": failure.model_dump(mode="json"),
                    "generation": None,
                    "evaluation": None,
                    "scorecard": None,
                }
            )
            if not continue_on_error:
                raise
            continue

        artifact_id = content_hash(generated.output)
        output_path = outputs_dir / f"{safe_id}.svg"
        atomic_write_text(output_path, generated.output)

        inspection = inspect_svg(generated.output)
        rendered = None
        if inspection.valid:
            try:
                rendered = render_svg(generated.output, inspection=inspection)
            except SVGRenderError:
                rendered = None
        render_path = renders_dir / f"{safe_id}.png"
        if rendered is not None:
            atomic_write_bytes(render_path, rendered.png)

        semantic_assessment = (
            semantic_assessor.assess(task, rendered)
            if semantic_assessor is not None and rendered is not None
            else None
        )
        semantic_path = semantics_dir / f"{safe_id}.json"
        if semantic_assessment is not None:
            write_json(semantic_path, semantic_assessment.model_dump(mode="json"))

        score = score_svg(
            task,
            generated.output,
            submission_id=artifact_id,
            semantic_assessment=semantic_assessment,
            inspection=inspection,
            rendered=rendered,
        )
        firewall = evaluate_judge_input(
            generated.output,
            inspection,
            rendered,
            policy=judge_policy,
        )
        score = score.model_copy(
            update={
                "critical_gates": {
                    **score.critical_gates,
                    "judge_input_safe": firewall.eligible,
                },
                "valid": score.valid and firewall.eligible,
            }
        )
        score_path = scores_dir / f"{safe_id}.json"
        write_json(score_path, score.model_dump(mode="json"))

        trial = TrialRecord(
            trial_id=trial_id,
            task_id=task.task_id,
            scenario_id=task.scenario_id,
            prompt_id=task.prompt_id,
            condition_id=task.condition_id,
            model_id=adapter.model_id,
            model_revision=adapter.model_revision,
            adapter_id=adapter.adapter_id,
            seed=trial_seed,
            status="success",
            attempts=max(1, int(generated.metadata.get("attempts", 1))),
            artifact_id=artifact_id,
            raw_response_hash=content_hash(generated.raw_response or ""),
            metadata=generated.metadata,
        )
        scorecard_hash = content_hash(score.model_dump(mode="json"))
        evaluation_payload = {
            "trial_id": trial_id,
            "artifact_id": artifact_id,
            "render_hash": score.render_hash,
            "scorer_version": score.scorer_version,
            "semantic_assessment_id": score.semantic_assessment_id,
        }
        evaluation = EvaluationRecord(
            evaluation_id="evaluation:" + content_hash(evaluation_payload).split(":", 1)[1][:24],
            trial_id=trial_id,
            task_id=task.task_id,
            artifact_id=artifact_id,
            render_hash=score.render_hash,
            scorer_version=score.scorer_version,
            semantic_assessment_id=score.semantic_assessment_id,
            scorecard_hash=scorecard_hash,
        )

        artifacts.extend(
            (
                artifact_record(output_path, media_type=generated.media_type, relative_to=root),
                artifact_record(score_path, media_type="application/json", relative_to=root),
            )
        )
        if rendered is not None:
            artifacts.append(artifact_record(render_path, media_type="image/png", relative_to=root))
        if semantic_assessment is not None:
            artifacts.append(
                artifact_record(semantic_path, media_type="application/json", relative_to=root)
            )

        scorecards.append(score)
        trials.append(trial)
        evaluations.append(evaluation)
        raw_records.append(
            {
                "task": task.model_dump(mode="json"),
                "trial": trial.model_dump(mode="json"),
                "generation": {
                    "media_type": generated.media_type,
                    "metadata": generated.metadata,
                    "raw_response_hash": trial.raw_response_hash,
                },
                "evaluation": evaluation.model_dump(mode="json"),
                "scorecard": score.model_dump(mode="json"),
            }
        )

    results_path = root / "results.jsonl"
    trials_path = root / "trials.jsonl"
    evaluations_path = root / "evaluations.jsonl"
    failures_path = root / "failures.jsonl"
    atomic_write_text(
        results_path,
        "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in raw_records
        ),
    )
    write_jsonl(trials_path, [item.model_dump(mode="json") for item in trials])
    write_jsonl(evaluations_path, [item.model_dump(mode="json") for item in evaluations])
    write_jsonl(failures_path, [item.model_dump(mode="json") for item in failures])
    artifacts.extend(
        (
            artifact_record(results_path, media_type="application/x-ndjson", relative_to=root),
            artifact_record(trials_path, media_type="application/x-ndjson", relative_to=root),
            artifact_record(evaluations_path, media_type="application/x-ndjson", relative_to=root),
            artifact_record(failures_path, media_type="application/x-ndjson", relative_to=root),
        )
    )

    reproduce_path = root / "reproduce.sh"
    # The final manifest identity does not depend on this verification script; the script
    # is nevertheless hashed as a primary run artifact.
    placeholder_manifest = build_run_manifest(
        tasks=task_values,
        artifacts=artifacts,
        benchmark_release=release,
        benchmark_commit=benchmark_commit,
        model_id=adapter.model_id,
        model_revision=adapter.model_revision,
        adapter_id=adapter.adapter_id,
        environment_digest=environment_digest,
        seed=seed,
        configuration={
            "runner_version": "0.3.0",
            "task_count": len(task_values),
            "success_count": len(scorecards),
            "failure_count": len(failures),
            "continue_on_error": continue_on_error,
        },
        trials=trials,
        evaluations=evaluations,
    )
    atomic_write_text(reproduce_path, reproduction_script(placeholder_manifest))
    reproduce_path.chmod(0o755)
    artifacts.append(
        artifact_record(reproduce_path, media_type="text/x-shellscript", relative_to=root)
    )

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
        configuration={
            "runner_version": "0.3.0",
            "task_count": len(task_values),
            "success_count": len(scorecards),
            "failure_count": len(failures),
            "continue_on_error": continue_on_error,
            "semantic_assessor_id": semantic_assessor.assessor_id if semantic_assessor else None,
            "semantic_assessor_revision": (
                semantic_assessor.assessor_revision if semantic_assessor else None
            ),
        },
        trials=trials,
        evaluations=evaluations,
    )
    write_json(root / "run-manifest.json", manifest.model_dump(mode="json"))
    write_json(
        root / "prov.jsonld",
        build_prov_jsonld(manifest, trials=trials, evaluations=evaluations),
    )
    write_json(root / "ro-crate-metadata.json", build_ro_crate(manifest))
    return RunResult(
        manifest=manifest,
        scorecards=tuple(scorecards),
        trials=tuple(trials),
        evaluations=tuple(evaluations),
        failures=tuple(failures),
        output_directory=root,
    )
