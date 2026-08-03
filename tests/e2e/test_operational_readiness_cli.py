from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pelicanbench.cli import app

RUNNER = CliRunner()


def test_design_campaign_and_protocol_cli(tmp_path: Path, root: Path) -> None:
    design_output = tmp_path / "design-assurance.json"
    design = RUNNER.invoke(
        app,
        ["design-assurance", "--root", str(root), "--output", str(design_output)],
    )
    assert design.exit_code == 0, design.output
    design_payload = json.loads(design_output.read_text(encoding="utf-8"))
    assert design_payload["replicates"] == 3
    assert design_payload["recommended_replicates_for_target"] in {3, 5, 7}

    manifest_output = tmp_path / "campaign.json"
    summary_output = tmp_path / "campaign-summary.json"
    campaign = RUNNER.invoke(
        app,
        [
            "build-campaign-manifest",
            "--root",
            str(root),
            "--output",
            str(manifest_output),
            "--summary-output",
            str(summary_output),
        ],
    )
    assert campaign.exit_code == 0, campaign.output
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    assert summary["cell_count"] == 2178
    assert summary["state_counts"] == {"blocked-qualification": 2178}
    assert summary["budget_gate"] == "blocked-no-hard-budget"

    status = RUNNER.invoke(
        app,
        ["campaign-status", "--manifest", str(manifest_output)],
    )
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["complete"] is False

    lock_output = tmp_path / "study-lock.json"
    lock = RUNNER.invoke(
        app,
        ["study-protocol-lock", "--root", str(root), "--output", str(lock_output)],
    )
    assert lock.exit_code == 0, lock.output

    verification_output = tmp_path / "protocol-verification.json"
    verification = RUNNER.invoke(
        app,
        [
            "verify-study-protocol",
            "--root",
            str(root),
            "--lock",
            str(lock_output),
            "--output",
            str(verification_output),
        ],
    )
    assert verification.exit_code == 0, verification.output
    assert json.loads(verification_output.read_text(encoding="utf-8"))["valid"] is True


def test_firewall_and_human_operations_cli(tmp_path: Path, root: Path) -> None:
    firewall_output = tmp_path / "firewall.json"
    firewall = RUNNER.invoke(
        app,
        [
            "judge-firewall",
            "--root",
            str(root),
            "--source",
            str(root / "benchmark/fixtures/adversarial/visible-judge-prompt-injection.svg"),
            "--output",
            str(firewall_output),
        ],
    )
    assert firewall.exit_code == 1
    firewall_payload = json.loads(firewall_output.read_text(encoding="utf-8"))
    assert firewall_payload["eligible"] is False
    assert firewall_payload["decision"] == "quarantined"

    adjudication_output = tmp_path / "adjudication.jsonl"
    adjudication = RUNNER.invoke(
        app,
        [
            "build-calibration-adjudication",
            "--root",
            str(root),
            "--source",
            str(root / "benchmark/fixtures/human-calibration/operations-responses.jsonl"),
            "--output",
            str(adjudication_output),
        ],
    )
    assert adjudication.exit_code == 0, adjudication.output
    assert len(adjudication_output.read_text(encoding="utf-8").splitlines()) == 4

    stopping_output = tmp_path / "stopping.json"
    stopping = RUNNER.invoke(
        app,
        [
            "evaluate-calibration-stopping",
            "--root",
            str(root),
            "--analysis",
            str(root / "benchmark/fixtures/human-calibration/operations-analysis.json"),
            "--output",
            str(stopping_output),
        ],
    )
    assert stopping.exit_code == 0, stopping.output
    assert json.loads(stopping_output.read_text(encoding="utf-8"))["ready_to_stop"] is True
