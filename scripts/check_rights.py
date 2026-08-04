#!/usr/bin/env python3
"""Fail when a source is mirrored without a compatible rights decision."""

from __future__ import annotations

import json
from pathlib import Path

from pelicanbench.source_rights import audit_sourced_artifacts

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/sources/source-registry.json"
THIRD_PARTY = ROOT / "data/third-party"


def main() -> int:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors: list[str] = []
    registry_ids = {
        source.get("source_id")
        for source in data.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }
    ledger_path = ROOT / "data/sources/rights-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_ids = {
        decision.get("source_id")
        for decision in ledger.get("decisions", [])
        if isinstance(decision, dict) and isinstance(decision.get("source_id"), str)
    }
    for source_id in sorted(registry_ids - ledger_ids):
        errors.append(f"registry source lacks an explicit rights-ledger decision: {source_id}")
    allowed = {"licensed", "public-domain", "permission-granted"}
    for source in data.get("sources", []):
        if source.get("rights_status") not in allowed and "mirror" in source.get(
            "permitted_uses", []
        ):
            errors.append(f"{source['source_id']}: mirror permission conflicts with rights status")
    if THIRD_PARTY.exists():
        for path in THIRD_PARTY.rglob("*"):
            if path.is_file() and path.name != "README.md":
                errors.append(f"unreviewed third-party byte artifact: {path.relative_to(ROOT)}")
    coverage = audit_sourced_artifacts(ROOT)
    for finding in coverage.findings:
        errors.append(f"{finding.code}: {finding.message}")
    if errors:
        print("\n".join(errors))
        return 1
    print(
        "Rights audit passed for "
        f"{len(data.get('sources', []))} registered sources and "
        f"{coverage.artifact_count} sourced records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
