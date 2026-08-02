#!/usr/bin/env python3
"""Create the complete PelicanBench release package and QA receipt."""

from __future__ import annotations

import argparse
from pathlib import Path

from pelicanbench.release_packaging import build_release_package

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--profile", default="v0.4-alpha")
    parser.add_argument(
        "--clean-clone-receipt",
        type=Path,
        default=Path("artifacts/clean-clone-receipt.json"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    receipt = build_release_package(
        ROOT,
        args.output,
        version=args.version,
        tag=args.tag,
        profile=args.profile,
        clean_clone_receipt=args.clean_clone_receipt,
        overwrite=args.overwrite,
    )
    print(args.output)
    print(receipt.package_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
