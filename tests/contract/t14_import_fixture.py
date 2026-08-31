"""Closed metadata-only toy import fixture; no responses or production intake."""

from __future__ import annotations

import hashlib

BINDINGS = {
    "schema_version": "t14-toy-envelope-v1",
    "protocol": "toy-protocol-not-approved",
    "consent": "toy-consent-not-operative",
    "asset_sha256": hashlib.sha256(b"non-study toy asset marker").hexdigest(),
    "provenance": "synthetic-envelope-only",
    "payload_marker": "no-response",
}
FIELDS = frozenset(BINDINGS) | {
    "participant",
    "presentation",
    "receipt",
    "withdrawn",
    "expired",
}
TOYS = {f"toy-person-{index:02d}": index for index in range(12)}


def envelope(index: int) -> dict[str, object]:
    """Supply fixed metadata, never visual answers or a human identity."""
    if type(index) is not int or index not in range(12):
        raise ValueError("toy index required")
    return {
        **BINDINGS,
        "participant": f"toy-person-{index:02d}",
        "presentation": f"toy-presentation-{index:02d}",
        "receipt": f"toy-receipt-{index:02d}",
        "withdrawn": False,
        "expired": False,
    }


def inspect_batch(rows: object) -> dict[str, object]:
    """Quarantine the entire batch on any failure, returning no input values.

    Withdrawal/expiry are toy flags, not verified production eligibility. All
    results deny downstream authority; this function has no I/O or stored state.
    """
    reasons: set[str] = set()
    count = len(rows) if type(rows) is list else 0
    receipts: set[str] = set()
    presentations: set[str] = set()
    if type(rows) is not list or not 1 <= count <= 12:
        reasons.add("batch-shape")
    else:
        for row in rows:
            if type(row) is not dict:
                reasons.add("record-type")
                continue
            if set(row) != FIELDS:
                reasons.add("fields")
                continue
            if any(
                type(row[key]) is not str or row[key] != value for key, value in BINDINGS.items()
            ):
                reasons.add("binding")
            person = row["participant"]
            if type(person) is not str or person not in TOYS:
                reasons.add("identity")
            else:
                index = TOYS[person]
                if row["presentation"] != f"toy-presentation-{index:02d}":
                    reasons.add("entitlement")
                if row["receipt"] != f"toy-receipt-{index:02d}":
                    reasons.add("receipt")
            for field, seen, code in (
                ("receipt", receipts, "duplicate-receipt"),
                ("presentation", presentations, "duplicate-presentation"),
            ):
                value = row[field]
                if type(value) is not str or len(value) > 64:
                    reasons.add("identifier-type")
                elif value in seen:
                    reasons.add(code)
                else:
                    seen.add(value)
            if any(type(row[field]) is not bool for field in ("withdrawn", "expired")):
                reasons.add("eligibility-type")
            elif row["withdrawn"] or row["expired"]:
                reasons.add("ineligible")
    return {
        "schema_version": "t14-toy-import-check-v1",
        "status": "quarantine" if reasons else "fixture-valid-not-approved-for-use",
        "record_count": count,
        "reason_codes": sorted(reasons),
        "authority_effect": dict.fromkeys(
            ("collection", "analysis", "unblinding", "promotion", "publication"), False
        ),
    }
