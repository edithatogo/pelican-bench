#!/usr/bin/env python3
"""Create a single-developer GitHub Projects v2 view over synchronized issues."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github/issues/manifest.json"


def run(command: list[str]) -> str:
    return subprocess.run(command, cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default="edithatogo")
    parser.add_argument("--repo", default="edithatogo/pelican-bench")
    parser.add_argument("--title", default="PelicanBench roadmap")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    issue_numbers = [
        number
        for track in manifest["tracks"]
        for number in [track.get("parent_issue"), *(phase.get("issue_number") for phase in track["phases"])]
        if number
    ]
    print(json.dumps({"title": args.title, "items_ready": len(issue_numbers), "mode": "apply" if args.apply else "dry-run"}, indent=2))
    if not args.apply:
        return 0
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI is required for --apply")
    projects = json.loads(run(["gh", "project", "list", "--owner", args.owner, "--format", "json"]))
    project = next((item for item in projects.get("projects", []) if item.get("title") == args.title), None)
    if project is None:
        project = json.loads(run(["gh", "project", "create", "--owner", args.owner, "--title", args.title, "--format", "json"]))
    for number in issue_numbers:
        url = f"https://github.com/{args.repo}/issues/{number}"
        subprocess.run(["gh", "project", "item-add", str(project["number"]), "--owner", args.owner, "--url", url], cwd=ROOT, check=False)
    print(f"Project #{project['number']} contains synchronized issue items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
