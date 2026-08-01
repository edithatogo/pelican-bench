#!/usr/bin/env python3
"""Build a rights-aware PelicanBench publication hand-off bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from pelicanbench.publication import build_publication_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    manifest = build_publication_bundle(
        ROOT,
        args.output,
        include_artifacts=tuple(args.artifact),
        overwrite=args.overwrite,
    )
    print(f"{args.output}: {len(manifest.files)} files, {manifest.bundle_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
