from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


def _run(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_static_and_toolchain_receipts_are_machine_readable(root: Path, tmp_path: Path) -> None:
    static_path = tmp_path / "static.json"
    static = _run(root, "scripts/static_audit.py", "--output", str(static_path))
    assert static.returncode == 0, static.stdout + static.stderr
    payload = json.loads(static_path.read_text(encoding="utf-8"))
    assert payload["passed"]
    assert payload["python_files"] >= 1

    toolchain_path = tmp_path / "toolchain.json"
    toolchain = _run(root, "scripts/toolchain_preflight.py", "--output", str(toolchain_path))
    assert toolchain.returncode == 0
    tools = json.loads(toolchain_path.read_text(encoding="utf-8"))["tools"]
    assert {item["tool"] for item in tools} >= {"ruff", "ty", "basedpyright", "vale"}


def test_contract_and_agent_flow_crosses_real_components(root: Path) -> None:
    completed = _run(
        root,
        "-m",
        "pytest",
        "-q",
        "tests/integration/test_consumer_contracts.py",
        "tests/agent/test_agent_harness.py",
        "-o",
        "addopts=",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
