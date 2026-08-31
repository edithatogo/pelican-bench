#!/usr/bin/env python3
"""Bind an inactive three-file preview locally, without deployment authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hf/t14-workflow-preview-v2"
OUTPUT = ROOT / "benchmark/preparation/t14-workflow-preview-v2-manifest.json"
ALLOWLIST = ("README.md", "index.html", "style.css")


def reject_symlinks(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("symlink path rejected")


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def build(package: Path = PACKAGE) -> dict[str, Any]:
    reject_symlinks(package)
    if not package.is_dir() or {item.name for item in package.iterdir()} != set(ALLOWLIST):
        raise ValueError("preview requires exact three-file allowlist")
    files = []
    for name in ALLOWLIST:
        path = package / name
        reject_symlinks(path)
        if not path.is_file():
            raise ValueError("preview member is not a regular file")
        data = path.read_bytes()
        files.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "schema_version": "t14-inactive-workflow-preview-v2-manifest-v1",
        "status": "local exact-package preparation; approval pending",
        "package_version": "t14-workflow-preview-v2",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "destination": None,
        "files": files,
        "allowlist": list(ALLOWLIST),
        "total_bytes": sum(item["bytes"] for item in files),
        "rights_basis": "project-original workflow text and non-study toy drawings",
        "content_scope": "inactive instructions and non-study assets; no answers or study assignments",
        "authority_effect": dict.fromkeys(
            (
                "deployment",
                "publication",
                "human_study_selection",
                "collection",
                "consent",
                "freeze",
                "response_analysis",
                "unblinding",
                "promotion",
                "attestation",
                "release",
            ),
            False,
        ),
        "limits": [
            "Hashes identify reviewed bytes; they do not confer approval or establish safety.",
            "The package remains inactive; no hosted destination or publication function exists.",
            "Manifest stays outside the public package and is not itself on the upload allowlist.",
            "No human usability, native zoom, screen-reader or hosted-delivery claim follows.",
        ],
    }


def validate(value: dict[str, Any], package: Path = PACKAGE) -> None:
    if encode(value) != encode(build(package)):
        raise ValueError("preview manifest does not match exact package recipe")


def check(output: Path = OUTPUT, package: Path = PACKAGE) -> None:
    reject_symlinks(output)
    data = output.read_bytes()
    validate(json.loads(data), package)
    if data != encode(build(package)):
        raise ValueError("noncanonical preview manifest encoding")


def write(output: Path = OUTPUT, package: Path = PACKAGE) -> None:
    reject_symlinks(output)
    reject_symlinks(package)
    if output.resolve().is_relative_to(package.resolve()):
        raise ValueError("manifest must remain outside public package")
    data = encode(build(package))
    with output.open("xb") as handle:
        handle.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check(args.output)
    else:
        write(args.output)


if __name__ == "__main__":
    main()
