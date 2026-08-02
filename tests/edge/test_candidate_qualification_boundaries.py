from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.candidate import CandidateFinding, _validate_factorial_panel
from pelicanbench.pilot import load_tasks
from pelicanbench.prospective import build_prospective_pilot_plan
from pelicanbench.qualification import (
    JudgeQualificationOutcome,
    ModelQualificationOutcome,
    build_judge_qualification_plan,
    build_model_qualification_plan,
    evaluate_judge_qualification,
    evaluate_model_qualification,
    load_default_judge_qualification_plan,
    load_default_model_qualification_plan,
)

pytestmark = pytest.mark.edge
ROOT = Path(__file__).parents[2]


def _prospective_inputs():
    tasks = load_tasks(ROOT / "benchmark/tasks/v1-candidate.jsonl")
    panel = json.loads(
        (ROOT / "benchmark/models/prospective-panel.json").read_text(encoding="utf-8")
    )
    commitment = json.loads(
        (ROOT / "benchmark/tasks/v1-candidate-commitment.json").read_text(encoding="utf-8")
    )["commitment"]
    return tasks, panel, commitment


def test_candidate_finding_and_factorial_failures_are_machine_readable() -> None:
    finding = CandidateFinding("error", "fixture", "message")
    assert finding.as_dict() == {
        "severity": "error",
        "code": "fixture",
        "message": "message",
    }

    task = load_tasks(ROOT / "benchmark/tasks/v1-candidate.jsonl")[0]
    findings = _validate_factorial_panel(
        [task],
        animals={"dog"},
        objects={"bicycle"},
        prompt_variants=2,
        panel_id="fixture",
    )
    assert {item.code for item in findings} == {
        "factorial-cells-missing",
        "factorial-cells-unexpected",
        "factorial-prompt-variant-count",
    }


def test_prospective_plan_rejects_digest_panel_and_identifier_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks, panel, commitment = _prospective_inputs()
    with pytest.raises(ValueError, match="prefixed SHA-256"):
        build_prospective_pilot_plan(tasks, panel, task_identity_commitment="not-a-digest")

    empty_panel = json.loads(json.dumps(panel))
    empty_panel["execution_stages"][0]["task_panel_id"] = "missing-panel"
    with pytest.raises(ValueError, match="empty task panel"):
        build_prospective_pilot_plan(
            tasks,
            empty_panel,
            task_identity_commitment=commitment,
        )

    monkeypatch.setattr("pelicanbench.prospective._stable_cell_id", lambda *_args: "duplicate")
    with pytest.raises(ValueError, match="cell identifiers must be unique"):
        build_prospective_pilot_plan(
            tasks,
            panel,
            task_identity_commitment=commitment,
            replicates=1,
        )


def test_prospective_summary_and_cells_are_serialisable() -> None:
    tasks, panel, commitment = _prospective_inputs()
    plan = build_prospective_pilot_plan(
        tasks,
        panel,
        task_identity_commitment=commitment,
        replicates=1,
    )
    summary = plan.summary()
    assert "cells" not in summary
    assert summary["stages"][0] == plan.stages[0].as_dict()
    assert plan.cells[0].as_dict()["cell_id"] == plan.cells[0].cell_id


def test_model_qualification_rejects_invalid_outcomes_and_empty_canary() -> None:
    plan = load_default_model_qualification_plan(ROOT)
    cell_id = plan["cells"][0]["cell_id"]
    with pytest.raises(ValueError, match="attempts"):
        ModelQualificationOutcome(
            cell_id=cell_id,
            retained=True,
            eventual_success=False,
            valid_svg=False,
            secure_render=False,
            first_attempt_success=False,
            attempts=0,
        )
    with pytest.raises(ValueError, match="valid SVG"):
        ModelQualificationOutcome(
            cell_id=cell_id,
            retained=True,
            eventual_success=True,
            valid_svg=False,
            secure_render=True,
            first_attempt_success=False,
        )
    duplicate = ModelQualificationOutcome(
        cell_id=cell_id,
        retained=True,
        eventual_success=False,
        valid_svg=False,
        secure_render=False,
        first_attempt_success=False,
    )
    with pytest.raises(ValueError, match="unique cell identifiers"):
        evaluate_model_qualification(plan, [duplicate, duplicate])

    panel = json.loads(
        (ROOT / "benchmark/models/prospective-panel.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="canary tasks"):
        build_model_qualification_plan([], panel, benchmark_release="fixture")


def test_judge_qualification_covers_diversity_and_outcome_boundaries() -> None:
    with pytest.raises(ValueError, match="human_agreement"):
        JudgeQualificationOutcome(
            cell_id="fixture",
            schema_valid=True,
            output_complete=True,
            source_independent=True,
            prompt_leakage=False,
            task_correct=True,
            human_agreement=1.1,
        )

    panel = {
        "judges": [
            {
                "judge_id": "judge-a",
                "family": "one-family",
                "roles": ["blind-open-set-extraction"],
            }
        ],
        "minimum_families_by_role": {"blind-open-set-extraction": 2},
    }
    manifest = {
        "canaries": [
            {
                "canary_id": "canary-a",
                "artifact_id": "artifact-a",
                "applicable_roles": ["blind-open-set-extraction"],
            }
        ]
    }
    summary, cells = build_judge_qualification_plan(panel, manifest)
    assert not summary["diversity_gates_satisfied"]
    assert summary["blockers"]
    assert cells[0].as_dict()["judge_id"] == "judge-a"

    _, default_cells = load_default_judge_qualification_plan(ROOT)
    outcome = JudgeQualificationOutcome(
        cell_id=default_cells[0].cell_id,
        schema_valid=True,
        output_complete=True,
        source_independent=True,
        prompt_leakage=False,
        task_correct=True,
    )
    gates = {
        "minimum_schema_valid_rate": 0.0,
        "minimum_output_complete_rate": 0.0,
        "minimum_source_independent_rate": 0.0,
        "maximum_prompt_leakage_rate": 1.0,
        "minimum_task_accuracy": 0.0,
        "minimum_human_agreement": 0.5,
    }
    with pytest.raises(ValueError, match="unique cell identifiers"):
        evaluate_judge_qualification(default_cells, [outcome, outcome], gates)
    unknown = JudgeQualificationOutcome(
        cell_id="JCEL-unknown",
        schema_valid=False,
        output_complete=False,
        source_independent=False,
        prompt_leakage=True,
        task_correct=False,
    )
    with pytest.raises(ValueError, match="unknown judge cells"):
        evaluate_judge_qualification(default_cells, [unknown], gates)
