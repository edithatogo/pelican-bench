from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pelicanbench.cli import app

ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()


def _json_output(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.e2e
def test_transactional_campaign_worker_cli_roundtrip(tmp_path: Path) -> None:
    manifest = ROOT / "benchmark/fixtures/campaign/manifest.json"
    tasks = ROOT / "benchmark/fixtures/campaign/tasks.jsonl"
    database = tmp_path / "campaign.sqlite"
    outputs = tmp_path / "runs"

    initial = _json_output(
        RUNNER.invoke(
            app,
            [
                "init-campaign-store",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
            ],
        )
    )
    assert initial["state_counts"] == {"ready": 1}

    batch = _json_output(
        RUNNER.invoke(
            app,
            [
                "run-fixture-campaign-worker",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
                "--tasks",
                str(tasks),
                "--model-id",
                "fixture/model",
                "--output",
                str(outputs),
                "--now",
                "2026-08-03T00:00:00Z",
            ],
        )
    )
    assert batch["succeeded"] == 1
    assert batch["leased_cells"] == 1

    status = _json_output(
        RUNNER.invoke(
            app,
            [
                "campaign-store-status",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
            ],
        )
    )
    assert status["complete"]
    assert status["state_counts"] == {"succeeded": 1}

    reconciliation = _json_output(
        RUNNER.invoke(
            app,
            [
                "reconcile-campaign-store",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
            ],
        )
    )
    assert reconciliation["valid"]

    ledger = tmp_path / "events.jsonl"
    exported = RUNNER.invoke(
        app,
        [
            "export-campaign-store-events",
            "--database",
            str(database),
            "--output",
            str(ledger),
        ],
    )
    assert exported.exit_code == 0, exported.output
    assert ledger.read_text(encoding="utf-8").count("\n") == 2

    execution_index = tmp_path / "executions.jsonl"
    execution_export = RUNNER.invoke(
        app,
        [
            "export-campaign-executions",
            "--campaign-output",
            str(outputs),
            "--output",
            str(execution_index),
        ],
    )
    assert execution_export.exit_code == 0, execution_export.output
    execution = json.loads(execution_index.read_text(encoding="utf-8"))
    assert execution["attempt"] == 1
    assert execution["terminal_state"] == "succeeded"

    execution_reconciliation = _json_output(
        RUNNER.invoke(
            app,
            [
                "reconcile-campaign-executions",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
                "--campaign-output",
                str(outputs),
            ],
        )
    )
    assert execution_reconciliation["valid"]
    assert execution_reconciliation["matched_records"] == 1

    reclaimed = _json_output(
        RUNNER.invoke(
            app,
            [
                "reclaim-campaign-leases",
                "--manifest",
                str(manifest),
                "--database",
                str(database),
            ],
        )
    )
    assert reclaimed["reclaimed"] == 0


@pytest.mark.e2e
def test_fixture_model_qualification_cli_is_resumable(tmp_path: Path) -> None:
    output = tmp_path / "qualification"
    arguments = [
        "run-fixture-model-qualification",
        "--root",
        str(ROOT),
        "--model-id",
        "openai/gpt-5.6-terra",
        "--output",
        str(output),
    ]
    first = _json_output(RUNNER.invoke(app, arguments))
    assert first["executed_cells"] == 9
    assert first["resumed_cells"] == 0
    assert all(item["qualified"] for item in first["results"])
    second = _json_output(RUNNER.invoke(app, arguments))
    assert second["executed_cells"] == 0
    assert second["resumed_cells"] == 9
    assert second["outcome_hash"] == first["outcome_hash"]


@pytest.mark.e2e
def test_design_and_judge_evidence_cli_matches_snapshots(tmp_path: Path) -> None:
    power_output = tmp_path / "power.json"
    power = _json_output(
        RUNNER.invoke(
            app,
            [
                "simulate-design-power",
                "--root",
                str(ROOT),
                "--spec",
                str(ROOT / "benchmark/design/power-simulation.json"),
                "--output",
                str(power_output),
            ],
        )
    )
    assert power == json.loads(
        (ROOT / "benchmark/evidence/snapshots/power-simulation.json").read_text()
    )

    judge_output = tmp_path / "judges.json"
    judge = _json_output(
        RUNNER.invoke(
            app,
            [
                "evaluate-judge-panel",
                "--root",
                str(ROOT),
                "--config",
                str(ROOT / "benchmark/judges/calibration-policy.json"),
                "--source",
                str(ROOT / "benchmark/fixtures/design/judge-calibration-observations.jsonl"),
                "--output",
                str(judge_output),
                "--require-empirical",
            ],
        )
    )
    assert judge["panel_empirically_qualified"]
    snapshot = json.loads(
        (ROOT / "benchmark/evidence/snapshots/judge-panel-calibration-fixture.json").read_text()
    )
    assert snapshot["evidence_level"] == "E2"
    assert snapshot["evidence_context"] == "synthetic-fixture"
    assert not snapshot["empirical_release_claim_permitted"]
    assert snapshot["calibration_report"] == judge


@pytest.mark.e2e
def test_challenge_commit_reveal_verify_cli(tmp_path: Path) -> None:
    tasks = ROOT / "benchmark/fixtures/challenge/tasks.jsonl"
    commitment = tmp_path / "commitment.json"
    secrets = tmp_path / "fixture-secrets.json"
    committed = _json_output(
        RUNNER.invoke(
            app,
            [
                "commit-sealed-challenge",
                "--tasks",
                str(tasks),
                "--output",
                str(commitment),
                "--secrets-output",
                str(secrets),
                "--release",
                "PB-CLI-FIXTURE",
                "--fixture-seed",
                "17",
                "--created-at",
                "2026-08-03T00:00:00Z",
                "--root",
                str(ROOT),
            ],
        )
    )
    assert committed["task_count"] == 5
    assert secrets.stat().st_mode & 0o777 == 0o600

    reveals = tmp_path / "reveals.jsonl"
    reveal_result = RUNNER.invoke(
        app,
        [
            "reveal-sealed-challenge",
            "--commitment",
            str(commitment),
            "--tasks",
            str(tasks),
            "--secrets-source",
            str(secrets),
            "--output",
            str(reveals),
        ],
    )
    assert reveal_result.exit_code == 0, reveal_result.output
    verified = _json_output(
        RUNNER.invoke(
            app,
            [
                "verify-sealed-challenge",
                "--commitment",
                str(commitment),
                "--reveal",
                str(reveals),
                "--require-full",
            ],
        )
    )
    assert verified["valid"]


@pytest.mark.e2e
def test_blinded_reassessment_and_replicate_wave_cli(tmp_path: Path) -> None:
    reassessment = _json_output(
        RUNNER.invoke(
            app,
            [
                "blinded-replicate-reassessment",
                "--root",
                str(ROOT),
                "--source",
                str(ROOT / "benchmark/fixtures/design/blinded-reassessment.jsonl"),
                "--tasks-per-model",
                "64",
                "--policy",
                str(ROOT / "benchmark/design/replicate-reassessment.json"),
                "--output",
                str(tmp_path / "reassessment.json"),
            ],
        )
    )
    assert reassessment["status"] == "decision-ready"
    assert reassessment == json.loads(
        (ROOT / "benchmark/evidence/snapshots/blinded-reassessment-fixture.json").read_text()
    )

    wave_path = tmp_path / "wave.json"
    planned = RUNNER.invoke(
        app,
        [
            "plan-replicate-wave",
            "--root",
            str(ROOT),
            "--target-replicates",
            "5",
            "--output",
            str(wave_path),
        ],
    )
    assert planned.exit_code == 0, planned.output
    wave = json.loads(wave_path.read_text())
    assert wave["current_replicates"] == 3
    assert wave["target_replicates"] == 5
    assert wave["additional_replicates"] == 2
    assert wave["cell_count"] > 0
