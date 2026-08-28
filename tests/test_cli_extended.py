from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from pelicanbench.cli import app

runner = CliRunner()


def _patch_openai_compatible_run(monkeypatch, calls: list[tuple[Path, int]]) -> None:
    entry = SimpleNamespace(
        model_id="fixture/model",
        eligible=True,
        eligibility_blockers=(),
        revision="fixture-revision",
    )
    profile = SimpleNamespace(
        profile_id="fixture-profile",
        system_prompt="system",
        first_user_prefix="",
        assistant_prefill="",
        temperature=0.0,
        max_tokens=256,
        timeout_seconds=45,
    )
    monkeypatch.setattr("pelicanbench.cli.load_registry", lambda _path: [entry])
    monkeypatch.setattr("pelicanbench.cli.load_runtime_profiles", lambda _path: object())
    monkeypatch.setattr(
        "pelicanbench.cli.runtime_profile_for_model", lambda _profiles, _model_id: profile
    )
    monkeypatch.setattr("pelicanbench.cli.load_tasks", lambda _path: (object(),))

    def fake_run_benchmark(_tasks, _adapter, *, output_directory, seed, **_kwargs):
        calls.append((Path(output_directory), seed))
        manifest = SimpleNamespace(model_dump=lambda **_kwargs: {"run_id": f"run-{len(calls)}"})
        return SimpleNamespace(manifest=manifest)

    monkeypatch.setattr("pelicanbench.cli.run_benchmark", fake_run_benchmark)


def test_validate_and_json_readiness_commands(root: Path):
    validated = runner.invoke(app, ["validate-repo", "--root", str(root)])
    assert validated.exit_code == 0, validated.output

    ontology = runner.invoke(
        app,
        [
            "ontology-interoperability-status",
            "--profile",
            str(root / "benchmark/ontologies/interoperability-profile.json"),
        ],
    )
    assert ontology.exit_code == 0, ontology.output
    ontology_payload = json.loads(ontology.output)
    assert ontology_payload["namespace_status"] == "registration-planned"
    assert "Repository contract valid" in validated.output

    readiness = runner.invoke(
        app,
        ["release-readiness", "--root", str(root), "--profile", "v0.2-alpha", "--json"],
    )
    assert readiness.exit_code == 0, readiness.output
    assert json.loads(readiness.output)["ready"] is True


def test_generate_prespecified_pilot_command(tmp_path: Path, root: Path):
    output = tmp_path / "pilot.jsonl"
    result = runner.invoke(
        app,
        [
            "generate-v1-pilot",
            "--output",
            str(output),
            "--design",
            str(root / "benchmark/tasks/v1-pilot-design.json"),
            "--grammar",
            str(root / "benchmark/tasks/grammar.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(output.read_text().splitlines()) == 33
    commitment = json.loads((tmp_path / "pilot-commitment.json").read_text())
    assert commitment["task_count"] == 33


def test_run_openai_compatible_replicate_waves(tmp_path: Path, monkeypatch):
    calls: list[tuple[Path, int]] = []
    _patch_openai_compatible_run(monkeypatch, calls)
    output = tmp_path / "run"

    result = runner.invoke(
        app,
        [
            "run-openai-compatible",
            "--endpoint",
            "https://example.invalid/v1",
            "--model-id",
            "fixture/model",
            "--output",
            str(output),
            "--replicates",
            "2",
            "--seed",
            "17",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (output / "replicate-01", 17),
        (output / "replicate-02", 2_000_017),
    ]
    assert '"replicate_index": 1' in result.output
    assert '"replicate_seed": 2000017' in result.output


def test_run_openai_compatible_refuses_nonempty_replicate(tmp_path: Path, monkeypatch):
    calls: list[tuple[Path, int]] = []
    _patch_openai_compatible_run(monkeypatch, calls)
    output = tmp_path / "run"
    occupied = output / "replicate-02"
    occupied.mkdir(parents=True)
    (occupied / "retained.json").write_text("{}\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run-openai-compatible",
            "--endpoint",
            "https://example.invalid/v1",
            "--model-id",
            "fixture/model",
            "--output",
            str(output),
            "--replicates",
            "2",
        ],
    )

    assert result.exit_code != 0
    assert "refusing to overwrite existing run output directory" in result.output
    assert calls == []


@pytest.mark.skipif(shutil.which("inkscape") is None, reason="Inkscape not installed")
def test_renderer_bridge_and_scorer_challenge_commands(tmp_path: Path, root: Path):
    source = root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg"
    bridge = runner.invoke(app, ["renderer-bridge", "--source", str(source), "--size", "128"])
    assert bridge.exit_code == 0, bridge.output
    assert json.loads(bridge.output)["materially_different"] is False

    report_path = tmp_path / "challenge.json"
    challenge = runner.invoke(
        app,
        ["scorer-challenges", "--source", str(source), "--output", str(report_path)],
    )
    assert challenge.exit_code == 0, challenge.output
    assert json.loads(report_path.read_text())["passed"] is True


def test_design_human_calibration_command(tmp_path: Path):
    candidates = tmp_path / "candidates.jsonl"
    rows = []
    for index, model in enumerate(("m1", "m2", "m3"), 1):
        rows.append(
            {
                "artifact_id": f"a{index}",
                "task_id": "task-1",
                "scenario_id": "scenario-1",
                "model_id": model,
                "interface_stratum": "sit-inside-and-control",
                "automatic_score": 0.2 + index * 0.2,
                "judge_disagreement": 0.1 * index,
            }
        )
    candidates.write_text("".join(json.dumps(row) + "\n" for row in rows))
    output = tmp_path / "calibration.json"
    result = runner.invoke(
        app,
        [
            "design-human-calibration",
            "--source",
            str(candidates),
            "--output",
            str(output),
            "--target",
            "3",
            "--seed",
            "8",
        ],
    )
    assert result.exit_code == 0, result.output
    design = json.loads(output.read_text())
    assert design["selected_artifacts"] == 3
    assert len(design["pairs"]) == 15

    batch = tmp_path / "human-batch"
    exported = runner.invoke(
        app,
        [
            "export-human-evaluation-batch",
            "--design",
            str(output),
            "--output",
            str(batch),
        ],
    )
    assert exported.exit_code == 0, exported.output
    assignments = batch / "assignments.csv"
    lines = assignments.read_text().splitlines()
    # Add two replicate votes for the first pair while retaining the privacy-minimised schema.
    header = lines[0]
    first = lines[1].split(",")
    winner_index = header.split(",").index("winner")
    rater_index = header.split(",").index("rater_hash")
    first[winner_index] = "A"
    first[rater_index] = "0000000000000001"
    second = list(first)
    second[rater_index] = "0000000000000002"
    assignments.write_text(
        header + "\n" + ",".join(first) + "\n" + ",".join(second) + "\n",
        encoding="utf-8",
    )
    analysed = runner.invoke(app, ["analyse-human-evaluation", "--source", str(assignments)])
    assert analysed.exit_code == 0, analysed.output
    payload = json.loads(analysed.output)
    assert payload["vote_count"] == 2


def test_ecosystem_pilot_and_publication_commands(tmp_path: Path, root: Path):
    audit = runner.invoke(
        app,
        [
            "ecosystem-audit",
            "--root",
            str(root),
            "--registry",
            str(root / "benchmark/integrations/ecosystem-registry.json"),
        ],
    )
    assert audit.exit_code == 0, audit.output
    assert json.loads(audit.output)["passed"] is True

    plan = tmp_path / "pilot-plan.json"
    planned = runner.invoke(
        app,
        [
            "plan-pilot",
            "--output",
            str(plan),
            "--tasks",
            str(root / "benchmark/tasks/v1-pilot.jsonl"),
            "--registry",
            str(root / "hf/model-eligibility.json"),
        ],
    )
    assert planned.exit_code == 0, planned.output
    plan_payload = json.loads(plan.read_text())
    assert plan_payload["model_count"] == 7
    assert plan_payload["cell_count"] == 693
    assert plan_payload["ready_cell_count"] == 495
    assert plan_payload["qualification_required_cell_count"] == 198

    bundle = tmp_path / "publication"
    published = runner.invoke(
        app,
        ["publication-bundle", "--root", str(root), "--output", str(bundle)],
    )
    assert published.exit_code == 0, published.output
    assert (bundle / "manifest.json").exists()
