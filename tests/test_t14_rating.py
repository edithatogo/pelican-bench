from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pelicanbench.t14_custody import build_restricted_custody_artifacts, canonical_bytes
from pelicanbench.t14_rating import (
    FrozenRatingSession,
    HashChainedRatingLedger,
    load_frozen_rating_session,
    validate_rating_authorization,
    validate_rating_row,
)


def _prepared_session(tmp_path: Path, root: Path) -> tuple[FrozenRatingSession, dict[str, Path]]:
    candidate_path = root / "benchmark/fixtures/repair/candidate/manifest.json"
    candidate_raw = candidate_path.read_bytes()
    candidate = json.loads(candidate_raw)
    aliases, schedule, _ = build_restricted_custody_artifacts(
        candidate,
        candidate_sha256=hashlib.sha256(candidate_raw).hexdigest(),
        secret=b"t14-rating-test-secret-material-32-bytes",
        custodian_id="test-custodian",
        custody_classification="procedural-self-custody-not-independent",
        created_at="2026-08-29T00:00:00Z",
    )
    alias_path = tmp_path / "alias.json"
    schedule_path = tmp_path / "schedule.json"
    alias_path.write_bytes(canonical_bytes(aliases))
    schedule_path.write_bytes(canonical_bytes(schedule))
    alias_path.chmod(0o600)
    schedule_path.chmod(0o600)
    freeze = {"decision": "freeze-exact-bytes"}
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    packet = {
        "status": "frozen-procedural-non-independent-e2",
        "study_id": aliases["study_id"],
        "ratings_authorized": False,
        "unblinding_authorized": False,
        "normative_manifest": {"sha256": hashlib.sha256(candidate_raw).hexdigest()},
        "pending_required_inputs": {
            "secret_bound_alias_manifest_sha256": hashlib.sha256(
                alias_path.read_bytes()
            ).hexdigest(),
            "restricted_duplicate_schedule_sha256": hashlib.sha256(
                schedule_path.read_bytes()
            ).hexdigest(),
            "steward_freeze_decision_receipt_sha256": hashlib.sha256(
                freeze_path.read_bytes()
            ).hexdigest(),
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    session = load_frozen_rating_session(
        root=root,
        packet_path=packet_path,
        freeze_receipt_path=freeze_path,
        candidate_path=candidate_path,
        alias_path=alias_path,
        assignment_path=schedule_path,
    )
    return session, {
        "packet": packet_path,
        "freeze": freeze_path,
        "candidate": candidate_path,
        "alias": alias_path,
        "assignment": schedule_path,
    }


def test_frozen_rating_session_exposes_assignment_aliases_only(tmp_path: Path, root: Path) -> None:
    session, _ = _prepared_session(tmp_path, root)
    assert len(session.assignments) == 106
    assert len(session.public_assignments) == 106
    assert all(set(row) == {"assignment_alias"} for row in session.public_assignments)
    assert len({row["assignment_alias"] for row in session.public_assignments}) == 106


def test_rating_authorization_is_exactly_scoped(tmp_path: Path, root: Path) -> None:
    session, _ = _prepared_session(tmp_path, root)
    receipt = {
        "receipt_kind": "t14-rating-authorization",
        "study_id": session.study_id,
        "freeze_receipt_sha256": session.freeze_receipt_sha256,
        "decision_maker": "benchmark-steward",
        "decision": "authorize-blinded-rating",
        "rating_route": "qualification",
        "assignment_limit": 12,
        "authority_effect": {
            "ratings": True,
            "score_promotion": False,
            "attestation": False,
            "release": False,
            "publication": False,
            "unblinding": False,
        },
    }
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validate_rating_authorization(path, session) == receipt
    receipt["authority_effect"]["unblinding"] = True
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="scope drift"):
        validate_rating_authorization(path, session)
    receipt["authority_effect"]["unblinding"] = False
    receipt["assignment_limit"] = 13
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="qualification assignment limit"):
        validate_rating_authorization(path, session)

    receipt["rating_route"] = "complete"
    receipt["assignment_limit"] = 106
    path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validate_rating_authorization(path, session)["rating_route"] == "complete"
    receipt["assignment_limit"] = 105
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="complete-wave assignment limit"):
        validate_rating_authorization(path, session)
    receipt["rating_route"] = "unknown"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="route drift"):
        validate_rating_authorization(path, session)


def test_frozen_session_rejects_permission_and_authority_drift(tmp_path: Path, root: Path) -> None:
    _, paths = _prepared_session(tmp_path, root)
    paths["alias"].chmod(0o644)
    with pytest.raises(ValueError, match="permissions are too broad"):
        load_frozen_rating_session(
            root=root,
            packet_path=paths["packet"],
            freeze_receipt_path=paths["freeze"],
            candidate_path=paths["candidate"],
            alias_path=paths["alias"],
            assignment_path=paths["assignment"],
        )
    paths["alias"].chmod(0o600)
    packet = json.loads(paths["packet"].read_text())
    packet["status"] = "pending"
    paths["packet"].write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="not procedurally frozen"):
        load_frozen_rating_session(
            root=root,
            packet_path=paths["packet"],
            freeze_receipt_path=paths["freeze"],
            candidate_path=paths["candidate"],
            alias_path=paths["alias"],
            assignment_path=paths["assignment"],
        )
    packet["status"] = "frozen-procedural-non-independent-e2"
    packet["ratings_authorized"] = True
    paths["packet"].write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="authority state drift"):
        load_frozen_rating_session(
            root=root,
            packet_path=paths["packet"],
            freeze_receipt_path=paths["freeze"],
            candidate_path=paths["candidate"],
            alias_path=paths["alias"],
            assignment_path=paths["assignment"],
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"assignment_alias": ""}, "assignment alias"),
        ({"target_corrected": "yes"}, "target_corrected"),
        ({"preservation_score_1_to_5": True}, "preservation score"),
        ({"preservation_score_1_to_5": 6}, "preservation score"),
        ({"confidence_0_to_100": True}, "confidence"),
        ({"confidence_0_to_100": 101}, "confidence"),
    ],
)
def test_rating_rows_fail_closed(mutation: dict[str, object], message: str) -> None:
    row: dict[str, object] = {
        "assignment_alias": "assignment-a",
        "target_corrected": True,
        "preservation_score_1_to_5": 4,
        "introduced_defect": False,
        "confidence_0_to_100": 80,
        "uncertain": False,
    }
    with pytest.raises(ValueError, match=message):
        validate_rating_row(row | mutation)


def test_rating_ledger_is_append_only_hash_chained_and_private(tmp_path: Path) -> None:
    path = tmp_path / "restricted" / "ratings.jsonl"
    ledger = HashChainedRatingLedger(path, {"assignment-a", "assignment-b"})
    first = ledger.append(
        {
            "assignment_alias": "assignment-a",
            "target_corrected": True,
            "preservation_score_1_to_5": 4,
            "introduced_defect": False,
            "confidence_0_to_100": 80,
            "uncertain": False,
        },
        saved_at="2026-08-29T00:00:00Z",
    )
    second = ledger.append(
        {
            "assignment_alias": "assignment-b",
            "target_corrected": None,
            "preservation_score_1_to_5": 3,
            "introduced_defect": None,
            "confidence_0_to_100": 40,
            "uncertain": True,
        },
        saved_at="2026-08-29T00:01:00Z",
    )
    assert second["previous_event_sha256"] == first["event_sha256"]
    assert len(ledger.latest_rows()) == 2
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError, match="already has"):
        ledger.append(ledger.latest_rows()[0], saved_at="2026-08-29T00:02:00Z")
    with pytest.raises(ValueError, match="not in the frozen session"):
        ledger.append(
            ledger.latest_rows()[0] | {"assignment_alias": "assignment-unknown"},
            saved_at="2026-08-29T00:02:00Z",
        )
    lines = path.read_text().splitlines()
    event = json.loads(lines[0])
    event["confidence_0_to_100"] = 99
    lines[0] = json.dumps(event)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="hash drift"):
        ledger.read()


def test_frozen_response_validator_requires_alias_only_106_rows(
    tmp_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = root / "scripts/validate_t14_rating_template.py"
    spec = importlib.util.spec_from_file_location("validate_t14_rating_template_v2", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = {
        "assignment_alias": "",
        "target_corrected": True,
        "preservation_score_1_to_5": 4,
        "introduced_defect": False,
        "confidence_0_to_100": 80,
        "uncertain": False,
    }
    payload = {
        "schema_version": "2.0.0",
        "status": "steward-submitted",
        "responses": [
            row | {"assignment_alias": f"assignment-{index:03d}"} for index in range(106)
        ],
        "privacy": {"direct_identifiers": False, "free_text": False},
    }
    path = tmp_path / "response.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(script), str(path)])
    assert module.main() == 0
    payload["responses"][0]["repair_id"] = "must-not-be-exposed"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="non-blinded"):
        module.main()
