#!/usr/bin/env python3
"""Generate or verify canonical JSON Schema snapshots for public records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pelicanbench.io import write_json
from pelicanbench.validation import SCHEMA_MODELS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = ROOT / "benchmark/schemas"


def expected_schemas() -> dict[str, dict[str, object]]:
    return {name: model.model_json_schema() for name, model in SCHEMA_MODELS.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail rather than rewrite when a committed schema is stale.",
    )
    parser.add_argument("--output-directory", type=Path, default=SCHEMA_DIRECTORY)
    args = parser.parse_args()

    stale: list[str] = []
    for filename, schema in expected_schemas().items():
        target = args.output_directory / filename
        if args.check:
            if not target.exists() or json.loads(target.read_text(encoding="utf-8")) != schema:
                stale.append(filename)
        else:
            write_json(target, schema)
    if stale:
        print("Stale schemas: " + ", ".join(stale))
        return 1
    if args.check:
        print(f"Verified {len(SCHEMA_MODELS)} schema snapshots.")
    else:
        print(f"Generated {len(SCHEMA_MODELS)} schema snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
