#!/usr/bin/env python3
"""Generate a machine-readable PelicanBench release manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pelicanbench.release_manifest import build_release_manifest

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", default="v0.2-alpha")
    parser.add_argument("--tag")
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()
    manifest = build_release_manifest(
        ROOT,
        profile=args.profile,
        tag=args.tag,
        artifacts=args.artifact,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if manifest["release"]["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
