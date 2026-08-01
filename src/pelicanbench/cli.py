"""PelicanBench command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .adapters import CallableAdapter
from .assurance import evaluate_release_readiness
from .calibration import CalibrationCandidate, build_calibration_design
from .corpus import annotate_document, corpus_summary
from .fuzzing import run_svg_fuzz_campaign
from .io import read_json, read_jsonl, write_json, write_jsonl
from .metamorphic import run_scorer_challenges
from .render_bridge import compare_renderers
from .runner import run_benchmark
from .semantic import StaticSemanticAssessor
from .taskgen import generate_design_tasks, generate_tasks, heritage_task, load_grammar, task_set_commitment
from .validation import validate_repository, validation_exit_code

app = typer.Typer(no_args_is_help=True, help="PelicanBench research and evaluation CLI.")


def _fixture_svg(_task: object, _seed: int) -> str:
    return (Path(__file__).resolve().parents[2] / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")


@app.command("validate-repo")
def validate_repo(
    root: Annotated[Path, typer.Option(help="Repository root.")] = Path("."),
) -> None:
    findings = validate_repository(root)
    for finding in findings:
        location = f" [{finding.path}]" if finding.path else ""
        typer.echo(f"{finding.severity.upper()} {finding.code}{location}: {finding.message}")
    if not findings:
        typer.echo("Repository contract valid.")
    raise typer.Exit(validation_exit_code(findings))


@app.command("release-readiness")
def release_readiness_command(
    profile: Annotated[str, typer.Option(help="Release assurance profile")] = "v0.2-alpha",
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    report = evaluate_release_readiness(root, profile=profile)
    if json_output:
        typer.echo(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        typer.echo(f"Profile: {profile}")
        for claim in report.claim_results:
            marker = "PASS" if claim.satisfied else "FAIL"
            typer.echo(
                f"{marker} {claim.claim_id}: {claim.evidence_level} "
                f"(requires {claim.required_level})"
            )
        for blocker in report.blocker_results:
            if blocker.blocks_profile:
                typer.echo(f"BLOCK {blocker.blocker_id}: {blocker.status}")
        typer.echo("READY" if report.ready else "NOT_READY")
    raise typer.Exit(0 if report.ready else 1)


@app.command("generate-tasks")
def generate_tasks_command(
    output: Annotated[Path, typer.Option(help="Destination JSONL file")],
    count: Annotated[int, typer.Option(min=1)] = 12,
    seed: int = 20260801,
    grammar: Path = Path("benchmark/tasks/grammar.json"),
    release: str = "PB-2026.08",
) -> None:
    tasks = generate_tasks(load_grammar(grammar), count=count, seed=seed, release=release)
    write_jsonl(output, [task.model_dump(mode="json") for task in tasks])
    typer.echo(f"Wrote {len(tasks)} tasks to {output}")


@app.command("generate-v1-pilot")
def generate_v1_pilot_command(
    output: Annotated[Path, typer.Option(help="Destination JSONL file")] = Path("benchmark/tasks/v1-pilot.jsonl"),
    design: Path = Path("benchmark/tasks/v1-pilot-design.json"),
    grammar: Path = Path("benchmark/tasks/grammar.json"),
) -> None:
    design_value = read_json(design)
    tasks = generate_design_tasks(
        load_grammar(grammar),
        design_value,
        seed=int(design_value["seed"]),
    )
    write_jsonl(output, [task.model_dump(mode="json") for task in tasks])
    commitment_path = output.with_name(output.stem + "-commitment.json")
    write_json(
        commitment_path,
        {
            "schema_version": "1.0.0",
            "release": design_value["release"],
            "task_count": len(tasks),
            "scenario_count": len({task.scenario_id for task in tasks}),
            "prompt_count": len({task.prompt_id for task in tasks}),
            "commitment": task_set_commitment(tasks),
        },
    )
    typer.echo(f"Wrote {len(tasks)} prespecified pilot tasks to {output}")


@app.command("renderer-bridge")
def renderer_bridge_command(
    source: Annotated[Path, typer.Option(help="SVG source file")],
    size: Annotated[int, typer.Option(min=32, max=4096)] = 512,
) -> None:
    result = compare_renderers(source.read_text(encoding="utf-8"), size=size)
    typer.echo(
        json.dumps(
            {
                "canonical_renderer": result.canonical_renderer,
                "bridge_renderer": result.bridge_renderer,
                "canonical_hash": result.canonical_hash,
                "bridge_hash": result.bridge_hash,
                "mean_absolute_error": result.mean_absolute_error,
                "differing_pixel_fraction": result.differing_pixel_fraction,
                "maximum_channel_error": result.maximum_channel_error,
                "materially_different": result.materially_different,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("scorer-challenges")
def scorer_challenges_command(
    source: Annotated[
        Path, typer.Option(help="Baseline SVG source file")
    ] = Path("benchmark/fixtures/svg/pelican-bicycle-valid.svg"),
    output: Annotated[
        Path | None, typer.Option(help="Optional machine-readable report destination")
    ] = None,
) -> None:
    report = run_scorer_challenges(
        heritage_task(seed=20260801),
        source.read_text(encoding="utf-8"),
    )
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("fuzz-svg")
def fuzz_svg_command(
    source: Annotated[
        Path, typer.Option(help="Baseline SVG source file")
    ] = Path("benchmark/fixtures/svg/pelican-bicycle-valid.svg"),
    output: Annotated[
        Path | None, typer.Option(help="Optional machine-readable report destination")
    ] = None,
    cases: Annotated[int, typer.Option(min=1, max=10000)] = 100,
    seed: int = 20260801,
    budget_ms: Annotated[float, typer.Option(min=1.0)] = 1000.0,
) -> None:
    report = run_svg_fuzz_campaign(
        source.read_text(encoding="utf-8"),
        cases=cases,
        seed=seed,
        budget_ms=budget_ms,
    )
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("run-fixture")
def run_fixture(
    output: Annotated[Path, typer.Option(help="Run output directory")] = Path("runs/fixture"),
    seed: int = 20260801,
) -> None:
    adapter = CallableAdapter(_fixture_svg, model_id="pelicanbench/fixture", model_revision="v1")
    result = run_benchmark(
        [heritage_task(seed=seed)],
        adapter,
        output_directory=output,
        seed=seed,
        benchmark_commit="working-tree",
        environment_digest="local-fixture",
        semantic_assessor=StaticSemanticAssessor(),
    )
    typer.echo(json.dumps(result.manifest.model_dump(mode="json"), indent=2))


@app.command("design-human-calibration")
def design_human_calibration_command(
    source: Annotated[
        Path, typer.Option(help="Candidate artifact JSONL")
    ],
    output: Annotated[
        Path, typer.Option(help="Calibration design JSON destination")
    ],
    target: Annotated[int, typer.Option(min=1)] = 64,
    seed: int = 20260801,
) -> None:
    candidates = [CalibrationCandidate(**item) for item in read_jsonl(source)]
    design_value = build_calibration_design(candidates, target=target, seed=seed)
    write_json(output, design_value.as_dict())
    typer.echo(
        f"Selected {design_value.selected_artifacts} artifacts and "
        f"created {len(design_value.pairs)} blinded criterion pairs"
    )


@app.command("analyse-corpus")
def analyse_corpus(
    source: Annotated[Path, typer.Option(help="Source JSONL with source_id and text")],
    output: Annotated[Path, typer.Option(help="Annotation JSONL destination")],
) -> None:
    annotations = [annotate_document(item) for item in read_jsonl(source)]
    write_jsonl(output, annotations)
    write_json(output.with_suffix(".summary.json"), corpus_summary(annotations))
    typer.echo(f"Annotated {len(annotations)} documents")


if __name__ == "__main__":
    app()
