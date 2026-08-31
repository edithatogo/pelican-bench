"""Synthetic envelope checks cannot accept people or promote classifications."""

import copy

import pytest
from t14_import_fixture import envelope, inspect_batch


def test_valid_fixture_does_not_authorize_use():
    rows = [envelope(0), envelope(1)]
    before = copy.deepcopy(rows)
    result = inspect_batch(rows)
    assert result["status"] == "fixture-valid-not-approved-for-use"
    assert result["record_count"] == 2
    assert not any(result["authority_effect"].values())
    assert rows == before
    assert "records" not in result and "responses" not in result


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("schema_version", "other-schema", "binding"),
        ("protocol", "D044", "binding"),
        ("consent", "another-version", "binding"),
        ("asset_sha256", "0" * 64, "binding"),
        ("provenance", "human", "binding"),
        ("participant", "real-person", "identity"),
        ("presentation", "unknown", "entitlement"),
        ("receipt", "reused", "receipt"),
        ("withdrawn", True, "ineligible"),
        ("expired", True, "ineligible"),
        ("withdrawn", 0, "eligibility-type"),
        ("expired", "false", "eligibility-type"),
        ("payload_marker", "yes", "binding"),
    ],
)
def test_invalid_envelope_quarantined_without_echo(field, value, reason):
    row = envelope(0)
    row[field] = value
    result = inspect_batch([row])
    assert result["status"] == "quarantine"
    assert reason in result["reason_codes"]
    assert str(value) not in str(result["reason_codes"])
    assert not any(result["authority_effect"].values())


@pytest.mark.parametrize("field", ["answer", "name", "email", "model_id", "score", "secret"])
def test_extra_fields_rejected_without_reading_or_logging_payload(field):
    row = envelope(0)
    row[field] = "sensitive-sentinel"
    result = inspect_batch([row])
    assert result["reason_codes"] == ["fields"]
    assert "sensitive-sentinel" not in str(result)


def test_missing_field_and_cross_participant_binding_rejected():
    row = envelope(0)
    del row["consent"]
    assert inspect_batch([row])["reason_codes"] == ["fields"]
    row = envelope(0)
    row["presentation"] = envelope(1)["presentation"]
    assert "entitlement" in inspect_batch([row])["reason_codes"]


def test_duplicate_records_are_not_independent_contributions():
    result = inspect_batch([envelope(0), envelope(0)])
    assert result["status"] == "quarantine"
    assert "duplicate-receipt" in result["reason_codes"]
    assert "duplicate-presentation" in result["reason_codes"]


@pytest.mark.parametrize("rows", [None, {}, "payload", [], [None], ["payload"], [1], [{}] * 13])
def test_malformed_and_unbounded_input_fails_closed(rows):
    assert inspect_batch(rows)["status"] == "quarantine"


def test_mixed_valid_invalid_batch_is_atomic():
    bad = envelope(1)
    bad["withdrawn"] = True
    result = inspect_batch([envelope(0), bad])
    assert result["status"] == "quarantine"
    assert result["record_count"] == 2
    assert "accepted" not in result


@pytest.mark.parametrize("index", [-1, 12, True, "0"])
def test_fixture_factory_rejects_non_toy_indices(index):
    with pytest.raises(ValueError, match="toy index"):
        envelope(index)


def test_all_toys_and_repeated_batch_do_not_establish_persisted_intake():
    rows = [envelope(index) for index in range(12)]
    first = inspect_batch(rows)
    assert first["status"] == "fixture-valid-not-approved-for-use"
    assert first["record_count"] == 12
    assert inspect_batch(rows) == first  # Deliberately no cross-batch replay state.


@pytest.mark.parametrize("field", ["participant", "presentation", "receipt"])
@pytest.mark.parametrize("value", [[], {}, True, "x" * 65])
def test_malformed_identifiers_are_quarantined(field, value):
    row = envelope(0)
    row[field] = value
    assert inspect_batch([row])["status"] == "quarantine"
