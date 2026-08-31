#!/usr/bin/env python3
"""Prepare an exact inactive preview ZIP locally; no upload or authority effect."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hf/t14-workflow-preview-v2"
MANIFEST = ROOT / "benchmark/preparation/t14-workflow-preview-v2-manifest.json"
MANIFEST_SHA256 = "7065026ada29ec3533a1d4e78db521fc5496fc6a18b59bf81418bad80df8e4d3"
ALLOWLIST = ("README.md", "index.html", "style.css")


def reject_symlinks(path: Path) -> None:
    if ".." in path.parts:
        raise ValueError("parent traversal rejected")
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("symlink path rejected")


def read_bounded(path: Path, limit: int) -> bytes:
    """Read one regular-file snapshot, never a FIFO, device or followed symlink."""
    reject_symlinks(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
        os.close(descriptor)
        raise ValueError("nonregular or oversized preview input")
    with os.fdopen(descriptor, "rb") as handle:
        value = handle.read(limit + 1)
    if len(value) > limit:
        raise ValueError("oversized preview input")
    return value


def build(package: Path = PACKAGE, manifest: Path = MANIFEST) -> bytes:
    """Validate and archive the same bytes; never reread a validated member."""
    raw = read_bounded(manifest, 16_384)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("reviewed manifest hash mismatch")
    value = json.loads(raw)
    canonical = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if canonical != raw:
        raise ValueError("noncanonical reviewed manifest")
    generator = ROOT / "scripts/build_t14_workflow_preview_manifest.py"
    if hashlib.sha256(read_bounded(generator, 16_384)).hexdigest() != value["generator_sha256"]:
        raise ValueError("reviewed manifest generator mismatch")
    reject_symlinks(package)
    names: list[str] = []
    with os.scandir(package) as entries:
        for entry in entries:
            names.append(entry.name)
            if len(names) > len(ALLOWLIST):
                raise ValueError("preview requires exact three-file allowlist")
    if set(names) != set(ALLOWLIST):
        raise ValueError("preview requires exact three-file allowlist")
    snapshots: list[tuple[str, bytes]] = []
    for row in value["files"]:
        data = read_bounded(package / row["path"], row["bytes"])
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("preview member differs from reviewed bytes")
        snapshots.append((row["path"], data))
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in snapshots:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    return result.getvalue()


def write(output: Path, package: Path = PACKAGE, manifest: Path = MANIFEST) -> None:
    """Install a complete local file atomically without overwriting an existing path."""
    reject_symlinks(output)
    reject_symlinks(package)
    if output.resolve().is_relative_to(package.resolve()):
        raise ValueError("archive must remain outside public package")
    if output.exists():
        raise FileExistsError(output)
    data = build(package, manifest)
    descriptor, staging_name = tempfile.mkstemp(prefix=".t14-preview-", dir=output.parent)
    staging = Path(staging_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        reject_symlinks(output)
        os.link(staging, output, follow_symlinks=False)
    finally:
        staging.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write(args.output)


if __name__ == "__main__":
    main()
