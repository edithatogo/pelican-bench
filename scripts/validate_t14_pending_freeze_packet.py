#!/usr/bin/env python3
"""Validate the T14 exact-hash decision packet and its bounded authority effect."""

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
FREEZE_RECEIPT = ROOT / "benchmark/evidence/advisory/t14/procedural-freeze-decision-receipt.json"


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
        packet["status"] == "frozen-procedural-non-independent-e2",
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
    procedural_panel_paths = {
        "measurement_design_sha256": "benchmark/evidence/advisory/t14/procedural-panel-design.json",
        "statistics_sha256": "benchmark/evidence/advisory/t14/procedural-panel-statistics.json",
        "governance_sha256": "benchmark/evidence/advisory/t14/procedural-panel-governance.json",
    }
    for key, path in procedural_panel_paths.items():
        require(
            packet["procedural_panel_packets"][key] == digest(path),
            f"procedural panel commitment drift: {key}",
        )
        panel = json.loads((ROOT / path).read_text())
        require(
            panel["reviewed_commit"] == packet["reviewed_repository_commit"], "panel commit drift"
        )
        require(panel["reviewed_tree"] == packet["reviewed_repository_tree"], "panel tree drift")
        classification = panel["classification"]
        require(classification["synthetic"] is True, "panel synthetic label drift")
        require(classification["human"] is False, "panel human overclaim")
        require(classification["independent"] is False, "panel independence overclaim")
        require(classification["normative"] is False, "panel normative overclaim")
        require(classification["gate_effect"] == "none", "panel gate-effect overclaim")
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
    freeze = json.loads(FREEZE_RECEIPT.read_text())
    require(freeze["receipt_kind"] == "exact-hash-steward-freeze-decision", "freeze kind drift")
    require(freeze["study_id"] == packet["study_id"], "freeze study drift")
    require(freeze["decision"] == "freeze-exact-bytes", "freeze decision drift")
    require(freeze["decision_maker"] == "benchmark-steward", "freeze decision maker drift")
    require(freeze["decision_at"] == packet["decision_at"], "freeze decision time drift")
    require(
        packet["pending_required_inputs"]["steward_freeze_decision_receipt_sha256"]
        == hashlib.sha256(FREEZE_RECEIPT.read_bytes()).hexdigest(),
        "freeze receipt commitment drift",
    )
    require(
        packet["pending_required_inputs"]["exact_commit_full_harness_receipt_sha256"]
        == freeze["tested_repository"]["exact_current_harness_receipt_sha256"],
        "exact-current harness commitment drift",
    )
    require_sha256(
        freeze["tested_repository"]["exact_current_harness_receipt_sha256"],
        "exact-current harness hash format drift",
    )
    require(
        packet["pending_required_inputs"]["exact_commit_full_harness_receipt_location"]
        == "restricted-local-external-to-git",
        "exact-current harness location drift",
    )
    require(
        freeze["tested_repository"]["commit"] == "a07e52bde7ee103afa999fa9c7ecc19cc4479571",
        "freeze tested commit drift",
    )
    require(
        freeze["tested_repository"]["tree"] == "da4aca7752b98f3cdf3f81862c26691ed86ec2f3",
        "freeze tested tree drift",
    )
    require(freeze["tested_repository"]["harness_result"] == "HARNESS_OK", "harness failed")
    require(freeze["classification"]["evidence_level"] == "E2", "freeze evidence overclaim")
    require(freeze["classification"]["independent"] is False, "freeze independence overclaim")
    require(
        freeze["classification"]["human_ratings_present"] is False,
        "freeze human-rating overclaim",
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
    require(verification["schema_version"] == "1.0.0", "custody verification schema drift")
    require(
        verification["verification_kind"] == "local-procedural-custody-cryptographic-verification",
        "custody verification kind drift",
    )
    require(
        verification["candidate_manifest_sha256"] == packet["normative_manifest"]["sha256"],
        "custody verification candidate drift",
    )
    require(
        verification["alias_manifest_sha256"] == custody["alias_manifest_sha256"],
        "custody verification alias drift",
    )
    require(
        verification["restricted_duplicate_schedule_sha256"]
        == custody["restricted_duplicate_schedule_sha256"],
        "custody verification schedule drift",
    )
    require(
        verification["custody_receipt_sha256"]
        == hashlib.sha256(CUSTODY_RECEIPT.read_bytes()).hexdigest(),
        "custody verification receipt drift",
    )
    require(verification["episode_alias_count"] == 96, "custody verification episode count drift")
    require(
        verification["duplicate_assignment_count"] == 10, "custody verification duplicate drift"
    )
    require(verification["assignment_count"] == 106, "custody verification assignment drift")
    require(
        set(verification["authority_effect"])
        == {"freeze", "ratings", "score_promotion", "release", "publication", "unblinding"},
        "custody verification authority key drift",
    )
    require(
        all(value is False for value in verification["authority_effect"].values()),
        "custody verification overclaims authority",
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
    frozen = freeze["frozen_commitments"]
    require(
        frozen["candidate_manifest_sha256"] == packet["normative_manifest"]["sha256"],
        "freeze candidate drift",
    )
    require(
        frozen["diagnostic_manifest_sha256"] == packet["diagnostic_manifest"]["sha256"],
        "freeze diagnostic drift",
    )
    require(frozen["protocol_sha256"] == packet["protocol_sha256"], "freeze protocol drift")
    require(
        frozen["analysis_plan_sha256"] == packet["analysis_plan_sha256"], "freeze analysis drift"
    )
    require(
        frozen["blinding_duplicate_rule_sha256"] == packet["blinding_duplicate_rule_sha256"],
        "freeze blinding drift",
    )
    require(
        frozen["procedural_custody_receipt_sha256"]
        == packet["pending_required_inputs"]["accountable_custodian_receipt_sha256"],
        "freeze custody drift",
    )
    require(
        frozen["renderer_toolchain_lock_sha256"] == packet["renderer_toolchain_lock_sha256"],
        "freeze renderer drift",
    )
    require(
        frozen["procedural_custody_verification_sha256"]
        == packet["procedural_custody_verification_sha256"],
        "freeze custody verification drift",
    )
    require(
        frozen["procedural_panel_design_sha256"]
        == packet["procedural_panel_packets"]["measurement_design_sha256"],
        "freeze design panel drift",
    )
    require(
        frozen["procedural_panel_statistics_sha256"]
        == packet["procedural_panel_packets"]["statistics_sha256"],
        "freeze statistics panel drift",
    )
    require(
        frozen["procedural_panel_governance_sha256"]
        == packet["procedural_panel_packets"]["governance_sha256"],
        "freeze governance panel drift",
    )
    require(packet["decision"] == "freeze-exact-bytes", "packet freeze decision drift")
    require(packet["normative_manifest"]["frozen"] is True, "normative manifest not frozen")
    require(packet["freeze_effect"] is True, "freeze effect absent")
    require(
        all(
            packet[key] is False
            for key in (
                "ratings_authorized",
                "score_promotion",
                "release_authorized",
                "publication_authorized",
                "unblinding_authorized",
            )
        ),
        "freeze packet overclaims downstream authority",
    )
    require(freeze["authority_effect"]["freeze"] is True, "freeze receipt effect absent")
    require(
        set(freeze["authority_effect"])
        == {
            "freeze",
            "ratings",
            "score_promotion",
            "attestation",
            "release",
            "publication",
            "unblinding",
        },
        "freeze authority key drift",
    )
    require(
        all(value is False for key, value in freeze["authority_effect"].items() if key != "freeze"),
        "freeze receipt overclaims downstream authority",
    )
    print(
        "T14 exact-hash packet frozen as procedural non-independent E2 preparation; "
        "ratings and downstream gates remain unauthorized"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
