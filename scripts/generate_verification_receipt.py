#!/usr/bin/env python3
"""Generate an edithatogo/repository-standards compatible verification receipt."""

from __future__ import annotations

import argparse
from pathlib import Path

from pelicanbench.io import write_json
from pelicanbench.verification import (
    build_repository_verification_receipt,
    validate_repository_verification_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "benchmark/schemas/repository-verification-receipt.schema.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", default="v0.4-alpha")
    parser.add_argument("--coverage", type=Path, default=Path("coverage.xml"))
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--revision")
    args = parser.parse_args()
    receipt = build_repository_verification_receipt(
        ROOT,
        profile=args.profile,
        revision=args.revision,
        coverage_path=args.coverage,
        artifact_paths=tuple(args.artifact),
    )
    validate_repository_verification_receipt(receipt, SCHEMA)
    write_json(args.output, receipt.model_dump(mode="json", exclude_none=True))
    print(args.output)
    return 0 if receipt.result != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
