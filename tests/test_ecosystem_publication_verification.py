from __future__ import annotations

import json
from pathlib import Path

from pelicanbench.ecosystem import (
    EcosystemRegistry,
    audit_ecosystem,
    load_ecosystem_registry,
)
from pelicanbench.interoperability import load_ontology_interoperability_profile
from pelicanbench.pilot import build_pilot_execution_plan, load_tasks
from pelicanbench.publication import build_publication_bundle, default_publication_plan
from pelicanbench.registry import load_registry, load_runtime_profiles, runtime_profile_for_model
from pelicanbench.verification import (
    build_repository_verification_receipt,
    coverage_metrics,
    validate_repository_verification_receipt,
)


def test_ecosystem_registry_is_complete_and_auditable(root: Path):
    registry = load_ecosystem_registry(root / "benchmark/integrations/ecosystem-registry.json")
    report = audit_ecosystem(root, registry)
    assert report.passed
    assert report.asset_count >= 40
    assert report.status_counts["implemented"] >= 5
    names = {item.name for item in registry.assets}
    assert {
        "edithatogo/repository-standards",
        "edithatogo/sourceright",
        "edithatogo/authentext",
        "edithatogo/osf-cli-go",
        "edithatogo/substack-cli-ts",
        "edithatogo/hermes-training",
        "edithatogo/qwen3-4b-hermes-lora",
        "edithatogo/UOGTO",
        "edithatogo/codev",
        "edithatogo/ralph-codex",
        "edithatogo/fyi-cli",
        "edithatogo/fyi-archive",
        "edithatogo/postiz-agent",
        "edithatogo/w3id.org",
    } <= names
    assert registry.excluded_families


def test_ecosystem_audit_detects_missing_declared_evidence(root: Path):
    registry = load_ecosystem_registry(root / "benchmark/integrations/ecosystem-registry.json")
    value = registry.model_dump(mode="json")
    value["assets"][0]["evidence"].append("does/not/exist")
    broken = EcosystemRegistry.model_validate(value)
    report = audit_ecosystem(root, broken)
    assert not report.passed
    assert any(item.code == "missing-integration-evidence" for item in report.findings)


def test_first_party_runtime_profiles_are_explicit(root: Path):
    models = load_registry(root / "hf/model-eligibility.json")
    profiles = load_runtime_profiles(root / "hf/runtime-profiles.json")
    by_id = {item.model_id: item for item in models}
    first_party = by_id["edithatogo/qwen3-4b-hermes-lora"]
    assert not first_party.eligible
    assert "revision-unresolved" in first_party.eligibility_blockers
    profile = runtime_profile_for_model(profiles, first_party.model_id)
    assert profile is not None
    assert profile.first_user_prefix.startswith("/no_think")
    assert "<think>" in profile.assistant_prefill


def test_pilot_plan_retains_qualification_gates(root: Path):
    tasks = load_tasks(root / "benchmark/tasks/v1-pilot.jsonl")
    models = load_registry(root / "hf/model-eligibility.json")
    plan = build_pilot_execution_plan(tasks, models, replicates=3, base_seed=9)
    assert plan.task_count == 33
    assert plan.model_count == 3
    assert plan.cell_count == 297
    assert plan.ready_cell_count == 99
    assert plan.qualification_required_cell_count == 198
    repeated = build_pilot_execution_plan(list(reversed(tasks)), models, replicates=3, base_seed=9)
    first = {(item.model_id, item.task_id, item.replicate): item.seed for item in plan.cells}
    second = {(item.model_id, item.task_id, item.replicate): item.seed for item in repeated.cells}
    assert first == second


def test_publication_bundle_is_deterministic_and_never_writes_externally(
    root: Path, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    first = build_publication_bundle(root, tmp_path / "first")
    second = build_publication_bundle(root, tmp_path / "second")
    assert first.bundle_hash == second.bundle_hash
    assert not first.external_writes_executed
    assert (tmp_path / "first/references/references.csl.json").exists()
    assert (tmp_path / "first/.sourceright/references.csl.json").exists()
    assert (
        (tmp_path / "first/references/references.csl.json").read_bytes()
        == (tmp_path / "first/.sourceright/references.csl.json").read_bytes()
    )
    assert (tmp_path / "first/arxiv/paper/metadata.json").exists()
    assert (tmp_path / "first/candidate/v1-candidate-commitment.json").exists()
    assert (tmp_path / "first/candidate/v1-candidate.jsonl").exists()
    assert (tmp_path / "first/candidate/human-calibration-study-spec.json").exists()
    assert (tmp_path / "first/evidence/prospective-pilot-plan.json").exists()
    assert (tmp_path / "first/evidence/historical/v1-pilot-commitment.json").exists()
    assert (tmp_path / "first/review/authentext-brief.md").exists()
    assert (tmp_path / "first/osf/project-metadata.json").exists()
    postiz_template = tmp_path / "first/distribution/postiz-post-template.json"
    assert postiz_template.exists()
    postiz = json.loads(postiz_template.read_text(encoding="utf-8"))
    assert postiz["status"] == "template-only-not-approved-for-write"
    assert postiz["safety"]["automatic_execution_permitted"] is False
    assert (tmp_path / "first/SHA256SUMS").exists()
    csl = json.loads((tmp_path / "first/references/references.csl.json").read_text())
    assert {item["id"] for item in csl} >= {"simon-tag-archive", "rareinsights-agentic"}
    plan = default_publication_plan()
    report_action = next(item for item in plan.actions if item.action_id == "sourceright-report")
    assert report_action.command[-1] == ".sourceright"
    postiz_action = next(item for item in plan.actions if item.action_id == "postiz-social-draft")
    assert postiz_action.mode == "manual-write"
    assert postiz_action.approval_required
    assert postiz_action.writes_external
    assert all(
        not action.writes_external or (action.mode == "manual-write" and action.approval_required)
        for action in plan.actions
    )


def test_ontology_interoperability_is_formal_but_does_not_overclaim_publication(root: Path):
    profile = load_ontology_interoperability_profile(
        root / "benchmark/ontologies/interoperability-profile.json"
    )
    assert profile.namespace == "https://w3id.org/pelicanbench/ontology#"
    assert profile.namespace_status == "registration-planned"
    assert profile.registration_target == "github:edithatogo/w3id.org"
    assert profile.registration_evidence is None
    by_asset = {item.asset_id: item for item in profile.sources}
    assert by_asset["github:edithatogo/UOGTO"].role == "design-pattern"
    assert by_asset["github:edithatogo/UOGTO"].semantic_import is False
    assert by_asset["github:edithatogo/w3id.org"].role == "namespace-host"
    context = json.loads(
        (root / "benchmark/ontologies/context.jsonld").read_text(encoding="utf-8")
    )
    assert context["@context"]["pb"] == profile.namespace
    assert f"<{profile.namespace}>" in (
        root / "benchmark/ontologies/shapes.ttl"
    ).read_text(encoding="utf-8")


def test_repository_standards_receipt_contract(root: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    coverage = tmp_path / "coverage.xml"
    coverage.write_text(
        '<?xml version="1.0" ?><coverage line-rate="0.95" branch-rate="0.91"></coverage>',
        encoding="utf-8",
    )
    metrics = coverage_metrics(coverage)
    assert metrics.line_coverage_percent == 95
    receipt = build_repository_verification_receipt(
        root,
        coverage_path=coverage,
        revision="1234567",
    )
    assert receipt.generated_at == "1970-01-01T00:00:00Z"
    assert receipt.result in {"pass", "partial"}
    validate_repository_verification_receipt(
        receipt,
        root / "benchmark/schemas/repository-verification-receipt.schema.json",
    )


def test_publication_contract_rejects_malformed_sources_and_unsafe_destinations(
    root: Path, tmp_path: Path
):
    import pytest

    from pelicanbench.publication import source_registry_to_csl

    with pytest.raises(TypeError, match="sources must be a list"):
        source_registry_to_csl({"sources": {}})
    with pytest.raises(TypeError, match="source records must be objects"):
        source_registry_to_csl({"sources": ["not-an-object"]})

    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "sentinel").write_text("occupied", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build_publication_bundle(root, destination)
    manifest = build_publication_bundle(root, destination, overwrite=True)
    assert manifest.files
    assert not (destination / "sentinel").exists()

    missing_root = tmp_path / "missing-root"
    missing_root.mkdir()
    with pytest.raises(FileNotFoundError):
        build_publication_bundle(missing_root, tmp_path / "missing-output")

    with pytest.raises(FileNotFoundError):
        build_publication_bundle(
            root,
            tmp_path / "bad-artifact",
            include_artifacts=(tmp_path / "absent-evidence.json",),
        )


def test_verification_receipt_missing_and_failure_branches(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    from pelicanbench import verification as verification_module

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(verification_module, "validate_repository", lambda _root: [])
    monkeypatch.setattr(
        verification_module,
        "evaluate_release_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True),
    )
    partial = build_repository_verification_receipt(project, revision="1234567")
    assert partial.result == "partial"
    assert {item.result for item in partial.checks} == {"pass", "skip"}

    # An ordinary non-Git directory must fall back to the explicit working-tree marker.
    assert verification_module._git_revision(project) == "working-tree"

    coverage = tmp_path / "external-coverage.xml"
    coverage.write_text(
        '<?xml version="1.0"?><coverage line-rate="0.40" branch-rate="0.20"/>',
        encoding="utf-8",
    )
    artifacts = project / "artifacts"
    artifacts.mkdir()
    (artifacts / "scorer-challenge-report.json").write_text("[]\n", encoding="utf-8")
    (artifacts / "svg-fuzz-report.json").write_text('{"passed":false}\n', encoding="utf-8")
    failed = build_repository_verification_receipt(
        project,
        revision="1234567",
        coverage_path=coverage,
        artifact_paths=(coverage, coverage, project / "missing.file"),
    )
    assert failed.result == "fail"
    coverage_check = next(item for item in failed.checks if item.name == "python-coverage-threshold")
    assert coverage_check.evidence == coverage.as_posix()
    assert len(failed.artifacts) == 1


def test_verification_receipt_can_reach_full_pass(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    from pelicanbench import verification as verification_module

    project = tmp_path / "project"
    registry = project / "benchmark/integrations/ecosystem-registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text("{}\n", encoding="utf-8")
    coverage = project / "coverage.xml"
    coverage.write_text(
        '<?xml version="1.0"?><coverage line-rate="0.99" branch-rate="0.95"/>',
        encoding="utf-8",
    )
    artifacts = project / "artifacts"
    artifacts.mkdir()
    for name in ("scorer-challenge-report.json", "svg-fuzz-report.json"):
        (artifacts / name).write_text('{"passed":true}\n', encoding="utf-8")

    monkeypatch.setattr(verification_module, "validate_repository", lambda _root: [])
    monkeypatch.setattr(
        verification_module,
        "evaluate_release_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(verification_module, "load_ecosystem_registry", lambda _path: object())
    monkeypatch.setattr(
        verification_module,
        "audit_ecosystem",
        lambda *_args, **_kwargs: SimpleNamespace(passed=True),
    )
    monkeypatch.setattr(
        verification_module,
        "_git_revision",
        lambda _root: "abcdef1234567890",
    )
    receipt = build_repository_verification_receipt(project, seed=None)
    assert receipt.result == "pass"
    assert receipt.revision == "abcdef1234567890"
    assert all(item.result == "pass" for item in receipt.checks)
