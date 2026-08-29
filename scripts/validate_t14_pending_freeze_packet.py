#!/usr/bin/env python3
"""Validate the incomplete T14 freeze packet without giving it freeze effect."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "benchmark/evidence/advisory/t14/pending-freeze-decision.json"


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
    require(
        all(value is None for value in packet["pending_required_inputs"].values()),
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
    print("T14 pending freeze packet valid: accountable inputs and steward decision absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
