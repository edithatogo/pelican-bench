from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_t14_custody_cli_requires_acknowledgement_and_writes_restricted_files(
    tmp_path: Path, root: Path
) -> None:
    script = root / "scripts/prepare_t14_custody_artifacts.py"
    environment = os.environ | {
        "PB_T14_TEST_SECRET": "t14-cli-test-secret-material-at-least-32-bytes"
    }
    missing_ack = subprocess.run(
        [
            str(script),
            "--output-directory",
            str(tmp_path / "missing"),
            "--secret-environment",
            "PB_T14_TEST_SECRET",
            "--custodian-id",
            "test-custodian",
            "--custody-classification",
            "procedural-self-custody-not-independent",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing_ack.returncode != 0
    assert "acknowledgement is required" in missing_ack.stderr

    output = tmp_path / "custody"
    generated = subprocess.run(
        [
            str(script),
            "--output-directory",
            str(output),
            "--secret-environment",
            "PB_T14_TEST_SECRET",
            "--custodian-id",
            "test-custodian",
            "--custody-classification",
            "procedural-self-custody-not-independent",
            "--acknowledge-accountable-custodian",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    assert json.loads(generated.stdout)["status"] == "generated-no-gate-effect"
    for name in (
        "restricted-alias-manifest.json",
        "restricted-duplicate-schedule.json",
        "custody-receipt.json",
    ):
        assert (output / name).stat().st_mode & 0o777 == 0o600
    assert output.stat().st_mode & 0o777 == 0o700
