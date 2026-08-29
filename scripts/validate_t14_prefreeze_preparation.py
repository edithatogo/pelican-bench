#!/usr/bin/env python3
"""Validate T14 prefreeze locks without creating a freeze or custody artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADVISORY = ROOT / "benchmark/evidence/advisory/t14"


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    blinding = json.loads((ADVISORY / "blinding-duplicate-plan.json").read_text())
    renderer = json.loads((ADVISORY / "renderer-toolchain-lock.json").read_text())
    candidate = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"
    require(blinding["status"] == "prefreeze-protocol-only", "blinding plan status drift")
    require(
        blinding["candidate_manifest_sha256"] == digest(candidate),
        "blinding candidate binding drift",
    )
    require(blinding["alias_rule"]["study_specific_secret_required"] is True, "secret gate lost")
    require(blinding["alias_rule"]["secret_must_not_be_committed"] is True, "secret policy lost")
    require(blinding["duplicate_rule"]["duplicate_assignment_count"] == 10, "duplicate count drift")
    require(
        blinding["duplicate_rule"]["interpretation"] == "repeated-measure-not-independent-episode",
        "duplicate interpretation drift",
    )
    custody = blinding["custody_gate"]
    require(custody["status"] == "pending-accountable-custodian", "custody gate drift")
    require(
        all(
            custody[field] is False
            for field in (
                "alias_manifest_present",
                "duplicate_schedule_present",
                "freeze_effect",
                "ratings_authorized",
                "unblinding_authorized",
            )
        ),
        "prefreeze plan overclaims authority",
    )
    require(renderer["status"] == "observed-local-prefreeze-lock", "renderer status drift")
    render_source = ROOT / renderer["canonical_render"]["render_source"]
    require(
        renderer["canonical_render"]["render_source_sha256"] == digest(render_source),
        "renderer source binding drift",
    )
    require(
        renderer["toolchain"]["pyproject_sha256"] == digest(ROOT / "pyproject.toml")
        and renderer["toolchain"]["uv_lock_sha256"] == digest(ROOT / "uv.lock"),
        "toolchain lock binding drift",
    )
    require(
        not any(renderer["boundaries"].values()),
        "local toolchain observation overclaims an external gate",
    )
    print("T14 prefreeze preparation valid: custody, freeze, attestation, and release pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
