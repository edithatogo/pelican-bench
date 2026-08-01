from __future__ import annotations

import random

import pytest

from pelicanbench.calibration import (
    CalibrationCandidate,
    build_calibration_design,
    build_pairwise_calibration_tasks,
    disagreement_band,
    score_band,
    select_calibration_sample,
)


def _candidates():
    rows = []
    index = 0
    for stratum in ("straddle", "inside"):
        for model in ("m1", "m2", "m3"):
            for score, disagreement in ((0.2, 0.05), (0.55, 0.3), (0.85, 0.1)):
                index += 1
                rows.append(
                    CalibrationCandidate(
                        artifact_id=f"a{index:02d}",
                        task_id=f"t-{stratum}-{index % 3}",
                        scenario_id=f"s-{stratum}-{index % 3}",
                        model_id=model,
                        interface_stratum=stratum,
                        automatic_score=score,
                        judge_disagreement=disagreement,
                    )
                )
    return rows


def test_score_and_disagreement_bands():
    assert score_band(0.2) == "low"
    assert score_band(0.5) == "decision-boundary"
    assert score_band(0.8) == "high"
    assert disagreement_band(0.2) == "high-disagreement"
    with pytest.raises(ValueError):
        score_band(1.5)


def test_stratified_sample_is_deterministic_and_order_invariant():
    rows = _candidates()
    first = select_calibration_sample(rows, target=12, seed=9)
    shuffled = rows[:]
    random.Random(3).shuffle(shuffled)
    second = select_calibration_sample(shuffled, target=12, seed=9)
    assert [item.candidate.artifact_id for item in first] == [
        item.candidate.artifact_id for item in second
    ]
    assert len({item.sampling_cell for item in first}) == 12
    assert {item.score_band for item in first} == {"low", "decision-boundary", "high"}


def test_invalid_artifacts_are_sampled_as_a_distinct_band():
    rows = _candidates()[:2]
    rows.append(
        CalibrationCandidate(
            "invalid-a",
            "t-invalid",
            "s-invalid",
            "m1",
            "inside",
            0.0,
            0.8,
            valid=False,
        )
    )
    selected = select_calibration_sample(rows, target=3)
    assert "invalid" in {item.score_band for item in selected}


def test_pairwise_tasks_are_within_task_and_cross_model():
    rows = [
        CalibrationCandidate("a1", "task", "s", "m1", "inside", 0.4, 0.2),
        CalibrationCandidate("a2", "task", "s", "m2", "inside", 0.6, 0.3),
        CalibrationCandidate("a3", "task", "s", "m3", "inside", 0.8, 0.1),
    ]
    selected = select_calibration_sample(rows, target=3)
    pairs = build_pairwise_calibration_tasks(selected, seed=1)
    assert len(pairs) == 3 * 5
    assert all(item.left_model_id != item.right_model_id for item in pairs)
    assert len({item.pair_id for item in pairs}) == len(pairs)


def test_complete_design():
    design = build_calibration_design(_candidates(), target=10, seed=4)
    assert design.selected_artifacts == 10
    assert design.schema_version == "1.0.0"
    assert design.as_dict()["requested_artifacts"] == 10


def test_duplicate_artifact_ids_rejected():
    row = CalibrationCandidate("a", "t", "s", "m", "inside", 0.5, 0.1)
    with pytest.raises(ValueError):
        select_calibration_sample([row, row], target=1)
