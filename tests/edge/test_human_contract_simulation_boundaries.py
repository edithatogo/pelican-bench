from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError

import pelicanbench.simulation as simulation
from pelicanbench.contracts import (
    ContractVerification,
    load_contract,
    validate_contract_directory,
)
from pelicanbench.human_study import (
    CalibrationSession,
    _nominal_alpha,
    analyse_calibration_responses,
    validate_calibration_response,
)
from pelicanbench.simulation import FaultInjection, run_canvas_simulation

pytestmark = pytest.mark.edge
ROOT = Path(__file__).parents[2]


def _blind_response() -> dict[str, object]:
    return {
        "animal_open_text": "pelican",
        "mobile_object_open_text": "bicycle",
        "relation_open_text": "rides_on",
        "recognition_confidence": 80,
    }


def _criteria_response() -> dict[str, object]:
    return {
        "animal_defects": "none",
        "object_defects": "none",
        "interaction_defects": "none",
        "animal_rating_1_to_5": 5,
        "object_rating_1_to_5": 5,
        "interaction_rating_1_to_5": 5,
        "criterion_confidence": 90,
    }


def test_calibration_session_rejects_unassigned_and_invalid_stages_and_chains_receipts() -> None:
    session = CalibrationSession(
        "assignment",
        "artifact",
        permitted_stages=("blind-recognition", "prompt-aware-criteria", "pairwise-preference"),
    )
    with pytest.raises(ValueError, match="not part"):
        session.submit("not-assigned", {})
    with pytest.raises(ValueError, match="missing_fields"):
        session.submit("blind-recognition", {})

    first = session.submit("blind-recognition", _blind_response())
    second = session.submit("prompt-aware-criteria", _criteria_response())
    third = session.submit("pairwise-preference", {"pairwise_winner": "tie"})
    assert second.previous_receipt_hash == first.receipt_hash
    assert third.previous_receipt_hash == second.receipt_hash
    assert session.next_stage is None
    assert third.as_dict()["receipt_hash"] == third.receipt_hash


def test_response_validation_handles_missing_nonfinite_and_noninteger_values() -> None:
    missing = validate_calibration_response("blind-recognition", {})
    assert set(missing.missing_fields) == {
        "animal_open_text",
        "mobile_object_open_text",
        "relation_open_text",
        "recognition_confidence",
    }
    nonfinite = validate_calibration_response(
        "blind-recognition",
        {**_blind_response(), "recognition_confidence": float("nan")},
    )
    assert nonfinite.invalid_fields == ("recognition_confidence",)
    criteria = validate_calibration_response(
        "prompt-aware-criteria",
        {**_criteria_response(), "animal_rating_1_to_5": 4.5},
    )
    assert criteria.invalid_fields == ("animal_rating_1_to_5",)


def test_human_analysis_records_invalid_shapes_and_empty_reliability() -> None:
    result = analyse_calibration_responses(
        [
            {"stage": "blind-recognition", "response": "not-a-mapping"},
            {"stage": "unknown", "response": {}},
            {"stage": "pairwise-preference", "response": {"pairwise_winner": "A"}},
        ]
    )
    assert result["responses_received"] == 3
    assert result["valid_responses"] == 1
    assert result["invalid_responses"] == 2
    assert result["limitations"] == ["inter-rater-alpha-unavailable"]
    assert _nominal_alpha([]) is None
    assert _nominal_alpha([["same", "same"]]) == 1.0


def test_contract_directory_rejects_empty_duplicate_and_invalid_schema(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no contracts"):
        validate_contract_directory(tmp_path)

    source = ROOT / "benchmark/contracts/human-rating-exchange.json"
    (tmp_path / "a.json").write_bytes(source.read_bytes())
    (tmp_path / "b.json").write_bytes(source.read_bytes())
    with pytest.raises(ValueError, match="duplicate contract"):
        validate_contract_directory(tmp_path)

    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps(
            {
                "contract_id": "contract:invalid",
                "schema_version": "1.0.0",
                "provider": "fixture",
                "description": "invalid schema",
                "request_schema": {"type": "not-a-json-schema-type"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SchemaError):
        load_contract(invalid)


def test_contract_and_simulation_receipts_cover_serialisation_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verification = ContractVerification(
        contract_id="contract:fixture",
        contract_digest="sha256:fixture",
        side="event",
        valid=True,
        errors=(),
        payload_hash="sha256:payload",
    )
    assert verification.as_dict()["errors"] == []

    with pytest.raises(ValueError, match="max_elements"):
        run_canvas_simulation([], max_elements=0)
    with pytest.raises(ValueError, match="fault index"):
        run_canvas_simulation([], faults=[FaultInjection(-1, {})])

    receipt = run_canvas_simulation([], seed=0)
    assert "receipt_hash" not in receipt.as_dict(include_receipt_hash=False)
    assert receipt.as_dict()["receipt_hash"] == receipt.receipt_hash

    original = simulation.run_canvas_simulation
    calls = 0

    def divergent(*args, **kwargs):
        nonlocal calls
        calls += 1
        value = original(*args, **kwargs)
        if calls == 2:
            return simulation.SimulationReceipt(
                **{**value.as_dict(include_receipt_hash=False), "receipt_hash": "sha256:different"}
            )
        return value

    monkeypatch.setattr(simulation, "run_canvas_simulation", divergent)
    with pytest.raises(AssertionError, match="diverged"):
        simulation.assert_deterministic_replay([])
