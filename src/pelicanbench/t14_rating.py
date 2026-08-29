"""Fail-closed preparation and local ledger support for frozen T14 ratings."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

RATING_FIELDS = (
    "target_corrected",
    "preservation_score_1_to_5",
    "introduced_defect",
    "confidence_0_to_100",
    "uncertain",
)
JsonObject = dict[str, Any]


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load(path: Path) -> tuple[JsonObject, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(JsonObject, value), raw


def _require_private(path: Path) -> None:
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError(f"restricted artifact permissions are too broad: {path.name}")


def _asset(root: Path, relative: object, expected_sha256: object) -> Path:
    if not isinstance(relative, str) or not isinstance(expected_sha256, str):
        raise ValueError("candidate asset path or hash is invalid")
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("candidate asset is missing or outside the repository")
    if sha256_bytes(path.read_bytes()) != expected_sha256:
        raise ValueError("candidate asset commitment drift")
    return path


@dataclass(frozen=True)
class FrozenRatingSession:
    study_id: str
    freeze_receipt_sha256: str
    candidate_manifest_sha256: str
    alias_manifest_sha256: str
    assignment_manifest_sha256: str
    assignments: tuple[dict[str, Any], ...]

    @property
    def public_assignments(self) -> tuple[dict[str, str], ...]:
        return tuple({"assignment_alias": row["assignment_alias"]} for row in self.assignments)


def load_frozen_rating_session(
    *,
    root: Path,
    packet_path: Path,
    freeze_receipt_path: Path,
    candidate_path: Path,
    alias_path: Path,
    assignment_path: Path,
) -> FrozenRatingSession:
    """Validate frozen public commitments and restricted maps without exposing labels."""
    root = root.resolve()
    packet, _ = _load(packet_path)
    freeze, freeze_raw = _load(freeze_receipt_path)
    candidate, candidate_raw = _load(candidate_path)
    aliases, alias_raw = _load(alias_path)
    schedule, schedule_raw = _load(assignment_path)
    _require_private(alias_path)
    _require_private(assignment_path)

    if packet.get("status") != "frozen-procedural-non-independent-e2":
        raise ValueError("T14 packet is not procedurally frozen")
    if (
        packet.get("ratings_authorized") is not False
        or packet.get("unblinding_authorized") is not False
    ):
        raise ValueError("frozen packet authority state drift")
    if packet.get("study_id") != aliases.get("study_id") or packet.get("study_id") != schedule.get(
        "study_id"
    ):
        raise ValueError("study identifier drift")
    candidate_sha256 = sha256_bytes(candidate_raw)
    if candidate_sha256 != packet["normative_manifest"]["sha256"]:
        raise ValueError("candidate manifest commitment drift")
    if (
        sha256_bytes(alias_raw)
        != packet["pending_required_inputs"]["secret_bound_alias_manifest_sha256"]
    ):
        raise ValueError("restricted alias commitment drift")
    if (
        sha256_bytes(schedule_raw)
        != packet["pending_required_inputs"]["restricted_duplicate_schedule_sha256"]
    ):
        raise ValueError("restricted assignment commitment drift")
    if (
        sha256_bytes(freeze_raw)
        != packet["pending_required_inputs"]["steward_freeze_decision_receipt_sha256"]
    ):
        raise ValueError("freeze receipt commitment drift")
    if freeze.get("decision") != "freeze-exact-bytes":
        raise ValueError("freeze decision drift")
    if (
        aliases.get("candidate_manifest_sha256") != candidate_sha256
        or schedule.get("candidate_manifest_sha256") != candidate_sha256
    ):
        raise ValueError("restricted candidate binding drift")

    episodes_value = candidate.get("episodes")
    alias_entries_value = aliases.get("entries")
    assignments_value = schedule.get("assignments")
    if not isinstance(episodes_value, list):
        raise ValueError("frozen candidate must contain 96 episodes")
    if not isinstance(alias_entries_value, list):
        raise ValueError("restricted alias manifest must contain 96 entries")
    if not isinstance(assignments_value, list):
        raise ValueError("restricted assignment manifest must contain 106 assignments")
    episodes = cast(list[JsonObject], episodes_value)
    alias_entries = cast(list[JsonObject], alias_entries_value)
    assignments = cast(list[JsonObject], assignments_value)
    if len(episodes) != 96:
        raise ValueError("frozen candidate must contain 96 episodes")
    if len(alias_entries) != 96:
        raise ValueError("restricted alias manifest must contain 96 entries")
    if len(assignments) != 106:
        raise ValueError("restricted assignment manifest must contain 106 assignments")
    episode_by_id = {str(row.get("repair_id")): row for row in episodes}
    alias_by_id = {str(row.get("repair_id")): row.get("episode_alias") for row in alias_entries}
    if len(episode_by_id) != 96 or len(alias_by_id) != 96 or set(episode_by_id) != set(alias_by_id):
        raise ValueError("candidate and alias identifiers do not match")

    prepared: list[dict[str, Any]] = []
    assignment_aliases: set[str] = set()
    duplicate_count = 0
    for expected_ordinal, assignment in enumerate(assignments, 1):
        if assignment.get("ordinal") != expected_ordinal:
            raise ValueError("assignment ordinal drift")
        repair_id = str(assignment.get("repair_id"))
        assignment_alias = assignment.get("assignment_alias")
        if (
            not isinstance(assignment_alias, str)
            or not assignment_alias
            or assignment_alias in assignment_aliases
        ):
            raise ValueError("assignment alias is missing or duplicated")
        assignment_aliases.add(assignment_alias)
        if assignment.get("episode_alias") != alias_by_id.get(repair_id):
            raise ValueError("assignment alias binding drift")
        episode = episode_by_id.get(repair_id)
        if episode is None:
            raise ValueError("assignment references an unknown candidate")
        before = _asset(root, episode.get("before"), episode.get("before_sha256"))
        after = _asset(root, episode.get("after_reference"), episode.get("after_sha256"))
        is_duplicate = assignment.get("is_duplicate") is True
        duplicate_count += is_duplicate
        prepared.append(
            {
                "assignment_alias": assignment_alias,
                "_before": str(before),
                "_after": str(after),
            }
        )
    if duplicate_count != 10:
        raise ValueError("duplicate assignment count drift")
    return FrozenRatingSession(
        study_id=packet["study_id"],
        freeze_receipt_sha256=sha256_bytes(freeze_raw),
        candidate_manifest_sha256=candidate_sha256,
        alias_manifest_sha256=sha256_bytes(alias_raw),
        assignment_manifest_sha256=sha256_bytes(schedule_raw),
        assignments=tuple(prepared),
    )


def validate_rating_authorization(path: Path, session: FrozenRatingSession) -> dict[str, Any]:
    """Require an exact, rating-only steward authorization before interface launch."""
    receipt, _ = _load(path)
    if receipt.get("receipt_kind") != "t14-rating-authorization":
        raise ValueError("rating authorization kind drift")
    if receipt.get("study_id") != session.study_id:
        raise ValueError("rating authorization study drift")
    if receipt.get("freeze_receipt_sha256") != session.freeze_receipt_sha256:
        raise ValueError("rating authorization freeze binding drift")
    if (
        receipt.get("decision_maker") != "benchmark-steward"
        or receipt.get("decision") != "authorize-blinded-rating"
    ):
        raise ValueError("rating authorization decision drift")
    route = receipt.get("rating_route")
    limit = receipt.get("assignment_limit")
    if route == "qualification":
        if not isinstance(limit, int) or isinstance(limit, bool) or not 8 <= limit <= 12:
            raise ValueError("qualification assignment limit drift")
    elif route == "complete":
        if limit != 106:
            raise ValueError("complete-wave assignment limit drift")
    else:
        raise ValueError("rating authorization route drift")
    effect = receipt.get("authority_effect")
    expected = {
        "ratings": True,
        "score_promotion": False,
        "attestation": False,
        "release": False,
        "publication": False,
        "unblinding": False,
    }
    if effect != expected:
        raise ValueError("rating authorization scope drift")
    return receipt


def validate_rating_row(row: Mapping[str, Any]) -> dict[str, Any]:
    alias = row.get("assignment_alias")
    if not isinstance(alias, str) or not alias:
        raise ValueError("rating assignment alias is invalid")
    for field in ("target_corrected", "introduced_defect", "uncertain"):
        if row.get(field) is not None and not isinstance(row.get(field), bool):
            raise ValueError(f"rating field {field} must be boolean or null")
    preservation = row.get("preservation_score_1_to_5")
    if (
        not isinstance(preservation, int)
        or isinstance(preservation, bool)
        or not 1 <= preservation <= 5
    ):
        raise ValueError("rating preservation score is invalid")
    confidence = row.get("confidence_0_to_100")
    if (
        not isinstance(confidence, int)
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 100
    ):
        raise ValueError("rating confidence is invalid")
    return {"assignment_alias": alias} | {field: row.get(field) for field in RATING_FIELDS}


class HashChainedRatingLedger:
    """Append-only, source-label-free local response ledger."""

    def __init__(self, path: Path, allowed_aliases: set[str]) -> None:
        self.path = path
        self.allowed_aliases = allowed_aliases

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        previous = "0" * 64
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            event = json.loads(line)
            claimed = event.pop("event_sha256", None)
            if event.get("sequence") != number or event.get("previous_event_sha256") != previous:
                raise ValueError("rating ledger chain drift")
            actual = sha256_bytes(canonical_bytes(event))
            if claimed != actual:
                raise ValueError("rating ledger event hash drift")
            event["event_sha256"] = actual
            events.append(event)
            previous = actual
        return events

    def append(self, row: Mapping[str, Any], *, saved_at: str) -> dict[str, Any]:
        clean = validate_rating_row(row)
        if clean["assignment_alias"] not in self.allowed_aliases:
            raise ValueError("rating assignment is not in the frozen session")
        events = self.read()
        if any(event["assignment_alias"] == clean["assignment_alias"] for event in events):
            raise ValueError("rating assignment already has an append-only response")
        previous = events[-1]["event_sha256"] if events else "0" * 64
        event = clean | {
            "sequence": len(events) + 1,
            "saved_at": saved_at,
            "previous_event_sha256": previous,
        }
        event["event_sha256"] = sha256_bytes(canonical_bytes(event))
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path.parent.chmod(0o700)
        descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, canonical_bytes(event))
        finally:
            os.close(descriptor)
        self.path.chmod(0o600)
        return event

    def latest_rows(self) -> list[dict[str, Any]]:
        return [
            {
                key: value
                for key, value in event.items()
                if key == "assignment_alias" or key in RATING_FIELDS
            }
            for event in self.read()
        ]
