from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pelicanbench.cli import app

ROOT = Path(__file__).parents[2]
RUNNER = CliRunner()


def test_candidate_empirical_and_qualification_commands(tmp_path: Path) -> None:
    candidate = RUNNER.invoke(app, ["validate-v1-candidate", "--root", str(ROOT)])
    assert candidate.exit_code == 0, candidate.output
    assert json.loads(candidate.output)["passed"] is True

    commitment_path = tmp_path / "commitment.json"
    commitment = RUNNER.invoke(
        app,
        ["candidate-commitment", "--root", str(ROOT), "--output", str(commitment_path)],
    )
    assert commitment.exit_code == 0, commitment.output
    assert json.loads(commitment_path.read_text(encoding="utf-8"))["task_count"] == 113

    empirical_path = tmp_path / "empirical.json"
    empirical = RUNNER.invoke(
        app,
        [
            "analyse-empirical-prompt-bridge",
            "--root",
            str(ROOT),
            "--output",
            str(empirical_path),
        ],
    )
    assert empirical.exit_code == 0, empirical.output
    assert json.loads(empirical_path.read_text(encoding="utf-8"))["nlp_report"]["records"] == 48

    model_path = tmp_path / "models.json"
    models = RUNNER.invoke(
        app,
        ["plan-model-qualification", "--root", str(ROOT), "--output", str(model_path)],
    )
    assert models.exit_code == 0, models.output
    assert len(json.loads(model_path.read_text(encoding="utf-8"))["cells"]) == 63

    judge_path = tmp_path / "judges.json"
    judge_cells = tmp_path / "judge-cells.jsonl"
    judges = RUNNER.invoke(
        app,
        [
            "plan-judge-qualification",
            "--root",
            str(ROOT),
            "--output",
            str(judge_path),
            "--cells-output",
            str(judge_cells),
        ],
    )
    assert judges.exit_code == 0, judges.output
    assert json.loads(judge_path.read_text(encoding="utf-8"))["cell_count"] == 40
    assert len(judge_cells.read_text(encoding="utf-8").splitlines()) == 40


def test_human_calibration_and_local_atom_commands(tmp_path: Path) -> None:
    rows = tmp_path / "responses.jsonl"
    rows.write_text(
        json.dumps(
            {
                "stage": "pairwise-preference",
                "response": {"pairwise_winner": "A"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    analysis_path = tmp_path / "analysis.json"
    analysis = RUNNER.invoke(
        app,
        [
            "analyse-human-calibration-jsonl",
            "--source",
            str(rows),
            "--output",
            str(analysis_path),
        ],
    )
    assert analysis.exit_code == 0, analysis.output
    assert json.loads(analysis_path.read_text(encoding="utf-8"))["valid_responses"] == 1

    atom = tmp_path / "feed.atom"
    atom.write_text(
        "<feed xmlns='http://www.w3.org/2005/Atom'><title>T</title>"
        "<entry><id>x</id><title>P</title><summary>pelican</summary></entry></feed>",
        encoding="utf-8",
    )
    output = tmp_path / "simon.jsonl"
    imported = RUNNER.invoke(
        app,
        [
            "import-simon-atom",
            "--source",
            str(atom),
            "--output",
            str(output),
        ],
    )
    assert imported.exit_code == 0, imported.output
    assert len(output.read_text(encoding="utf-8").splitlines()) == 1
