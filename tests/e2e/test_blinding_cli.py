from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pelicanbench.cli import app
from pelicanbench.io import read_json, read_jsonl, write_jsonl

pytestmark = pytest.mark.e2e

RUNNER = CliRunner()
KEY = "pelicanbench-cli-test-key-material-32bytes"
ENV = {"PB_TEST_BLINDING_KEY": KEY}


def test_model_blinding_cli_round_trip(tmp_path: Path, root: Path) -> None:
    public_path = tmp_path / "public-blinding.json"
    private_path = tmp_path / "restricted" / "private-blinding.json"
    built = RUNNER.invoke(
        app,
        [
            "build-model-blinding",
            "--root",
            str(root),
            "--public-output",
            str(public_path),
            "--private-output",
            str(private_path),
            "--key-environment",
            "PB_TEST_BLINDING_KEY",
        ],
        env=ENV,
    )
    assert built.exit_code == 0, built.output
    built_payload = json.loads(built.output)
    assert built_payload["passed"] is True
    assert built_payload["model_count"] == 7
    public = read_json(public_path)
    private = read_json(private_path)
    assert public["contains_model_identifiers"] is False
    assert private["sensitivity"] == "restricted-unblinding-map"
    assert all(entry["model_id"] not in public_path.read_text() for entry in private["entries"])

    verification_path = tmp_path / "verification.json"
    verified = RUNNER.invoke(
        app,
        [
            "verify-model-blinding",
            "--public",
            str(public_path),
            "--private",
            str(private_path),
            "--key-environment",
            "PB_TEST_BLINDING_KEY",
            "--output",
            str(verification_path),
        ],
        env=ENV,
    )
    assert verified.exit_code == 0, verified.output
    assert read_json(verification_path)["cryptographic_mapping_verified"] is True

    records_path = tmp_path / "records.jsonl"
    blinded_path = tmp_path / "blinded.jsonl"
    model_ids = [entry["model_id"] for entry in private["entries"]]
    write_jsonl(
        records_path,
        [
            {"model_id": model_ids[0], "score": 0.4},
            {"generator_model_id": model_ids[1], "judge_model_id": model_ids[2]},
        ],
    )
    blinded = RUNNER.invoke(
        app,
        [
            "blind-model-records",
            "--source",
            str(records_path),
            "--destination",
            str(blinded_path),
            "--private",
            str(private_path),
        ],
    )
    assert blinded.exit_code == 0, blinded.output
    assert all(model_id not in blinded_path.read_text() for model_id in model_ids)

    analysis_lock = tmp_path / "analysis-lock.json"
    analysis = RUNNER.invoke(
        app,
        [
            "build-study-freeze",
            "--root",
            str(root),
            "--output",
            str(analysis_lock),
            "--freeze-type",
            "analysis-lock",
            "--input",
            "docs/v1-pilot-analysis-plan.md",
        ],
        env=ENV,
    )
    assert analysis.exit_code == 0, analysis.output
    data_freeze = tmp_path / "data-freeze.json"
    data = RUNNER.invoke(
        app,
        [
            "build-study-freeze",
            "--root",
            str(root),
            "--output",
            str(data_freeze),
            "--freeze-type",
            "data-freeze",
            "--input",
            "benchmark/fixtures/campaign-ledger/events.jsonl",
            "--ledger-head",
            "benchmark/fixtures/campaign-ledger/verification.json",
        ],
        env=ENV,
    )
    assert data.exit_code == 0, data.output

    authorization_path = tmp_path / "authorization.json"
    authorized = RUNNER.invoke(
        app,
        [
            "authorize-model-unblinding-from-freezes",
            "--root",
            str(root),
            "--private",
            str(private_path),
            "--analysis-lock",
            str(analysis_lock),
            "--data-freeze",
            str(data_freeze),
            "--output",
            str(authorization_path),
            "--authorized-by",
            "study-custodian",
            "--reason",
            "Analysis and data freeze are complete.",
            "--key-environment",
            "PB_TEST_BLINDING_KEY",
        ],
        env=ENV,
    )
    assert authorized.exit_code == 0, authorized.output

    checked = RUNNER.invoke(
        app,
        [
            "verify-model-unblinding-authorization",
            "--private",
            str(private_path),
            "--authorization",
            str(authorization_path),
            "--key-environment",
            "PB_TEST_BLINDING_KEY",
        ],
        env=ENV,
    )
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output)["passed"] is True

    unblinded_path = tmp_path / "restricted-unblinded.jsonl"
    unblinded = RUNNER.invoke(
        app,
        [
            "unblind-model-records",
            "--source",
            str(blinded_path),
            "--destination",
            str(unblinded_path),
            "--private",
            str(private_path),
            "--authorization",
            str(authorization_path),
            "--key-environment",
            "PB_TEST_BLINDING_KEY",
        ],
        env=ENV,
    )
    assert unblinded.exit_code == 0, unblinded.output
    assert read_jsonl(unblinded_path) == read_jsonl(records_path)


def test_blinding_cli_fails_closed_without_secret(tmp_path: Path, root: Path) -> None:
    result = RUNNER.invoke(
        app,
        [
            "build-model-blinding",
            "--root",
            str(root),
            "--public-output",
            str(tmp_path / "public.json"),
            "--private-output",
            str(tmp_path / "private.json"),
            "--key-environment",
            "PB_MISSING_BLINDING_KEY",
        ],
        env={"PB_MISSING_BLINDING_KEY": ""},
    )
    assert result.exit_code != 0
    assert "required secret environment variable is unset" in result.output
