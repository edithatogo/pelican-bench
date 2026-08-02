"""PelicanBench command-line interface."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from .adapters import CallableAdapter, OpenAICompatibleAdapter
from .assurance import evaluate_release_readiness
from .calibration import CalibrationCandidate, PairwiseCalibrationTask, build_calibration_design
from .candidate import candidate_commitment_payload, validate_candidate
from .corpus import annotate_document, corpus_summary
from .ecosystem import audit_ecosystem, load_ecosystem_registry
from .empirical_nlp import (
    PromptRecord,
    annotate_prompt_corpus,
    empirical_nlp_report,
    task_design_coverage,
)
from .fuzzing import run_svg_fuzz_campaign
from .human_eval import (
    export_pairwise_evaluation_batch,
    fit_bradley_terry,
    inter_rater_agreement,
    load_pairwise_votes_csv,
)
from .human_study import analyse_calibration_responses
from .interoperability import load_ontology_interoperability_profile
from .io import read_json, read_jsonl, write_json, write_jsonl
from .metamorphic import run_scorer_challenges
from .pilot import build_pilot_execution_plan, load_tasks, write_pilot_execution_plan
from .prospective import build_prospective_pilot_plan
from .publication import build_publication_bundle
from .qualification import (
    load_default_judge_qualification_plan,
    load_default_model_qualification_plan,
)
from .registry import (
    load_registry,
    load_runtime_profiles,
    registry_summary,
    runtime_profile_for_model,
)
from .render_bridge import compare_renderers
from .runner import run_benchmark
from .simon_corpus import fetch_atom, parse_simon_atom, write_simon_atom_corpus
from .semantic import StaticSemanticAssessor
from .taskgen import generate_design_tasks, generate_tasks, heritage_task, load_grammar, task_set_commitment
from .validation import validate_repository, validation_exit_code
from .verification import (
    build_repository_verification_receipt,
    validate_repository_verification_receipt,
)

app = typer.Typer(no_args_is_help=True, help="PelicanBench research and evaluation CLI.")


def _fixture_svg(_task: object, _seed: int) -> str:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "benchmark/fixtures/svg/pelican-bicycle-valid.svg"
    )
    return fixture.read_text(encoding="utf-8")


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


@app.command("validate-v1-candidate")
def validate_v1_candidate_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[
        Path | None, typer.Option(help="Optional machine-readable report destination")
    ] = None,
) -> None:
    report = validate_candidate(root)
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("candidate-commitment")
def candidate_commitment_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[Path | None, typer.Option(help="Optional JSON destination")] = None,
) -> None:
    payload = candidate_commitment_payload(root)
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("analyse-empirical-prompt-bridge")
def analyse_empirical_prompt_bridge_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[Path | None, typer.Option(help="Optional report destination")] = None,
) -> None:
    records = [
        PromptRecord.from_mapping(item)
        for item in read_jsonl(root / "data/derived/castillo-2026-prompt-corpus.jsonl")
    ]
    annotations = annotate_prompt_corpus(records)
    status = "source-derived-exact-prompt-bridge-E2"
    payload = {
        "nlp_report": empirical_nlp_report(annotations, evidence_status=status),
        "design_coverage": task_design_coverage(
            annotations,
            load_tasks(root / "benchmark/tasks/v1-candidate.jsonl"),
            panel_id="castillo-2026-factorial-bridge",
            evidence_status=status,
        ),
        "annotations": [item.as_dict() for item in annotations],
    }
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("plan-prospective-pilot")
def plan_prospective_pilot_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[Path, typer.Option(help="Plan summary destination")] = Path(
        "artifacts/prospective-pilot-plan.json"
    ),
    cells_output: Annotated[
        Path | None, typer.Option(help="Optional detailed cell JSONL destination")
    ] = None,
    replicates: Annotated[int, typer.Option(min=1, max=100)] = 3,
    seed: int = 20260802,
) -> None:
    tasks = load_tasks(root / "benchmark/tasks/v1-candidate.jsonl")
    panel = read_json(root / "benchmark/models/prospective-panel.json")
    commitment = read_json(root / "benchmark/tasks/v1-candidate-commitment.json")
    plan = build_prospective_pilot_plan(
        tasks,
        panel,
        task_identity_commitment=str(commitment["commitment"]),
        replicates=replicates,
        base_seed=seed,
    )
    write_json(output, plan.summary())
    detailed = cells_output or output.with_name(output.stem + "-cells.jsonl")
    write_jsonl(detailed, [item.as_dict() for item in plan.cells])
    typer.echo(
        f"Wrote {plan.cell_count} cells across {len(plan.stages)} stages to "
        f"{output} and {detailed}"
    )


@app.command("plan-model-qualification")
def plan_model_qualification_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[Path | None, typer.Option(help="Optional plan destination")] = None,
) -> None:
    payload = load_default_model_qualification_plan(root)
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("plan-judge-qualification")
def plan_judge_qualification_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    output: Annotated[Path | None, typer.Option(help="Optional summary destination")] = None,
    cells_output: Annotated[
        Path | None, typer.Option(help="Optional detailed cell JSONL destination")
    ] = None,
) -> None:
    summary, cells = load_default_judge_qualification_plan(root)
    if output is not None:
        write_json(output, summary)
    if cells_output is not None:
        write_jsonl(cells_output, [item.as_dict() for item in cells])
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))


@app.command("analyse-human-calibration-jsonl")
def analyse_human_calibration_jsonl_command(
    source: Annotated[Path, typer.Option(help="Staged response JSONL")],
    output: Annotated[Path | None, typer.Option(help="Optional analysis destination")] = None,
) -> None:
    payload = analyse_calibration_responses(read_jsonl(source))
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("import-simon-atom")
def import_simon_atom_command(
    output: Annotated[Path, typer.Option(help="Destination JSONL")],
    source: Annotated[Path | None, typer.Option(help="Local Atom XML; otherwise fetch URL")] = None,
    url: Annotated[str, typer.Option(help="Atom URL used when source is absent")] = (
        "https://simonwillison.net/tags/pelican-riding-a-bicycle.atom"
    ),
    rights_status: Annotated[str, typer.Option(help="Rights-ledger status")] = "metadata-only",
    include_content: Annotated[bool, typer.Option("--include-content")] = False,
    timeout_seconds: Annotated[float, typer.Option(min=0.1, max=120.0)] = 30.0,
) -> None:
    payload = source.read_bytes() if source is not None else fetch_atom(url, timeout_seconds=timeout_seconds)
    corpus = parse_simon_atom(
        payload, rights_status=rights_status, include_content=include_content
    )
    records, summary = write_simon_atom_corpus(corpus, output)
    typer.echo(f"Wrote {corpus.entry_count} entries to {records}; summary {summary}")


@app.command("release-readiness")
def release_readiness_command(
    profile: Annotated[str, typer.Option(help="Release assurance profile")] = "v0.4-alpha",
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


@app.command("export-human-evaluation-batch")
def export_human_evaluation_batch_command(
    design: Annotated[
        Path, typer.Option(help="Calibration design JSON generated by design-human-calibration")
    ],
    output: Annotated[
        Path, typer.Option(help="Privacy-minimised evaluation package directory")
    ],
    seed: int = 20260801,
) -> None:
    value = read_json(design)
    raw_pairs = value.get("pairs") if isinstance(value, dict) else None
    if not isinstance(raw_pairs, list):
        raise typer.BadParameter("calibration design must contain a pairs array")
    pairs = [PairwiseCalibrationTask(**item) for item in raw_pairs]
    batch = export_pairwise_evaluation_batch(pairs, output, seed=seed)
    typer.echo(
        f"Exported {batch.assignments} blinded assignments across "
        f"{len(batch.criteria)} criteria to {output}"
    )


@app.command("analyse-human-evaluation")
def analyse_human_evaluation_command(
    source: Annotated[Path, typer.Option(help="Completed human-rating CSV")],
    output: Annotated[Path | None, typer.Option(help="Optional analysis JSON destination")] = None,
) -> None:
    votes = load_pairwise_votes_csv(source)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "vote_count": len(votes),
        "criteria": {},
    }
    criteria = sorted({vote.criterion for vote in votes})
    criterion_results: dict[str, object] = {}
    for criterion in criteria:
        subset = [vote for vote in votes if vote.criterion == criterion]
        result: dict[str, object] = {
            "votes": len(subset),
            "bradley_terry_scores": fit_bradley_terry(subset),
        }
        try:
            result["agreement"] = asdict(inter_rater_agreement(subset))
        except ValueError as exc:
            result["agreement"] = {"status": "insufficient-replicate-ratings", "reason": str(exc)}
        criterion_results[criterion] = result
    payload["criteria"] = criterion_results
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("analyse-corpus")
def analyse_corpus(
    source: Annotated[Path, typer.Option(help="Source JSONL with source_id and text")],
    output: Annotated[Path, typer.Option(help="Annotation JSONL destination")],
) -> None:
    annotations = [annotate_document(item) for item in read_jsonl(source)]
    write_jsonl(output, annotations)
    write_json(output.with_suffix(".summary.json"), corpus_summary(annotations))
    typer.echo(f"Annotated {len(annotations)} documents")


@app.command("ecosystem-audit")
def ecosystem_audit_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    registry: Annotated[
        Path, typer.Option(help="Machine-readable integration registry")
    ] = Path("benchmark/integrations/ecosystem-registry.json"),
    output: Annotated[
        Path | None, typer.Option(help="Optional audit report destination")
    ] = None,
) -> None:
    report = audit_ecosystem(root, load_ecosystem_registry(registry))
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("model-registry-status")
def model_registry_status_command(
    registry: Annotated[
        Path, typer.Option(help="Model eligibility registry")
    ] = Path("hf/model-eligibility.json"),
    runtime_profiles: Annotated[
        Path, typer.Option(help="Runtime prompt-profile registry")
    ] = Path("hf/runtime-profiles.json"),
) -> None:
    entries = load_registry(registry)
    profiles = load_runtime_profiles(runtime_profiles)
    payload = registry_summary(entries)
    payload["profiles"] = len(profiles.profiles)
    payload["models_detail"] = [
        {
            "model_id": item.model_id,
            "eligible": item.eligible,
            "blockers": list(item.eligibility_blockers),
            "runtime_profile": item.runtime_profile,
            "first_party": item.first_party,
        }
        for item in entries
    ]
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("ontology-interoperability-status")
def ontology_interoperability_status_command(
    profile: Annotated[
        Path, typer.Option(help="Ontology interoperability profile")
    ] = Path("benchmark/ontologies/interoperability-profile.json"),
) -> None:
    value = load_ontology_interoperability_profile(profile)
    typer.echo(json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command("plan-pilot")
def plan_pilot_command(
    output: Annotated[Path, typer.Option(help="Execution-plan JSON destination")],
    tasks: Annotated[
        Path, typer.Option(help="Prespecified pilot task JSONL")
    ] = Path("benchmark/tasks/v1-pilot.jsonl"),
    registry: Annotated[
        Path, typer.Option(help="Model eligibility registry")
    ] = Path("hf/model-eligibility.json"),
    replicates: Annotated[int, typer.Option(min=1, max=100)] = 3,
    seed: int = 20260801,
    include_candidates: Annotated[
        bool, typer.Option("--include-candidates/--eligible-only")
    ] = True,
) -> None:
    plan = build_pilot_execution_plan(
        load_tasks(tasks),
        load_registry(registry),
        replicates=replicates,
        base_seed=seed,
        include_candidate_models=include_candidates,
    )
    summary, cells = write_pilot_execution_plan(plan, output)
    typer.echo(
        f"Wrote {plan.cell_count} cells ({plan.ready_cell_count} ready; "
        f"{plan.qualification_required_cell_count} qualification-required) "
        f"to {summary} and {cells}"
    )


@app.command("verification-receipt")
def verification_receipt_command(
    output: Annotated[Path, typer.Option(help="Receipt JSON destination")],
    profile: str = "v0.4-alpha",
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    coverage: Annotated[Path, typer.Option(help="Coverage XML path")] = Path("coverage.xml"),
    artifact: Annotated[list[Path] | None, typer.Option(help="Additional evidence artifact")] = None,
) -> None:
    receipt = build_repository_verification_receipt(
        root,
        profile=profile,
        coverage_path=coverage,
        artifact_paths=tuple(artifact or ()),
    )
    schema = Path(root) / "benchmark/schemas/repository-verification-receipt.schema.json"
    validate_repository_verification_receipt(receipt, schema)
    write_json(output, receipt.model_dump(mode="json", exclude_none=True))
    typer.echo(json.dumps(receipt.model_dump(mode="json", exclude_none=True), indent=2, sort_keys=True))
    raise typer.Exit(0 if receipt.result != "fail" else 1)


@app.command("publication-bundle")
def publication_bundle_command(
    output: Annotated[Path, typer.Option(help="Publication bundle directory")],
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    artifact: Annotated[list[Path] | None, typer.Option(help="Evidence artifact to copy")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    manifest = build_publication_bundle(
        root,
        output,
        include_artifacts=tuple(artifact or ()),
        overwrite=overwrite,
    )
    typer.echo(
        f"Publication bundle contains {len(manifest.files)} files; "
        f"bundle hash {manifest.bundle_hash}"
    )


@app.command("run-openai-compatible")
def run_openai_compatible_command(
    endpoint: Annotated[str, typer.Option(help="OpenAI-compatible server base URL")],
    model_id: Annotated[str, typer.Option(help="Model ID in the eligibility registry")],
    output: Annotated[Path, typer.Option(help="Run output directory")],
    tasks: Annotated[Path, typer.Option(help="Task JSONL file")] = Path(
        "benchmark/tasks/public-anchor.jsonl"
    ),
    registry: Annotated[Path, typer.Option(help="Model registry")] = Path(
        "hf/model-eligibility.json"
    ),
    runtime_profiles: Annotated[Path, typer.Option(help="Runtime profiles")] = Path(
        "hf/runtime-profiles.json"
    ),
    api_key_environment: Annotated[
        str | None, typer.Option(help="Environment variable containing endpoint token")
    ] = None,
    allow_unqualified: Annotated[bool, typer.Option("--allow-unqualified")] = False,
    seed: int = 20260801,
) -> None:
    entries = {item.model_id: item for item in load_registry(registry)}
    if model_id not in entries:
        raise typer.BadParameter(f"model is absent from registry: {model_id}")
    entry = entries[model_id]
    if not entry.eligible and not allow_unqualified:
        raise typer.BadParameter(
            "model is not qualified: " + ", ".join(entry.eligibility_blockers)
        )
    profile = runtime_profile_for_model(load_runtime_profiles(runtime_profiles), model_id)
    if profile is None:
        raise typer.BadParameter(f"no runtime prompt profile matches {model_id}")
    adapter = OpenAICompatibleAdapter(
        endpoint,
        adapter_id=f"openai-compatible:{profile.profile_id}",
        model_id=model_id,
        model_revision=entry.revision,
        api_key_environment=api_key_environment,
        system_prompt=profile.system_prompt,
        first_user_prefix=profile.first_user_prefix,
        assistant_prefill=profile.assistant_prefill,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
    )
    result = run_benchmark(
        load_tasks(tasks),
        adapter,
        output_directory=output,
        seed=seed,
        benchmark_commit="working-tree",
        environment_digest="openai-compatible",
        continue_on_error=True,
    )
    typer.echo(json.dumps(result.manifest.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
