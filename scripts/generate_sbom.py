#!/usr/bin/env python3
"""Generate a deterministic minimal SPDX 2.3 SBOM for repository code."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pelicanbench.io import file_hash
from pelicanbench.timeutil import utc_now_iso

ROOT = Path(__file__).resolve().parents[1]
INCLUDED_SUFFIXES = {".py", ".rs", ".mojo", ".json", ".jsonl", ".md", ".toml", ".yml", ".yaml", ".sh", ".tex"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = []
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or ".git" in path.parts
            or "artifacts" in path.parts
            or "runs" in path.parts
            or path.suffix not in INCLUDED_SUFFIXES
        ):
            continue
        relative = path.relative_to(ROOT).as_posix()
        files.append(
            {
                "SPDXID": "SPDXRef-File-" + relative.replace("/", "-").replace(".", "-"),
                "fileName": relative,
                "checksums": [{"algorithm": "SHA256", "checksumValue": file_hash(path).split(":", 1)[1]}],
                "licenseConcluded": "NOASSERTION",
            }
        )
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "pelican-bench-source",
        "documentNamespace": "https://github.com/edithatogo/pelican-bench/sbom/" + os.getenv("GITHUB_SHA", "working-tree"),
        "creationInfo": {"created": utc_now_iso(), "creators": ["Tool: pelicanbench-generate-sbom/0.1.0"]},
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
