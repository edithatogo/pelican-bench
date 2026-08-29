from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate_t14_diagnostic_episodes.py"
SPEC = importlib.util.spec_from_file_location("validate_t14_diagnostics", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_diagnostics_are_balanced_and_non_normative() -> None:
    payload = json.loads(MODULE.MANIFEST.read_text())
    assert payload["episode_count"] == 40
    assert payload["normative_eligible"] is False
    assert payload["normative_sample_frozen"] is False
    assert {row["diagnostic_class"] for row in payload["episodes"]} == MODULE.CLASSES
    assert all(row["normative_eligible"] is False for row in payload["episodes"])


def test_diagnostic_resolution_rejects_candidate_path() -> None:
    with pytest.raises(ValueError, match="prefix invalid"):
        MODULE.resolve(Path("benchmark/fixtures/repair/candidate/manifest.json"))
