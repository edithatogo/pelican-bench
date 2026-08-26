from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate_t14_candidate_episodes.py"
SPEC = importlib.util.spec_from_file_location("validate_t14_candidate_episodes", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_candidate_asset_resolution_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="resolves outside candidate root"):
        MODULE.resolve_candidate_asset(Path("benchmark/fixtures/repair/candidate/../../tasks.json"))


def test_candidate_asset_resolution_accepts_committed_asset() -> None:
    resolved = MODULE.resolve_candidate_asset(
        Path("benchmark/fixtures/repair/candidate/assets/repair-t14-candidate-01-01-before.svg")
    )
    assert resolved.is_file()
