from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_t14_prospective_statistics.py"
PLAN = ROOT / "benchmark/evidence/advisory/t14/prospective-statistical-analysis-plan.json"


def load_module():
    spec = importlib.util.spec_from_file_location("t14_prospective_statistics", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prospective_plan_and_synthetic_allocation_are_valid() -> None:
    module = load_module()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    rows = module.synthetic_allocation()

    assert rows == module.synthetic_allocation()
    report = module.validate(plan, rows)
    assert report["status"] == "valid-prospective-synthetic-only"
    assert report["scene_cluster_split"] == {"development": 18, "held-out": 6}
    assert report["normative_sample_frozen"] is False
    assert report["human_ratings_present"] is False
    assert report["score_promotion"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda rows: rows.__setitem__(72, {**rows[72], "scene_cluster": "synthetic-scene-18"}),
            "scene",
        ),
        (lambda rows: rows.__setitem__(0, {**rows[0], "severity": "severe"}), "severity"),
        (
            lambda rows: [
                row.__setitem__("target-correction", "positive")
                for row in rows
                if row["partition"] == "held-out"
            ],
            "class support",
        ),
    ],
)
def test_validator_fails_closed_on_design_drift(mutation, message: str) -> None:
    module = load_module()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    rows = module.synthetic_allocation()
    mutation(rows)

    with pytest.raises(ValueError, match=message):
        module.validate(plan, rows)
