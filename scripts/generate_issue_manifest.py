#!/usr/bin/env python3
"""Generate or verify the GitHub issue manifest from Conductor source records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pelicanbench.io import write_json
from pelicanbench.workgraph import build_issue_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".github/issues/manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    existing = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else None
    generated_at = existing.get("generated_at") if isinstance(existing, dict) else None
    expected = build_issue_manifest(
        ROOT,
        generated_at=generated_at,
        preserve_numbers=args.output == DEFAULT_OUTPUT,
    )
    if args.check:
        if existing != expected:
            print("GitHub issue manifest is stale; run scripts/generate_issue_manifest.py")
            return 1
        print(
            f"Verified {len(expected['tracks'])} tracks, "
            f"{sum(len(item['phases']) for item in expected['tracks'])} phases and "
            f"{len(expected['release_blockers'])} release blockers."
        )
        return 0
    write_json(args.output, expected)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
