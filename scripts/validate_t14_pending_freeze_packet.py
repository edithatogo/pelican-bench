#!/usr/bin/env python3
"""Validate the incomplete T14 freeze packet without giving it freeze effect."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "benchmark/evidence/advisory/t14/pending-freeze-decision.json"
HARNESS_RECEIPT = ROOT / "benchmark/evidence/advisory/t14/exact-commit-local-harness-receipt.json"
CUSTODY_RECEIPT = ROOT / "benchmark/evidence/advisory/t14/procedural-custody-receipt.json"
CUSTODY_VERIFICATION = ROOT / "benchmark/evidence/advisory/t14/procedural-custody-verification.json"


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_sha256(value: object, message: str) -> None:
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), message)


def main() -> int:
    packet = json.loads(PACKET.read_text())
    require(
        packet["status"] == "panel-remediation-in-progress-no-freeze-effect",
        "packet status drift",
    )
    require(
        packet["normative_manifest"]["sha256"] == digest(packet["normative_manifest"]["path"]),
        "candidate commitment drift",
    )
    require(
        packet["diagnostic_manifest"]["sha256"] == digest(packet["diagnostic_manifest"]["path"]),
        "diagnostic commitment drift",
    )
    panel_paths = {
        "measurement_design_sha256": "benchmark/evidence/advisory/t14/measurement-design-final.json",
        "statistics_sha256": "benchmark/evidence/advisory/t14/statistics-final.json",
        "governance_sha256": "benchmark/evidence/advisory/t14/governance-final.json",
    }
    for key, path in panel_paths.items():
        require(packet["panel_packets"][key] == digest(path), f"panel commitment drift: {key}")
    receipt = json.loads(HARNESS_RECEIPT.read_text())
    require(receipt["receipt_kind"] == "local-execution-observation", "harness receipt kind drift")
    require(receipt["terminal_result"] == "HARNESS_OK", "harness receipt result drift")
    require(receipt["exit_status"] == 0, "harness receipt exit status drift")
    require(
        receipt["tested_repository_commit"] == "ca6882ad0e966459fda2ffa4d6b647e0a9ab551f",
        "tested commit drift",
    )
    require(
        receipt["tested_repository_tree"] == "40465cb4315a2b2e9f6c366adac276d3a2f8215f",
        "tested tree drift",
    )
    require(
        all(value is False for value in receipt["authority_effect"].values()),
        "local harness receipt overclaims authority",
    )
    require(
        packet["pending_required_inputs"]["exact_commit_full_harness_receipt_sha256"]
        == hashlib.sha256(HARNESS_RECEIPT.read_bytes()).hexdigest(),
        "harness receipt commitment drift",
    )
    require(
        packet["pending_required_inputs"]["steward_freeze_decision_receipt_sha256"] is None,
        "steward decision added without packet transition",
    )
    custody = json.loads(CUSTODY_RECEIPT.read_text())
    require(custody["schema_version"] == "1.0.0", "custody schema drift")
    require(custody["study_id"] == packet["study_id"], "custody study drift")
    require(custody["receipt_kind"] == "accountable-custody-generation", "custody kind drift")
    require(
        custody["custody_classification"] == "procedural-self-custody-not-independent",
        "custody classification drift",
    )
    require(custody["custodian_id"] == "benchmark-steward", "custodian identity drift")
    require(custody["secret_recorded"] is False, "custody receipt records secret")
    require(
        custody["candidate_manifest_sha256"] == packet["normative_manifest"]["sha256"],
        "custody candidate drift",
    )
    require(custody["episode_count"] == 96, "custody episode count drift")
    require(custody["duplicate_assignment_count"] == 10, "custody duplicate count drift")
    require(custody["assignment_count"] == 106, "custody assignment count drift")
    for key in (
        "key_commitment_sha256",
        "alias_manifest_sha256",
        "restricted_duplicate_schedule_sha256",
    ):
        require_sha256(custody[key], f"custody hash format drift: {key}")
    require(
        set(custody["authority_effect"])
        == {"freeze", "ratings", "score_promotion", "release", "publication", "unblinding"},
        "custody authority key drift",
    )
    require(
        all(value is False for value in custody["authority_effect"].values()),
        "custody receipt overclaims authority",
    )
    require(
        packet["pending_required_inputs"]["secret_bound_alias_manifest_sha256"]
        == custody["alias_manifest_sha256"],
        "alias commitment drift",
    )
    require(
        packet["pending_required_inputs"]["restricted_duplicate_schedule_sha256"]
        == custody["restricted_duplicate_schedule_sha256"],
        "duplicate schedule commitment drift",
    )
    require(
        packet["pending_required_inputs"]["accountable_custodian_receipt_sha256"]
        == hashlib.sha256(CUSTODY_RECEIPT.read_bytes()).hexdigest(),
        "custody receipt commitment drift",
    )
    verification = json.loads(CUSTODY_VERIFICATION.read_text())
    require(
        packet["procedural_custody_verification_sha256"]
        == hashlib.sha256(CUSTODY_VERIFICATION.read_bytes()).hexdigest(),
        "custody verification commitment drift",
    )
    require(verification["study_id"] == packet["study_id"], "custody verification study drift")
    require(
        verification["candidate_manifest_sha256"] == packet["normative_manifest"]["sha256"],
        "custody verification candidate drift",
    )
    for field in (
        "key_commitment_verified",
        "alias_manifest_exactly_regenerated",
        "duplicate_schedule_exactly_regenerated",
        "custody_receipt_exactly_regenerated",
        "held_out_duplicate_requirement_met",
    ):
        require(verification[field] is True, f"custody verification failed: {field}")
    require(verification["held_out_duplicate_assignment_count"] >= 3, "held-out duplicates sparse")
    require(verification["restricted_contents_disclosed"] is False, "restricted contents disclosed")
    require(verification["independence_claimed"] is False, "custody verification overclaims")
    require(
        all(
            packet[key] is False
            for key in (
                "freeze_effect",
                "ratings_authorized",
                "score_promotion",
                "release_authorized",
                "publication_authorized",
                "unblinding_authorized",
            )
        ),
        "pending packet overclaims authority",
    )
    print(
        "T14 pending freeze packet valid: procedural custody and local harness bound; steward decision absent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
