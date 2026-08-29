"""Fail-closed construction of restricted T14 custody artifacts."""

from __future__ import annotations

import hashlib
import hmac
import json
from operator import itemgetter
from pathlib import Path
from typing import Any

ALIAS_DOMAIN = "pelicanbench:t14-human-calibration-v1:episode-alias:v1"
SELECTION_DOMAIN = "pelicanbench:t14-human-calibration-v1:duplicate-selection:v1"
ORDER_DOMAIN = "pelicanbench:t14-human-calibration-v1:assignment-order:v1"
STUDY_ID = "t14-human-calibration-v1"


def canonical_bytes(value: object) -> bytes:
    """Serialize an artifact deterministically for hashing and writing."""
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hmac(secret: bytes, domain: str, value: str) -> str:
    return hmac.new(secret, f"{domain}\0{value}".encode(), hashlib.sha256).hexdigest()


def build_restricted_custody_artifacts(
    candidate: dict[str, Any],
    *,
    candidate_sha256: str,
    secret: bytes,
    custodian_id: str,
    custody_classification: str,
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build the alias map, duplicate schedule, and non-secret custody receipt."""
    if len(secret) < 32:
        raise ValueError("custody secret must contain at least 32 bytes")
    identity = custodian_id.strip()
    if not identity:
        raise ValueError("custodian identity must not be empty")
    if custody_classification not in {
        "independent-custody",
        "procedural-self-custody-not-independent",
    }:
        raise ValueError("unsupported custody classification")
    episodes = candidate.get("episodes")
    if not isinstance(episodes, list) or len(episodes) != 96:
        raise ValueError("candidate must contain exactly 96 episodes")
    repair_ids = [str(episode.get("repair_id", "")).strip() for episode in episodes]
    if any(not repair_id for repair_id in repair_ids) or len(set(repair_ids)) != 96:
        raise ValueError("candidate repair identifiers must be present and unique")

    alias_entries = [
        {
            "repair_id": repair_id,
            "episode_alias": "episode-" + _hmac(secret, ALIAS_DOMAIN, repair_id)[:16],
        }
        for repair_id in sorted(repair_ids)
    ]
    aliases = {entry["repair_id"]: entry["episode_alias"] for entry in alias_entries}
    if len(set(aliases.values())) != 96:
        raise ValueError("episode alias collision")
    selected = set(
        sorted(repair_ids, key=lambda value: _hmac(secret, SELECTION_DOMAIN, value))[:10]
    )
    assignments: list[dict[str, Any]] = []
    for repair_id in repair_ids:
        occurrences = ("primary", "duplicate-1") if repair_id in selected else ("primary",)
        for occurrence in occurrences:
            assignment_key = f"{repair_id}\0{occurrence}"
            assignments.append(
                {
                    "assignment_alias": "assignment-"
                    + _hmac(secret, ORDER_DOMAIN, assignment_key)[:16],
                    "episode_alias": aliases[repair_id],
                    "repair_id": repair_id,
                    "occurrence": occurrence,
                    "is_duplicate": occurrence != "primary",
                    "order_key": _hmac(secret, ORDER_DOMAIN, "order\0" + assignment_key),
                }
            )
    assignments.sort(key=itemgetter("order_key"))
    for index, assignment in enumerate(assignments, start=1):
        assignment["ordinal"] = index
        del assignment["order_key"]
    if len(assignments) != 106 or sum(item["is_duplicate"] for item in assignments) != 10:
        raise ValueError("duplicate schedule cardinality drift")
    if len({item["assignment_alias"] for item in assignments}) != 106:
        raise ValueError("assignment alias collision")

    key_commitment = sha256_bytes(secret)
    alias_manifest = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "sensitivity": "restricted-custodian-artifact",
        "candidate_manifest_sha256": candidate_sha256,
        "algorithm": "HMAC-SHA256",
        "domain": ALIAS_DOMAIN,
        "key_commitment_sha256": key_commitment,
        "entries": alias_entries,
    }
    duplicate_schedule = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "sensitivity": "restricted-custodian-artifact",
        "candidate_manifest_sha256": candidate_sha256,
        "selection_domain": SELECTION_DOMAIN,
        "assignment_order_domain": ORDER_DOMAIN,
        "source_episode_count": 96,
        "duplicate_assignment_count": 10,
        "assignment_count": 106,
        "assignments": assignments,
    }
    alias_bytes = canonical_bytes(alias_manifest)
    schedule_bytes = canonical_bytes(duplicate_schedule)
    receipt = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "receipt_kind": "accountable-custody-generation",
        "custodian_id": identity,
        "custody_classification": custody_classification,
        "created_at": created_at,
        "candidate_manifest_sha256": candidate_sha256,
        "key_commitment_sha256": key_commitment,
        "secret_recorded": False,
        "alias_manifest_sha256": sha256_bytes(alias_bytes),
        "restricted_duplicate_schedule_sha256": sha256_bytes(schedule_bytes),
        "episode_count": 96,
        "duplicate_assignment_count": 10,
        "assignment_count": 106,
        "authority_effect": {
            "freeze": False,
            "ratings": False,
            "score_promotion": False,
            "release": False,
            "publication": False,
            "unblinding": False,
        },
    }
    return alias_manifest, duplicate_schedule, receipt


def write_new_private_file(path: Path, value: object) -> None:
    """Create a restricted artifact without overwriting an existing path."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
    path.chmod(0o600)
