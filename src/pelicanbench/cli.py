"""PelicanBench command-line interface."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from .adapters import CallableAdapter, OpenAICompatibleAdapter
from .assurance import evaluate_release_readiness
from .blinding import (
    blind_jsonl,
    build_blinding_manifests,
    build_unblinding_authorization,
    load_private_blinding_map,
    load_public_blinding_manifest,
    unblind_jsonl,
    verify_blinding_manifests,
    verify_unblinding_authorization,
    write_blinding_manifests,
)
from .calibration import CalibrationCandidate, PairwiseCalibrationTask, build_calibration_design
from .calibration_ops import build_adjudication_queue, evaluate_calibration_stopping
from .campaign import CampaignManifest
from .campaign_store import (
    campaign_store_status,
    export_store_events,
    initialise_campaign_store,
    reclaim_expired_leases,
    reconcile_campaign_store,
)
from .campaign_worker import (
    export_campaign_execution_index,
    reconcile_campaign_execution_records,
)
from .candidate import candidate_commitment_payload, validate_candidate
from .challenge import commit_challenge, reveal_challenge, verify_challenge
from .corpus import annotate_document, corpus_summary
from .design_assurance import build_design_assurance_report
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
from .judge_calibration import evaluate_judge_panel
from .judge_firewall import JudgeFirewallPolicy, evaluate_judge_input
from .metamorphic import run_scorer_challenges
from .pilot import build_pilot_execution_plan, load_tasks, write_pilot_execution_plan
from .power_simulation import simulate_design_power
from .prospective import build_prospective_pilot_plan
from .protocol import verify_study_protocol, write_study_protocol_lock
from .publication import build_publication_bundle
from .qualification import (
    load_default_judge_qualification_plan,
    load_default_model_qualification_plan,
)
from .qualification_runner import run_fixture_model_qualification
from .reassessment import blinded_reassessment, plan_replicate_wave
from .registry import (
    load_registry,
    load_runtime_profiles,
    registry_summary,
    runtime_profile_for_model,
)
from .render import render_svg
from .render_bridge import compare_renderers
from .runner import run_benchmark
from .semantic import StaticSemanticAssessor
from .simon_corpus import fetch_atom, parse_simon_atom, write_simon_atom_corpus
from .study_freeze import (
    authorization_commitments,
    build_study_freeze,
    load_study_freeze,
    verify_study_freeze,
    write_study_freeze,
)
from .svg import inspect_svg
from .taskgen import (
    generate_design_tasks,
    generate_tasks,
    heritage_task,
    load_grammar,
    task_set_commitment,
)
from .validation import validate_repository, validation_exit_code
from .verification import (
    build_repository_verification_receipt,
    validate_repository_verification_receipt,
)

app = typer.Typer(no_args_is_help=True, help="PelicanBench research and evaluation CLI.")


def _required_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise typer.BadParameter(f"required secret environment variable is unset: {name}")
    return value


def _campaign_manifest(path: Path) -> CampaignManifest:
    return CampaignManifest.from_mapping(read_json(path))


def _fixture_svg(_task: object, _seed: int) -> str:
    fixture = (
        Path(__file__).resolve().parents[2] / "benchmark/fixtures/svg/pelican-bicycle-valid.svg"
    )
    return fixture.read_text(encoding="utf-8")


@app.command("validate-repo")
def validate_repo(
    root: Annotated[Path, typer.Option(help="Repository root.")] = Path(),
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
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
    output: Annotated[Path | None, typer.Option(help="Optional JSON destination")] = None,
) -> None:
    payload = candidate_commitment_payload(root)
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("analyse-empirical-prompt-bridge")
def analyse_empirical_prompt_bridge_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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
        f"Wrote {plan.cell_count} cells across {len(plan.stages)} stages to {output} and {detailed}"
    )


@app.command("plan-model-qualification")
def plan_model_qualification_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
    output: Annotated[Path | None, typer.Option(help="Optional plan destination")] = None,
) -> None:
    payload = load_default_model_qualification_plan(root)
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("plan-judge-qualification")
def plan_judge_qualification_command(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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


@app.command("run-fixture-model-qualification")
def run_fixture_model_qualification_command(
    root: Path = Path(),
    model_id: str = "openai/gpt-5.6-terra",
    output: Path = Path("artifacts/model-qualification"),
) -> None:
    payload = run_fixture_model_qualification(
        load_default_model_qualification_plan(root), model_id=model_id, output=output
    )
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command("evaluate-judge-panel")
def evaluate_judge_panel_command(
    root: Path = Path(),
    config: Path = Path("benchmark/judges/calibration-policy.json"),
    source: Path = Path("benchmark/fixtures/design/judge-calibration-observations.jsonl"),
    output: Path = Path("artifacts/judge-panel-calibration.json"),
    require_empirical: bool = False,
) -> None:
    del root
    payload = evaluate_judge_panel(
        read_jsonl(source), read_json(config), require_empirical=require_empirical
    )
    write_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))


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
    payload = (
        source.read_bytes()
        if source is not None
        else fetch_atom(url, timeout_seconds=timeout_seconds)
    )
    corpus = parse_simon_atom(payload, rights_status=rights_status, include_content=include_content)
    records, summary = write_simon_atom_corpus(corpus, output)
    typer.echo(f"Wrote {corpus.entry_count} entries to {records}; summary {summary}")


@app.command("release-readiness")
def release_readiness_command(
    profile: Annotated[str, typer.Option(help="Release assurance profile")] = "v0.4-alpha",
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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
    output: Annotated[Path, typer.Option(help="Destination JSONL file")] = Path(
        "benchmark/tasks/v1-pilot.jsonl"
    ),
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
    source: Annotated[Path, typer.Option(help="Baseline SVG source file")] = Path(
        "benchmark/fixtures/svg/pelican-bicycle-valid.svg"
    ),
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
    source: Annotated[Path, typer.Option(help="Baseline SVG source file")] = Path(
        "benchmark/fixtures/svg/pelican-bicycle-valid.svg"
    ),
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
    source: Annotated[Path, typer.Option(help="Candidate artifact JSONL")],
    output: Annotated[Path, typer.Option(help="Calibration design JSON destination")],
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
    output: Annotated[Path, typer.Option(help="Privacy-minimised evaluation package directory")],
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
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
    registry: Annotated[Path, typer.Option(help="Machine-readable integration registry")] = Path(
        "benchmark/integrations/ecosystem-registry.json"
    ),
    output: Annotated[Path | None, typer.Option(help="Optional audit report destination")] = None,
) -> None:
    report = audit_ecosystem(root, load_ecosystem_registry(registry))
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("model-registry-status")
def model_registry_status_command(
    registry: Annotated[Path, typer.Option(help="Model eligibility registry")] = Path(
        "hf/model-eligibility.json"
    ),
    runtime_profiles: Annotated[Path, typer.Option(help="Runtime prompt-profile registry")] = Path(
        "hf/runtime-profiles.json"
    ),
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
    profile: Annotated[Path, typer.Option(help="Ontology interoperability profile")] = Path(
        "benchmark/ontologies/interoperability-profile.json"
    ),
) -> None:
    value = load_ontology_interoperability_profile(profile)
    typer.echo(json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command("plan-pilot")
def plan_pilot_command(
    output: Annotated[Path, typer.Option(help="Execution-plan JSON destination")],
    tasks: Annotated[Path, typer.Option(help="Prespecified pilot task JSONL")] = Path(
        "benchmark/tasks/v1-pilot.jsonl"
    ),
    registry: Annotated[Path, typer.Option(help="Model eligibility registry")] = Path(
        "hf/model-eligibility.json"
    ),
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
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
    coverage: Annotated[Path, typer.Option(help="Coverage XML path")] = Path("coverage.xml"),
    artifact: Annotated[
        list[Path] | None, typer.Option(help="Additional evidence artifact")
    ] = None,
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
    typer.echo(
        json.dumps(receipt.model_dump(mode="json", exclude_none=True), indent=2, sort_keys=True)
    )
    raise typer.Exit(0 if receipt.result != "fail" else 1)


@app.command("publication-bundle")
def publication_bundle_command(
    output: Annotated[Path, typer.Option(help="Publication bundle directory")],
    root: Annotated[Path, typer.Option(help="Repository root")] = Path(),
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
        raise typer.BadParameter("model is not qualified: " + ", ".join(entry.eligibility_blockers))
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


@app.command("build-model-blinding")
def build_model_blinding_command(
    root: Path = Path(),
    public_output: Path = Path("benchmark/blinding/public.json"),
    private_output: Path = Path("benchmark/blinding/restricted/private.json"),
    key_environment: str = "PELICANBENCH_BLINDING_KEY",
) -> None:
    panel = read_json(root / "benchmark/models/prospective-panel.json")
    cohort = next(
        item for item in panel["cohorts"] if item["cohort_id"] == "castillo-2026-replication-seven"
    )
    model_ids = sorted(str(model) for model in cohort["models"])
    commitment = str(read_json(root / "benchmark/tasks/v1-candidate-commitment.json")["commitment"])
    public, private = build_blinding_manifests(
        model_ids,
        key=_required_secret(key_environment),
        study_id="pelicanbench-v1",
        task_identity_commitment=commitment,
    )
    write_blinding_manifests(public_output, private_output, public, private)
    typer.echo(
        json.dumps(
            verify_blinding_manifests(
                public, private, key=_required_secret(key_environment), require_key=True
            ).as_dict(),
            sort_keys=True,
        )
    )


@app.command("verify-model-blinding")
def verify_model_blinding_command(
    public: Path = Path("public.json"),
    private: Path = Path("private.json"),
    key_environment: str = "PELICANBENCH_BLINDING_KEY",
    output: Path | None = None,
) -> None:
    report = verify_blinding_manifests(
        load_public_blinding_manifest(public),
        load_private_blinding_map(private),
        key=_required_secret(key_environment),
        require_key=True,
    )
    if output is not None:
        write_json(output, report.as_dict())
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("blind-model-records")
def blind_model_records_command(
    source: Path = Path("records.jsonl"),
    destination: Path = Path("blinded.jsonl"),
    private: Path = Path("private.json"),
) -> None:
    typer.echo(json.dumps({"records": blind_jsonl(source, destination, private)}))


@app.command("unblind-model-records")
def unblind_model_records_command(
    source: Path = Path("blinded.jsonl"),
    destination: Path = Path("unblinded.jsonl"),
    private: Path = Path("private.json"),
    authorization: Path = Path("authorization.json"),
    key_environment: str = "PELICANBENCH_BLINDING_KEY",
) -> None:
    count = unblind_jsonl(
        source,
        destination,
        private,
        authorization,
        key=_required_secret(key_environment),
    )
    typer.echo(json.dumps({"records": count}))


@app.command("build-study-freeze")
def build_study_freeze_command(
    root: Path = Path(),
    output: Path = Path("artifacts/study-freeze.json"),
    freeze_type: str = "analysis-lock",
    input: list[Path] | None = None,
    ledger_head: Path | None = None,
    generated_at: str | None = None,
) -> None:
    commitment = str(read_json(root / "benchmark/tasks/v1-candidate-commitment.json")["commitment"])
    ledger = (
        read_json(root / ledger_head)
        if ledger_head is not None and not ledger_head.is_absolute()
        else (read_json(ledger_head) if ledger_head is not None else None)
    )
    manifest = build_study_freeze(
        root,
        tuple(input or ()),
        study_id="pelicanbench-v1",
        freeze_type=freeze_type,  # type: ignore[arg-type]
        task_identity_commitment=commitment,
        ledger_head=ledger,
        generated_at=generated_at,
    )
    write_study_freeze(output, manifest)
    report = verify_study_freeze(root, manifest)
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("verify-study-freeze")
def verify_study_freeze_command(
    root: Path = Path(),
    manifest: Path | None = None,
    lock: Path | None = None,
    output: Path | None = None,
) -> None:
    selected = manifest or lock
    if selected is None:
        raise typer.BadParameter("a manifest or lock path is required")
    report = verify_study_freeze(root, load_study_freeze(selected))
    if output is not None:
        write_json(output, report.as_dict())
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.passed else 1)


@app.command("authorize-model-unblinding-from-freezes")
def authorize_model_unblinding_from_freezes_command(
    root: Path = Path(),
    private: Path = Path("private.json"),
    analysis_lock: Path = Path("analysis-lock.json"),
    data_freeze: Path = Path("data-freeze.json"),
    output: Path = Path("authorization.json"),
    authorized_by: str = "",
    reason: str = "",
    key_environment: str = "PELICANBENCH_BLINDING_KEY",
) -> None:
    analysis = load_study_freeze(analysis_lock)
    data = load_study_freeze(data_freeze)
    if not verify_study_freeze(root, analysis).passed or not verify_study_freeze(root, data).passed:
        raise typer.BadParameter("analysis lock and data freeze must both verify")
    analysis_commitment, data_commitment = authorization_commitments(analysis, data)
    private_value = load_private_blinding_map(private)
    receipt = build_unblinding_authorization(
        key=_required_secret(key_environment),
        private=private_value,
        analysis_lock_commitment=analysis_commitment,
        data_freeze_commitment=data_commitment,
        authorized_by=authorized_by,
        reason=reason,
    )
    write_json(output, receipt.as_dict())
    output.chmod(0o600)
    typer.echo(json.dumps({"passed": True, **receipt.as_dict()}, sort_keys=True))


@app.command("verify-model-unblinding-authorization")
def verify_model_unblinding_authorization_command(
    private: Path = Path("private.json"),
    authorization: Path = Path("authorization.json"),
    key_environment: str = "PELICANBENCH_BLINDING_KEY",
) -> None:
    passed = verify_unblinding_authorization(
        read_json(authorization),
        key=_required_secret(key_environment),
        private=load_private_blinding_map(private),
    )
    typer.echo(json.dumps({"passed": passed}))
    raise typer.Exit(0 if passed else 1)


@app.command("judge-firewall")
def judge_firewall_command(
    root: Path = Path(),
    source: Path = Path("submission.svg"),
    output: Path = Path("artifacts/judge-firewall.json"),
) -> None:
    svg = source.read_text(encoding="utf-8")
    inspection = inspect_svg(svg)
    rendered = render_svg(svg, inspection=inspection) if inspection.valid else None
    report = evaluate_judge_input(svg, inspection, rendered, policy=JudgeFirewallPolicy())
    write_json(output, report.as_dict())
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.eligible else 1)


@app.command("build-calibration-adjudication")
def build_calibration_adjudication_command(
    root: Path = Path(),
    source: Path = Path("responses.jsonl"),
    output: Path = Path("artifacts/adjudication.jsonl"),
) -> None:
    items = build_adjudication_queue(read_jsonl(source))
    write_jsonl(output, [item.as_dict() for item in items])
    typer.echo(json.dumps({"items": len(items)}))


@app.command("evaluate-calibration-stopping")
def evaluate_calibration_stopping_command(
    root: Path = Path(),
    analysis: Path = Path("analysis.json"),
    output: Path = Path("artifacts/stopping.json"),
) -> None:
    policy = read_json(root / "benchmark/human-calibration/operations-policy.json")
    report = evaluate_calibration_stopping(read_json(analysis), policy)
    write_json(output, report.as_dict())
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))


@app.command("design-assurance")
def design_assurance_command(root: Path = Path(), output: Path | None = None) -> None:
    report = build_design_assurance_report(
        read_jsonl(root / "benchmark/tasks/v1-candidate.jsonl"),
        read_json(root / "benchmark/models/prospective-panel.json"),
        read_json(root / "benchmark/human-calibration/study-spec.json"),
        read_json(root / "benchmark/design/assumptions.json"),
    )
    payload = report.as_dict()
    if output is not None:
        write_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command("build-campaign-manifest")
def build_campaign_manifest_command(
    root: Path = Path(),
    output: Path = Path("artifacts/campaign-manifest.json"),
    summary_output: Path = Path("artifacts/campaign-summary.json"),
) -> None:
    from .campaign import CampaignPolicy, build_campaign_manifest

    tasks = load_tasks(root / "benchmark/tasks/v1-candidate.jsonl")
    panel = read_json(root / "benchmark/models/prospective-panel.json")
    commitment = str(read_json(root / "benchmark/tasks/v1-candidate-commitment.json")["commitment"])
    plan = build_prospective_pilot_plan(
        tasks, panel, task_identity_commitment=commitment, replicates=3
    )
    models = {cell.model_id: False for cell in plan.cells}
    policy = CampaignPolicy(**read_json(root / "benchmark/campaign/policy.json"))
    manifest = build_campaign_manifest(plan, qualified_models=models, policy=policy)
    write_json(output, manifest.as_dict())
    write_json(summary_output, manifest.summary())
    typer.echo(json.dumps(manifest.summary(), sort_keys=True))


@app.command("campaign-status")
def campaign_status_command(manifest: Path = Path("manifest.json")) -> None:
    from .campaign import campaign_status

    typer.echo(json.dumps(campaign_status(_campaign_manifest(manifest)).as_dict(), sort_keys=True))


@app.command("study-protocol-lock")
def study_protocol_lock_command(
    root: Path = Path(), output: Path = Path("artifacts/study-protocol-lock.json")
) -> None:
    write_study_protocol_lock(root, output)
    typer.echo(str(output))


@app.command("verify-study-protocol")
def verify_study_protocol_command(
    root: Path = Path(),
    lock: Path = Path("artifacts/study-protocol-lock.json"),
    output: Path | None = None,
) -> None:
    report = verify_study_protocol(root, lock)
    if output is not None:
        write_json(output, report.as_dict())
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.valid else 1)


@app.command("simulate-design-power")
def simulate_design_power_command(
    root: Path = Path(),
    spec: Path = Path("benchmark/design/power-simulation.json"),
    output: Path = Path("artifacts/power-simulation.json"),
) -> None:
    payload = simulate_design_power(read_json(spec))
    write_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command("blinded-replicate-reassessment")
def blinded_replicate_reassessment_command(
    root: Path = Path(),
    source: Path = Path("benchmark/fixtures/design/blinded-reassessment.jsonl"),
    tasks_per_model: int = 64,
    policy: Path = Path("benchmark/design/replicate-reassessment.json"),
    output: Path = Path("artifacts/blinded-reassessment.json"),
) -> None:
    payload = blinded_reassessment(
        read_jsonl(source), tasks_per_model=tasks_per_model, policy=read_json(policy)
    )
    write_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command("plan-replicate-wave")
def plan_replicate_wave_command(
    root: Path = Path(),
    target_replicates: int = 5,
    output: Path = Path("artifacts/replicate-wave.json"),
) -> None:
    panel = read_json(root / "benchmark/models/prospective-panel.json")
    models = len(
        next(x for x in panel["cohorts"] if x["cohort_id"] == "core-prospective-six")["models"]
    )
    tasks = len(read_jsonl(root / "benchmark/tasks/v1-candidate.jsonl"))
    payload = plan_replicate_wave(
        models=models, tasks=tasks, current_replicates=3, target_replicates=target_replicates
    )
    write_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command("commit-sealed-challenge")
def commit_sealed_challenge_command(
    tasks: Path = Path("challenge-tasks.jsonl"),
    output: Path = Path("commitment.json"),
    secrets_output: Path = Path("restricted/challenge-secrets.json"),
    release: str = "PB-CHALLENGE",
    fixture_seed: int = 0,
    created_at: str = "2026-08-03T00:00:00Z",
    root: Path = Path(),
) -> None:
    public, secrets = commit_challenge(
        read_jsonl(tasks), release=release, seed=fixture_seed, created_at=created_at
    )
    write_json(output, public)
    write_json(secrets_output, secrets)
    secrets_output.chmod(0o600)
    typer.echo(json.dumps(public, sort_keys=True))


@app.command("reveal-sealed-challenge")
def reveal_sealed_challenge_command(
    commitment: Path = Path("commitment.json"),
    tasks: Path = Path("challenge-tasks.jsonl"),
    secrets_source: Path = Path("restricted/challenge-secrets.json"),
    output: Path = Path("reveals.jsonl"),
) -> None:
    values = reveal_challenge(read_json(commitment), read_jsonl(tasks), read_json(secrets_source))
    write_jsonl(output, values)
    typer.echo(str(output))


@app.command("verify-sealed-challenge")
def verify_sealed_challenge_command(
    commitment: Path = Path("commitment.json"),
    reveal: Path = Path("reveals.jsonl"),
    require_full: bool = False,
) -> None:
    payload = verify_challenge(read_json(commitment), read_jsonl(reveal), require_full=require_full)
    typer.echo(json.dumps(payload, sort_keys=True))
    raise typer.Exit(0 if payload["valid"] else 1)


@app.command("init-campaign-store")
def init_campaign_store_command(
    manifest: Path = Path("manifest.json"), database: Path = Path("campaign.sqlite")
) -> None:
    typer.echo(
        json.dumps(
            initialise_campaign_store(database, _campaign_manifest(manifest)).as_dict(),
            sort_keys=True,
        )
    )


@app.command("campaign-store-status")
def campaign_store_status_command(
    manifest: Path = Path("manifest.json"), database: Path = Path("campaign.sqlite")
) -> None:
    typer.echo(
        json.dumps(
            campaign_store_status(database, _campaign_manifest(manifest)).as_dict(), sort_keys=True
        )
    )


@app.command("reconcile-campaign-store")
def reconcile_campaign_store_command(
    manifest: Path = Path("manifest.json"), database: Path = Path("campaign.sqlite")
) -> None:
    report = reconcile_campaign_store(database, _campaign_manifest(manifest))
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.valid else 1)


@app.command("export-campaign-store-events")
def export_campaign_store_events_command(
    database: Path = Path("campaign.sqlite"), output: Path = Path("events.jsonl")
) -> None:
    export_store_events(database, output)
    typer.echo(str(output))


@app.command("reclaim-campaign-leases")
def reclaim_campaign_leases_command(
    manifest: Path = Path("manifest.json"), database: Path = Path("campaign.sqlite")
) -> None:
    events = reclaim_expired_leases(database, _campaign_manifest(manifest))
    typer.echo(json.dumps({"reclaimed": len(events)}))


@app.command("run-fixture-campaign-worker")
def run_fixture_campaign_worker_command(
    manifest: Path = Path("manifest.json"),
    database: Path = Path("campaign.sqlite"),
    tasks: Path = Path("tasks.jsonl"),
    model_id: str = "fixture/model",
    output: Path = Path("runs"),
    now: str | None = None,
) -> None:
    from .campaign_worker import execute_campaign_batch

    adapter = CallableAdapter(_fixture_svg, model_id=model_id)
    payload = execute_campaign_batch(
        database,
        _campaign_manifest(manifest),
        load_tasks(tasks),
        adapter,
        worker_id="fixture-worker",
        output_directory=output,
        limit=1,
        semantic_assessor=StaticSemanticAssessor(),
        now=now,
    )
    typer.echo(json.dumps(payload.as_dict(), sort_keys=True))


@app.command("export-campaign-executions")
def export_campaign_executions_command(
    campaign_output: Path = Path("runs"), output: Path = Path("executions.jsonl")
) -> None:
    export_campaign_execution_index(campaign_output, output)
    typer.echo(str(output))


@app.command("reconcile-campaign-executions")
def reconcile_campaign_executions_command(
    manifest: Path = Path("manifest.json"),
    database: Path = Path("campaign.sqlite"),
    campaign_output: Path = Path("runs"),
) -> None:
    report = reconcile_campaign_execution_records(
        database, _campaign_manifest(manifest), campaign_output
    )
    typer.echo(json.dumps(report.as_dict(), sort_keys=True))
    raise typer.Exit(0 if report.valid else 1)


if __name__ == "__main__":
    app()
