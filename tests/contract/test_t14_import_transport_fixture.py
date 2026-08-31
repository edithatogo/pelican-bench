"""Raw JSON boundary tests for closed toy metadata; never human intake."""

import json

import pytest
from t14_import_fixture import envelope, inspect_batch
from t14_import_transport_fixture import MAX_BYTES, inspect_encoded_batch


def encoded():
    return json.dumps([envelope(index) for index in range(12)]).encode()


def test_exact_toy_batch_and_size_boundary():
    source = encoded()
    expected = inspect_batch([envelope(index) for index in range(12)])
    assert inspect_encoded_batch(source) == expected
    assert inspect_encoded_batch(source + b" " * (MAX_BYTES - len(source))) == expected
    assert not any(expected["authority_effect"].values())


@pytest.mark.parametrize(
    "source",
    [None, "[]", bytearray(b"[]"), b" " * 16385, b"\xff", b"\xef\xbb\xbf[]", b"", b"[", b"[]extra"],
)
def test_bad_transport_is_quarantined_without_echo(source):
    result = inspect_encoded_batch(source)
    assert result["status"] == "quarantine"
    assert result["record_count"] == 0
    assert not any(result["authority_effect"].values())


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e9999", "12", "1.2"])
def test_numeric_tokens_never_enter_closed_toy_contract(value):
    result = inspect_encoded_batch(('[{"secret": ' + value + "}]").encode())
    assert result["status"] == "quarantine"
    assert result["reason_codes"] == ["json-encoding"]


@pytest.mark.parametrize("key", ['"participant"', '"partic\\u0069pant"'])
def test_duplicate_keys_rejected_even_when_final_value_is_valid(key):
    source = json.dumps([envelope(0)]).replace(
        '"participant":', '"participant": "sensitive-sentinel", ' + key + ":"
    )
    result = inspect_encoded_batch(source.encode())
    assert result["reason_codes"] == ["json-encoding"]
    assert "sensitive-sentinel" not in str(result)


@pytest.mark.parametrize("source", [b"[[[]]]", b'[{"x": {}}]', b"[" * 4000 + b"]" * 4000])
def test_nested_structures_rejected_before_decoder(monkeypatch, source):
    def unexpected(*args, **kwargs):
        raise AssertionError("decoder must not see excessive nesting")

    monkeypatch.setattr(json, "loads", unexpected)
    result = inspect_encoded_batch(source)
    assert result["reason_codes"] == ["json-depth"]


def test_brackets_and_escaped_quotes_inside_strings_do_not_count_as_depth():
    row = envelope(0)
    row["extra"] = '[{\\"sensitive-sentinel\\"}]'
    result = inspect_encoded_batch(json.dumps([row]).encode())
    assert result["reason_codes"] == ["fields"]
    assert "sensitive-sentinel" not in str(result)


@pytest.mark.parametrize("source", [b"{}", b"null", b"true", b"[]"])
def test_valid_json_with_invalid_batch_shape_remains_quarantined(source):
    assert inspect_encoded_batch(source)["reason_codes"] == ["batch-shape"]
