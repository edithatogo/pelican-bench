from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pelicanbench.cli import app

runner = CliRunner()


def test_validate_and_json_readiness_commands(root: Path):
    validated = runner.invoke(app, ["validate-repo", "--root", str(root)])
    assert validated.exit_code == 0, validated.output
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
