from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pelicanbench.qualification import (
    JudgeQualificationOutcome,
    ModelQualificationOutcome,
    build_judge_qualification_plan,
    evaluate_judge_qualification,
    evaluate_model_qualification,
    load_default_judge_qualification_plan,
    load_default_model_qualification_plan,
)

ROOT = Path(__file__).parents[2]


def test_model_qualification_plan_matches_checked_snapshot() -> None:
    actual = load_default_model_qualification_plan(ROOT)
    expected = json.loads(
        (ROOT / "benchmark/evidence/snapshots/model-qualification-plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert actual == expected
    assert len(actual["cells"]) == 63


def test_model_qualification_retains_failures_and_applies_all_gates() -> None:
    plan = load_default_model_qualification_plan(ROOT)
    first_model = plan["models"][0]
    cells = [item for item in plan["cells"] if item["model_id"] == first_model]
    outcomes = [
        ModelQualificationOutcome(
            cell_id=item["cell_id"],
            retained=True,
            eventual_success=True,
            valid_svg=True,
            secure_render=True,
            first_attempt_success=index < 5,
            attempts=1 if index < 5 else 2,
        )
        for index, item in enumerate(cells)
    ]
    results = evaluate_model_qualification(plan, outcomes)
    result = next(item for item in results if item.model_id == first_model)
    assert result.retained_cells == 9
    assert result.success_rate == 1.0
    assert result.secure_render_rate == 1.0
    assert result.first_attempt_rate == pytest.approx(5 / 9)
    assert result.qualified
    # Models without outcomes fail rather than disappearing from the denominator.
    assert all(not item.qualified for item in results if item.model_id != first_model)


def test_model_qualification_rejects_incoherent_and_unknown_outcomes() -> None:
    plan = load_default_model_qualification_plan(ROOT)
    cell_id = plan["cells"][0]["cell_id"]
    with pytest.raises(ValueError, match="implies eventual"):
        ModelQualificationOutcome(
            cell_id=cell_id,
            retained=True,
            eventual_success=False,
            valid_svg=False,
            secure_render=False,
            first_attempt_success=True,
        )
    with pytest.raises(ValueError, match="unknown qualification cells"):
        evaluate_model_qualification(
            plan,
            [
                ModelQualificationOutcome(
                    cell_id="QCEL-unknown",
                    retained=True,
                    eventual_success=False,
                    valid_svg=False,
                    secure_render=False,
                    first_attempt_success=False,
                    error_type="fixture",
                )
            ],
        )


def test_judge_qualification_plan_matches_checked_summary() -> None:
    summary, cells = load_default_judge_qualification_plan(ROOT)
    expected = json.loads(
        (ROOT / "benchmark/evidence/snapshots/judge-qualification-plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary == expected
    assert len(cells) == 40
    assert len({item.cell_id for item in cells}) == 40


def test_judge_technical_and_human_calibration_gates_are_separate() -> None:
    panel = json.loads(
        (ROOT / "benchmark/judges/prospective-panel.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (ROOT / "benchmark/judges/canary-manifest.json").read_text(encoding="utf-8")
    )
    _, cells = build_judge_qualification_plan(panel, manifest)
    outcomes = [
        JudgeQualificationOutcome(
            cell_id=cell.cell_id,
            schema_valid=True,
            output_complete=True,
            source_independent=True,
            prompt_leakage=False,
            task_correct=True,
        )
        for cell in cells
    ]
    technical = evaluate_judge_qualification(cells, outcomes, panel["qualification_gates"])
    assert all(item.technical_gates_passed for item in technical)
    assert all(not item.empirical_gate_passed for item in technical)
    assert {item.evidence_status for item in technical} == {
        "E2-technical-qualified-human-calibration-required"
    }

    calibrated = [replace(item, human_agreement=0.9) for item in outcomes]
    empirical = evaluate_judge_qualification(cells, calibrated, panel["qualification_gates"])
    assert all(item.empirical_gate_passed for item in empirical)
    assert {item.evidence_status for item in empirical} == {"E3-human-calibrated"}


def test_judge_qualification_fails_closed_for_missing_or_duplicate_cells() -> None:
    panel = json.loads(
        (ROOT / "benchmark/judges/prospective-panel.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (ROOT / "benchmark/judges/canary-manifest.json").read_text(encoding="utf-8")
    )
    _, cells = build_judge_qualification_plan(panel, manifest)
    one = JudgeQualificationOutcome(
        cell_id=cells[0].cell_id,
        schema_valid=True,
        output_complete=True,
        source_independent=True,
        prompt_leakage=False,
        task_correct=True,
    )
    results = evaluate_judge_qualification(cells, [one], panel["qualification_gates"])
    target = next(item for item in results if item.judge_id == cells[0].judge_id and item.role == cells[0].role)
    assert not target.technical_gates_passed
    with pytest.raises(ValueError, match="unique cell identifiers"):
        evaluate_judge_qualification(cells, [one, one], panel["qualification_gates"])
