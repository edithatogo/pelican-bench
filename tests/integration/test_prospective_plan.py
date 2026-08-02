from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.pilot import load_tasks
from pelicanbench.prospective import build_prospective_pilot_plan

ROOT = Path(__file__).parents[2]


def _inputs():
    tasks = load_tasks(ROOT / "benchmark/tasks/v1-candidate.jsonl")
    panel = json.loads(
        (ROOT / "benchmark/models/prospective-panel.json").read_text(encoding="utf-8")
    )
    commitment = json.loads(
        (ROOT / "benchmark/tasks/v1-candidate-commitment.json").read_text(encoding="utf-8")
    )["commitment"]
    return tasks, panel, commitment


def test_prospective_plan_has_prespecified_stage_denominators(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1785628800")
    tasks, panel, commitment = _inputs()
    plan = build_prospective_pilot_plan(
        tasks, panel, task_identity_commitment=commitment, replicates=3
    )
    assert plan.generated_at == "2026-08-02T00:00:00Z"
    assert plan.task_count == 113
    assert plan.model_count == 7
    assert plan.cell_count == 2178
    assert plan.ready_cell_count == 0
    assert plan.qualification_required_cell_count == 2178
    assert [(item.task_panel_id, item.cell_count) for item in plan.stages] == [
        ("heritage-anchor", 18),
        ("castillo-2026-factorial-bridge", 1008),
        ("pelicanbench-interface-confirmatory-v1", 1152),
    ]
    assert len({item.cell_id for item in plan.cells}) == 2178


def test_prospective_plan_is_order_invariant_and_reflects_qualification() -> None:
    tasks, panel, commitment = _inputs()
    first = build_prospective_pilot_plan(
        tasks, panel, task_identity_commitment=commitment, replicates=1
    )
    second = build_prospective_pilot_plan(
        reversed(tasks), panel, task_identity_commitment=commitment, replicates=1
    )
    assert [item.as_dict() for item in first.cells] == [item.as_dict() for item in second.cells]

    qualified = build_prospective_pilot_plan(
        tasks,
        panel,
        task_identity_commitment=commitment,
        replicates=1,
        model_qualification={"openai/gpt-5.6-terra": True},
    )
    ready = [item for item in qualified.cells if item.status == "ready"]
    assert ready
    assert {item.model_id for item in ready} == {"openai/gpt-5.6-terra"}


def test_prospective_plan_rejects_invalid_inputs() -> None:
    tasks, panel, commitment = _inputs()
    with pytest.raises(ValueError, match="replicates"):
        build_prospective_pilot_plan(tasks, panel, task_identity_commitment=commitment, replicates=0)
    with pytest.raises(ValueError, match="candidate tasks"):
        build_prospective_pilot_plan([], panel, task_identity_commitment=commitment)
    broken = json.loads(json.dumps(panel))
    broken["execution_stages"][0]["cohort_id"] = "missing"
    with pytest.raises(ValueError, match="unknown model cohort"):
        build_prospective_pilot_plan(tasks, broken, task_identity_commitment=commitment)
