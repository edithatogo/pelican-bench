#!/usr/bin/env python3
"""Fail when a source is mirrored without a compatible rights decision."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/sources/source-registry.json"
THIRD_PARTY = ROOT / "data/third-party"


def main() -> int:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors: list[str] = []
    allowed = {"licensed", "public-domain", "permission-granted"}
    for source in data.get("sources", []):
        if source.get("rights_status") not in allowed and "mirror" in source.get("permitted_uses", []):
            errors.append(f"{source['source_id']}: mirror permission conflicts with rights status")
    if THIRD_PARTY.exists():
        for path in THIRD_PARTY.rglob("*"):
            if path.is_file() and path.name != "README.md":
                errors.append(f"unreviewed third-party byte artifact: {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Rights audit passed for {len(data.get('sources', []))} registered sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
