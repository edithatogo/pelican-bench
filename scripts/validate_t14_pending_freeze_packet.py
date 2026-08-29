#!/usr/bin/env python3
"""Validate the incomplete T14 freeze packet without giving it freeze effect."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "benchmark/evidence/advisory/t14/pending-freeze-decision.json"
HARNESS_RECEIPT = ROOT / "benchmark/evidence/advisory/t14/exact-commit-local-harness-receipt.json"


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    packet = json.loads(PACKET.read_text())
    require(packet["status"] == "incomplete-pending-accountable-inputs", "packet status drift")
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
        all(
            packet["pending_required_inputs"][key] is None
            for key in (
                "secret_bound_alias_manifest_sha256",
                "restricted_duplicate_schedule_sha256",
                "accountable_custodian_receipt_sha256",
                "steward_freeze_decision_receipt_sha256",
            )
        ),
        "accountable input added without packet transition",
    )
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
        "T14 pending freeze packet valid: local harness bound; accountable inputs and steward decision absent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
