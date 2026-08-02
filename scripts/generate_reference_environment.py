#!/usr/bin/env python3
"""Generate a deterministic snapshot of the installed PelicanBench dependency closure.

This is an evidence artifact, not a substitute for a registry-resolved ``uv.lock``. It is
useful in restricted environments where the configured package mirror does not expose all
required distributions.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import tomllib
from collections import deque
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "constraints/reference-environment.txt"


def project_roots() -> set[str]:
    value = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = value["project"]
    raw = list(project.get("dependencies", []))
    for items in project.get("optional-dependencies", {}).values():
        raw.extend(items)
    return {canonicalize_name(Requirement(item).name) for item in raw}


def dependency_closure(roots: set[str]) -> tuple[dict[str, str], set[str]]:
    installed: dict[str, str] = {}
    missing: set[str] = set()
    queue: deque[str] = deque(sorted(roots))
    while queue:
        name = canonicalize_name(queue.popleft())
        if name in installed or name in missing:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.add(name)
            continue
        installed[name] = distribution.version
        for raw_requirement in distribution.requires or ():
            requirement = Requirement(raw_requirement)
            if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                continue
            queue.append(canonicalize_name(requirement.name))
    return installed, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    installed, missing = dependency_closure(project_roots())
    lines = [
        "# PelicanBench reference environment snapshot",
        "# Generated from the installed dependency closure; not a universal resolver lock.",
        "# Regenerate with: python scripts/generate_reference_environment.py",
    ]
    lines.extend(f"{name}=={installed[name]}" for name in sorted(installed))
    if missing:
        lines.append("# Missing from the current environment: " + ", ".join(sorted(missing)))
    text = "\n".join(lines) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {len(installed)} pinned distributions to {args.output}")
    if missing:
        print("Missing: " + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
