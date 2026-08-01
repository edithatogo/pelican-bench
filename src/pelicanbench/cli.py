"""PelicanBench command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .adapters import CallableAdapter
from .corpus import annotate_document, corpus_summary
from .io import read_jsonl, write_json, write_jsonl
from .runner import run_benchmark
from .taskgen import generate_tasks, heritage_task, load_grammar
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
    )
    typer.echo(json.dumps(result.manifest.model_dump(mode="json"), indent=2))


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
