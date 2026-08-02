from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.human_study import (
    CalibrationSession,
    analyse_calibration_responses,
    validate_calibration_response,
)

ROOT = Path(__file__).parents[2]


def _blind(artifact_id: str) -> dict[str, object]:
    return {
        "stage": "blind-recognition",
        "artifact_id": artifact_id,
        "duplicate_group_id": "dup-1",
        "expected_animal": "pelican",
        "expected_mobile_object": "bicycle",
        "expected_relation": "rides_on",
        "response": {
            "animal_open_text": "pelican",
            "mobile_object_open_text": "bicycle",
            "relation_open_text": "rides_on",
            "recognition_confidence": 95,
        },
    }


def test_fixture_analysis_matches_checked_snapshot() -> None:
    rows = [
        _blind("artifact-1"),
        _blind("artifact-2"),
        {
            "stage": "prompt-aware-criteria",
            "artifact_id": "artifact-1",
            "response": {
                "animal_defects": "none visible",
                "object_defects": "none visible",
                "interaction_defects": "one approximate pedal contact",
                "animal_rating_1_to_5": 5,
                "object_rating_1_to_5": 5,
                "interaction_rating_1_to_5": 4,
                "criterion_confidence": 90,
            },
        },
        {
            "stage": "pairwise-preference",
            "artifact_id": "pair-1",
            "response": {"pairwise_winner": "A"},
        },
    ]
    actual = analyse_calibration_responses(rows)
    expected = json.loads(
        (ROOT / "benchmark/evidence/snapshots/human-calibration-analysis-fixture.json").read_text(
            encoding="utf-8"
        )
    )
    assert actual == expected


def test_session_enforces_blind_first_and_content_addressed_locking() -> None:
    response = {
        "animal_open_text": "pelican",
        "mobile_object_open_text": "bicycle",
        "relation_open_text": "rides_on",
        "recognition_confidence": 80,
    }
    stages = ("blind-recognition", "prompt-aware-criteria")
    first = CalibrationSession("assignment-1", "artifact-1", permitted_stages=stages)
    second = CalibrationSession("assignment-1", "artifact-1", permitted_stages=stages)
    assert not first.prompt_disclosure_permitted
    with pytest.raises(ValueError, match="completed in order"):
        first.submit(
            "prompt-aware-criteria",
            {
                "animal_defects": "none",
                "object_defects": "none",
                "interaction_defects": "none",
                "animal_rating_1_to_5": 5,
                "object_rating_1_to_5": 5,
                "interaction_rating_1_to_5": 5,
                "criterion_confidence": 90,
            },
        )
    receipt_a = first.submit("blind-recognition", response)
    receipt_b = second.submit("blind-recognition", response)
    assert receipt_a == receipt_b
    assert first.prompt_disclosure_permitted
    assert first.next_stage == "prompt-aware-criteria"
    with pytest.raises(ValueError, match="already locked"):
        first.submit("blind-recognition", response)
    exported = first.export()
    assert exported["completed_stages"] == ["blind-recognition"]
    assert exported["receipts"][0]["receipt_hash"].startswith("sha256:")


def test_response_validation_rejects_identifiers_ranges_and_unknown_stages() -> None:
    validation = validate_calibration_response(
        "blind-recognition",
        {
            "animal_open_text": "pelican",
            "mobile_object_open_text": "bicycle",
            "relation_open_text": "rides_on",
            "recognition_confidence": 101,
            "email": "not-permitted@example.test",
        },
    )
    assert not validation.valid
    assert validation.invalid_fields == ("recognition_confidence",)
    assert validation.prohibited_fields == ("email",)

    pair = validate_calibration_response("pairwise-preference", {"pairwise_winner": "unknown"})
    assert not pair.valid
    assert pair.invalid_fields == ("pairwise_winner",)
    with pytest.raises(ValueError, match="unknown calibration stage"):
        validate_calibration_response("post-hoc", {})


def test_analysis_counts_invalid_rows_and_computes_inter_rater_alpha() -> None:
    rows = [
        {
            **_blind("shared-artifact"),
            "duplicate_group_id": None,
        },
        {
            **_blind("shared-artifact"),
            "duplicate_group_id": None,
            "response": {
                **_blind("shared-artifact")["response"],
                "animal_open_text": "heron",
            },
        },
        {"stage": "pairwise-preference", "response": {"pairwise_winner": "invalid"}},
    ]
    result = analyse_calibration_responses(rows)
    assert result["responses_received"] == 3
    assert result["valid_responses"] == 2
    assert result["invalid_responses"] == 1
    assert "animal_open_text" in result["nominal_alpha_by_field"]
    assert result["limitations"] == []
