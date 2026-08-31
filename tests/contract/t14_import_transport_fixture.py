"""Bounded raw JSON wrapper for toy metadata only; no I/O or human responses."""

from __future__ import annotations

import json

from t14_import_fixture import inspect_batch

MAX_BYTES = 16384


def _quarantine(reason: str) -> dict[str, object]:
    result = inspect_batch(None)
    result["reason_codes"] = [reason]
    return result


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate key")
        output[key] = value
    return output


def _reject_number(value: str) -> object:
    raise ValueError("numeric tokens are not toy metadata")


def inspect_encoded_batch(source: object) -> dict[str, object]:
    """Decode at most 16 KiB of strict UTF-8, then inspect the closed toy contract.

    Only a list of flat objects can match that contract. Limit structural depth
    before JSON decoding; duplicate keys and all numeric tokens fail closed.
    Errors contain reason codes only. No persistent replay or eligibility exists.
    """
    if type(source) is not bytes or len(source) > MAX_BYTES:
        return _quarantine("transport-size-or-type")
    try:
        text = source.decode("utf-8")
    except UnicodeError:
        return _quarantine("json-encoding")
    depth = 0
    quoted = False
    escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 2:
                return _quarantine("json-depth")
        elif char in "]}":
            depth -= 1
    try:
        rows = json.loads(
            text,
            object_pairs_hook=_object,
            parse_int=_reject_number,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (ValueError, RecursionError):
        return _quarantine("json-encoding")
    return inspect_batch(rows)
