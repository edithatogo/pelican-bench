#!/usr/bin/env python3
"""Synchronise Conductor parent and phase issues with GitHub using the gh CLI.

The script is dry-run by default. It creates phase issues first, then parent
issues containing tracked checklists. Where GitHub's native sub-issue endpoint
is available, it attaches the phase issues to the parent as well.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from urllib.parse import quote
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github/issues/manifest.json"
STATE = ROOT / ".github/issue-sync-state.json"


def run_json(command: list[str]) -> Any:
    completed = subprocess.run(command, cwd=ROOT, text=True, check=True, stdout=subprocess.PIPE)
    output = completed.stdout.strip()
    return json.loads(output) if output else None


def gh_api(endpoint: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    command = ["gh", "api", endpoint, "--method", method]
    if payload is not None:
        command.extend(["--input", "-"])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            check=True,
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
        )
        return json.loads(completed.stdout) if completed.stdout.strip() else None
    return run_json(command)


def find_issue(repo: str, title: str) -> dict[str, Any] | None:
    query = quote(f'repo:{repo} is:issue in:title "{title}"')
    payload = gh_api(f"search/issues?q={query}&per_page=20")
    return next((item for item in payload.get("items", []) if item.get("title") == title), None)


def ensure_issue(repo: str, *, title: str, body: str, status: str = "planned") -> dict[str, Any]:
    desired_state = "closed" if status == "complete" else "open"
    payload = {"title": title, "body": body, "state": desired_state}
    if desired_state == "closed":
        payload["state_reason"] = "completed"
    existing = find_issue(repo, title)
    if existing is None:
        return gh_api(f"repos/{repo}/issues", method="POST", payload=payload)
    return gh_api(f"repos/{repo}/issues/{existing['number']}", method="PATCH", payload=payload)


def attach_native_sub_issue(repo: str, parent_number: int, child_id: int) -> None:
    endpoint = f"repos/{repo}/issues/{parent_number}/sub_issues"
    try:
        existing = gh_api(endpoint)
        if not any(int(item["id"]) == child_id for item in existing):
            gh_api(endpoint, method="POST", payload={"sub_issue_id": child_id})
    except subprocess.CalledProcessError:
        print(f"Native sub-issue attachment unavailable for #{parent_number}; checklist remains authoritative.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="edithatogo/pelican-bench")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tracks = manifest["tracks"]
    summary = {
        "repository": args.repo,
        "mode": "apply" if args.apply else "dry-run",
        "parent_issues": len(tracks),
        "phase_issues": sum(len(track["phases"]) for track in tracks),
        "total_issues": len(tracks) + sum(len(track["phases"]) for track in tracks),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not args.apply:
        if not args.summary_only:
            for track in tracks:
                print(track["parent_title"])
                for phase in track["phases"]:
                    print(f"  {phase['title']}")
        return 0
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI is required for --apply")
    run_json(["gh", "auth", "status", "--json", "hosts"])
    state: dict[str, Any] = {"repository": args.repo, "tracks": {}}
    for track in tracks:
        phase_records = []
        for phase in track["phases"]:
            issue = ensure_issue(args.repo, title=phase["title"], body=phase["body"], status=phase.get("status", "planned"))
            phase["issue_number"] = int(issue["number"])
            phase_records.append(issue)
        checklist = "\n".join(f"- [{'x' if phase.get('status') == 'complete' else ' '}] #{issue['number']}" for phase, issue in zip(track["phases"], phase_records, strict=True))
        parent_body = track["parent_body"] + "\n\n## Phase issues\n\n" + checklist + "\n"
        parent = ensure_issue(args.repo, title=track["parent_title"], body=parent_body, status="planned")
        track["parent_issue"] = int(parent["number"])
        for issue in phase_records:
            attach_native_sub_issue(args.repo, int(parent["number"]), int(issue["id"]))
        state["tracks"][track["code"]] = {
            "parent": int(parent["number"]),
            "phases": {phase["phase"]: int(phase["issue_number"]) for phase in track["phases"]},
        }
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    STATE.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Synchronized {summary['total_issues']} issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
