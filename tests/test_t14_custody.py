from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pelicanbench.t14_custody import build_restricted_custody_artifacts, canonical_bytes


def test_t14_custody_artifacts_are_deterministic_and_fail_closed(root: Path) -> None:
    candidate_bytes = (root / "benchmark/fixtures/repair/candidate/manifest.json").read_bytes()
    candidate = json.loads(candidate_bytes)
    kwargs = {
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "secret": b"t14-test-custody-secret-material-32-bytes",
        "custodian_id": "test-custodian",
        "custody_classification": "procedural-self-custody-not-independent",
        "created_at": "2026-08-29T00:00:00Z",
    }
    first = build_restricted_custody_artifacts(candidate, **kwargs)
    second = build_restricted_custody_artifacts(candidate, **kwargs)
    assert tuple(canonical_bytes(value) for value in first) == tuple(
        canonical_bytes(value) for value in second
    )
    aliases, schedule, receipt = first
    assert len(aliases["entries"]) == 96
    assert len(schedule["assignments"]) == 106
    assert sum(item["is_duplicate"] for item in schedule["assignments"]) == 10
    assert len({item["assignment_alias"] for item in schedule["assignments"]}) == 106
    assert receipt["secret_recorded"] is False
    assert all(value is False for value in receipt["authority_effect"].values())
    assert receipt["alias_manifest_sha256"] == hashlib.sha256(canonical_bytes(aliases)).hexdigest()
    assert (
        receipt["restricted_duplicate_schedule_sha256"]
        == hashlib.sha256(canonical_bytes(schedule)).hexdigest()
    )

    with pytest.raises(ValueError, match="at least 32 bytes"):
        build_restricted_custody_artifacts(candidate, **(kwargs | {"secret": b"short"}))


def test_t14_custody_rejects_candidate_cardinality_drift(root: Path) -> None:
    candidate = json.loads(
        (root / "benchmark/fixtures/repair/candidate/manifest.json").read_bytes()
    )
    candidate["episodes"].pop()
    with pytest.raises(ValueError, match="exactly 96"):
        build_restricted_custody_artifacts(
            candidate,
            candidate_sha256="0" * 64,
            secret=b"t14-test-custody-secret-material-32-bytes",
            custodian_id="test-custodian",
            custody_classification="procedural-self-custody-not-independent",
            created_at="2026-08-29T00:00:00Z",
        )
