"""Existing learning boundaries only; no new storage or promotion policy."""

import json

import pytest

from pelicanbench.self_learning import LearningRecord, can_auto_promote, load_records

pytestmark = pytest.mark.contract


def record(**changes):
    fields = {
        "track": "T16",
        "phase": "P3",
        "observation": "synthetic boundary fixture",
        "evidence": ("toy:one",),
        "strategy": "test only",
        "result": "not empirical",
        "proposed_heuristic": "none",
        "confidence": 0.8,
        "scope": "synthetic fixture",
        "review_trigger": "accountable review",
    }
    fields.update(changes)
    return LearningRecord(**fields)


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -float("inf"), -0.01, 1.01])
def test_invalid_confidence_fails_existing_validation(confidence):
    with pytest.raises(ValueError, match="confidence"):
        record(confidence=confidence)


@pytest.mark.parametrize("status", ["proposed", "validated", "promoted", "rejected", "expired"])
@pytest.mark.parametrize("confidence", [0.0, 0.7, 1.0])
def test_no_auto_promotion_for_any_existing_status(status, confidence):
    assert can_auto_promote(record(status=status, confidence=confidence)) is False


@pytest.mark.parametrize("suffix", [b'{"partial":', b"not-json\n", b'{"nested": [1,]}\n'])
def test_malformed_ledger_is_rejected_without_rewriting_bytes(tmp_path, suffix):
    path = tmp_path / "synthetic-ledger.jsonl"
    original = b'{"fixture": "valid-prefix"}\n' + suffix
    path.write_bytes(original)
    with pytest.raises(json.JSONDecodeError):
        load_records(path)
    assert path.read_bytes() == original


def test_missing_and_empty_ledger_remain_empty_without_creation(tmp_path):
    path = tmp_path / "synthetic-ledger.jsonl"
    assert load_records(path) == []
    assert not path.exists()
    path.write_bytes(b"")
    assert load_records(path) == []
    assert path.read_bytes() == b""
