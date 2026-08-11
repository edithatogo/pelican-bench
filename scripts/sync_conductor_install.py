#!/usr/bin/env python3
"""Verify the pinned Conductor submodule and PelicanBench skill adapters."""

from __future__ import annotations

import argparse
import json
import re
import shutil

# The command path is resolved and all arguments are internal constants.
import subprocess  # nosec B404
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".agents/plugins/conductor"
DIRECT = ROOT / ".agents/skills"
LOCK = ROOT / ".conductor/vendor/UPSTREAM.lock.json"
UPSTREAM = "https://github.com/gemini-cli-extensions/conductor.git"
SKILLS = (
    "conductor-setup",
    "conductor-new-track",
    "conductor-implement",
    "conductor-status",
    "conductor-review",
    "conductor-revert",
)
GIT = shutil.which("git")


def git(*args: str) -> str:
    if GIT is None:
        raise RuntimeError("git executable is unavailable")
    # Only fixed Git subcommands are supplied by this module.
    return subprocess.check_output(  # nosec B603
        [GIT, "-C", str(PLUGIN), *args],
        text=True,
        encoding="utf-8",
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = str(lock.get("commit", ""))
    errors: list[str] = []
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        errors.append("invalid lock commit")
    if not PLUGIN.exists():
        errors.append("Conductor submodule is not initialized")
    else:
        try:
            actual = git("rev-parse", "HEAD")
            origin = git("remote", "get-url", "origin")
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            errors.append(f"cannot inspect Conductor submodule: {exc}")
        else:
            if actual != expected:
                errors.append(f"submodule HEAD is {actual}, expected {expected}")
            if origin.rstrip("/") != UPSTREAM.rstrip("/"):
                errors.append(f"unexpected submodule origin: {origin}")

    for name in SKILLS:
        upstream_skill = PLUGIN / "skills" / name / "SKILL.md"
        adapter = DIRECT / name / "SKILL.md"
        if not upstream_skill.exists():
            errors.append(f"missing upstream skill: {name}")
        if not adapter.exists():
            errors.append(f"missing PelicanBench adapter: {name}")
        elif f'upstream_commit: "{expected}"' not in adapter.read_text(encoding="utf-8"):
            errors.append(f"stale PelicanBench adapter pin: {name}")

    if errors:
        print("Conductor installation errors: " + "; ".join(errors))
        return 1
    print("Conductor submodule and PelicanBench skill adapters are synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
