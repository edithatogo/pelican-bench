from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pelicanbench.cli import app
from pelicanbench.io import read_json

pytestmark = pytest.mark.e2e

RUNNER = CliRunner()
KEY = "pelicanbench-freeze-cli-key-material-32bytes"
ENV = {"PB_TEST_FREEZE_KEY": KEY, "SOURCE_DATE_EPOCH": "1785715200"}


def _build_blinding(tmp_path: Path, root: Path) -> tuple[Path, Path]:
    public = tmp_path / "public-blinding.json"
    private = tmp_path / "restricted" / "private-blinding.json"
    result = RUNNER.invoke(
        app,
        [
            "build-model-blinding",
            "--root",
            str(root),
            "--public-output",
            str(public),
            "--private-output",
            str(private),
            "--key-environment",
            "PB_TEST_FREEZE_KEY",
        ],
        env=ENV,
    )
    assert result.exit_code == 0, result.output
    return public, private


def test_study_freeze_cli_and_controlled_unblinding_authorization(
    tmp_path: Path,
    root: Path,
) -> None:
    _, private = _build_blinding(tmp_path, root)
    analysis_path = tmp_path / "analysis-lock.json"
    analysis = RUNNER.invoke(
        app,
        [
            "build-study-freeze",
            "--root",
            str(root),
            "--output",
            str(analysis_path),
            "--freeze-type",
            "analysis-lock",
            "--input",
            "docs/v1-pilot-analysis-plan.md",
            "--input",
            "benchmark/design/assumptions.json",
            "--generated-at",
            "2026-08-03T00:00:00Z",
        ],
        env=ENV,
    )
    assert analysis.exit_code == 0, analysis.output
    assert json.loads(analysis.output)["passed"] is True

    data_path = tmp_path / "data-freeze.json"
    data = RUNNER.invoke(
        app,
        [
            "build-study-freeze",
            "--root",
            str(root),
            "--output",
            str(data_path),
            "--freeze-type",
            "data-freeze",
            "--input",
            "benchmark/fixtures/campaign-ledger/events.jsonl",
            "--input",
            "benchmark/fixtures/campaign-ledger/manifest.json",
            "--ledger-head",
            "benchmark/fixtures/campaign-ledger/verification.json",
            "--generated-at",
            "2026-08-03T01:00:00Z",
        ],
        env=ENV,
    )
    assert data.exit_code == 0, data.output
    assert json.loads(data.output)["passed"] is True

    for manifest in (analysis_path, data_path):
        verified = RUNNER.invoke(
            app,
            [
                "verify-study-freeze",
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            ],
        )
        assert verified.exit_code == 0, verified.output
        assert json.loads(verified.output)["passed"] is True

    authorization_path = tmp_path / "restricted" / "authorization.json"
    authorization = RUNNER.invoke(
        app,
        [
            "authorize-model-unblinding-from-freezes",
            "--root",
            str(root),
            "--private",
            str(private),
            "--analysis-lock",
            str(analysis_path),
            "--data-freeze",
            str(data_path),
            "--output",
            str(authorization_path),
            "--authorized-by",
            "independent-study-custodian",
            "--reason",
            "The analysis lock and complete campaign-data freeze both verify.",
            "--key-environment",
            "PB_TEST_FREEZE_KEY",
        ],
        env=ENV,
    )
    assert authorization.exit_code == 0, authorization.output
    payload = json.loads(authorization.output)
    assert payload["passed"] is True
    receipt = read_json(authorization_path)
    assert receipt["analysis_lock_commitment"] == read_json(analysis_path)["freeze_commitment"]
    assert receipt["data_freeze_commitment"] == read_json(data_path)["freeze_commitment"]


def test_study_freeze_cli_rejects_tampering_and_unverified_authorization(
    tmp_path: Path,
    root: Path,
) -> None:
    _, private = _build_blinding(tmp_path, root)
    analysis_path = tmp_path / "analysis-lock.json"
    built = RUNNER.invoke(
        app,
        [
            "build-study-freeze",
            "--root",
            str(root),
            "--output",
            str(analysis_path),
            "--freeze-type",
            "analysis-lock",
            "--input",
            "docs/v1-pilot-analysis-plan.md",
        ],
        env=ENV,
    )
    assert built.exit_code == 0, built.output
    raw = read_json(analysis_path)
    raw["files"][0]["sha256"] = "sha256:" + "0" * 64
    analysis_path.write_text(json.dumps(raw), encoding="utf-8")

    verified = RUNNER.invoke(
        app,
        [
            "verify-study-freeze",
            "--root",
            str(root),
            "--manifest",
            str(analysis_path),
        ],
    )
    assert verified.exit_code == 1
    assert json.loads(verified.output)["passed"] is False

    authorization = RUNNER.invoke(
        app,
        [
            "authorize-model-unblinding-from-freezes",
            "--root",
            str(root),
            "--private",
            str(private),
            "--analysis-lock",
            str(analysis_path),
            "--data-freeze",
            str(analysis_path),
            "--output",
            str(tmp_path / "authorization.json"),
            "--authorized-by",
            "custodian",
            "--reason",
            "should fail",
            "--key-environment",
            "PB_TEST_FREEZE_KEY",
        ],
        env=ENV,
    )
    assert authorization.exit_code != 0
    assert "must both verify" in authorization.output


def test_raw_digest_unblinding_command_is_not_exposed() -> None:
    result = RUNNER.invoke(app, ["authorize-model-unblinding", "--help"])
    assert result.exit_code != 0
    assert "No such command" in result.output
