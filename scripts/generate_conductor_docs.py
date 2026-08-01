#!/usr/bin/env python3
"""Generate or verify deterministic Conductor registry and status views."""

from __future__ import annotations

import argparse
from pathlib import Path

from pelicanbench.conductor_docs import generated_documents

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    documents = generated_documents(ROOT)
    stale: list[str] = []
    for path, expected in documents.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            if actual != expected:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.write_text(expected, encoding="utf-8")
            print(path)
    if stale:
        print("Conductor views are stale: " + ", ".join(stale))
        return 1
    if args.check:
        print("Conductor registry and status views are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
