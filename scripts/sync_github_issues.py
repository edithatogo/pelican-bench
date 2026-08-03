#!/usr/bin/env python3
"""Synchronise the nested Conductor work graph with GitHub using ``gh``.

The script is dry-run by default. Under ``--apply`` it creates or updates work-package
issues, phase issues, track parents and cross-track release blockers. It then attaches
work packages beneath phases and phases beneath tracks through GitHub native sub-issues
where supported. Generated checklists remain authoritative when that endpoint is absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github/issues/manifest.json"
STATE = ROOT / ".github/issue-sync-state.json"
OWNER = "edithatogo"
BASE_LABELS: dict[str, tuple[str, str]] = {
    "conductor": ("5319e7", "Managed by the repository Conductor work graph"),
    "track": ("1d76db", "Top-level Conductor capability track"),
    "phase": ("8250df", "Conductor maturity phase"),
    "work-package": ("c5def5", "Evidence-specific nested Conductor deliverable"),
    "release-blocker": ("b60205", "Cross-track benchmark release blocker"),
    "phase:P0": ("bfdadc", "Contract phase"),
    "phase:P1": ("9be9a8", "Prototype phase"),
    "phase:P2": ("fbca04", "Validated phase"),
    "phase:P3": ("0e8a16", "Hardened phase"),
    "status:complete": ("0e8a16", "Repository exit criteria are currently evidenced"),
    "status:partial": ("fbca04", "Some phase exit criteria are evidenced"),
    "status:blocked": ("b60205", "External dependency or governance constraint blocks completion"),
    "status:planned": ("d4c5f9", "Planned work with no completion claim"),
    "status:reopened": ("d93f0b", "Previously claimed evidence has been reopened"),
    "evidence:E0": ("d4c5f9", "Defined"),
    "evidence:E1": ("c5def5", "Implemented"),
    "evidence:E2": ("fbca04", "Fixture-verified"),
    "evidence:E3": ("9be9a8", "Empirically calibrated"),
    "evidence:E4": ("bfdadc", "Independently reproduced"),
    "evidence:E5": ("0e8a16", "Operationally hardened"),
}


def run_json(command: list[str]) -> Any:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    )
    output = completed.stdout.strip()
    return json.loads(output) if output else None


def gh_api(
    endpoint: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
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


def track_label(track_id: str) -> tuple[str, str, str]:
    colour = hashlib.sha256(track_id.encode("utf-8")).hexdigest()[:6]
    return f"track:{track_id}", colour, f"Conductor track {track_id}"


def ensure_labels(repo: str, tracks: list[dict[str, Any]]) -> None:
    existing = {item["name"]: item for item in gh_api(f"repos/{repo}/labels?per_page=100")}
    desired = dict(BASE_LABELS)
    for track in tracks:
        name, colour, description = track_label(str(track["track_id"]))
        desired[name] = (colour, description)
    for name, (colour, description) in desired.items():
        payload = {"name": name, "color": colour, "description": description}
        if name in existing:
            gh_api(f"repos/{repo}/labels/{quote(name, safe='')}", method="PATCH", payload=payload)
        else:
            gh_api(f"repos/{repo}/labels", method="POST", payload=payload)


def ensure_issue(
    repo: str,
    *,
    title: str,
    body: str,
    status: str = "planned",
    labels: list[str] | None = None,
    issue_number: int | None = None,
) -> dict[str, Any]:
    desired_state = "closed" if status == "complete" else "open"
    mutable_payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "state": desired_state,
        "assignees": [OWNER],
        "labels": labels or [],
    }
    if desired_state == "closed":
        mutable_payload["state_reason"] = "completed"
    existing = (
        gh_api(f"repos/{repo}/issues/{issue_number}")
        if issue_number is not None
        else find_issue(repo, title)
    )
    if existing is None:
        issue = gh_api(
            f"repos/{repo}/issues",
            method="POST",
            payload={
                "title": title,
                "body": body,
                "assignees": [OWNER],
                "labels": labels or [],
            },
        )
        if desired_state == "closed":
            issue = gh_api(
                f"repos/{repo}/issues/{issue['number']}",
                method="PATCH",
                payload={"state": "closed", "state_reason": "completed"},
            )
        return issue
    return gh_api(
        f"repos/{repo}/issues/{existing['number']}",
        method="PATCH",
        payload=mutable_payload,
    )


def attach_native_sub_issue(repo: str, parent_number: int, child_id: int) -> None:
    endpoint = f"repos/{repo}/issues/{parent_number}/sub_issues"
    try:
        existing = gh_api(endpoint)
        if not any(int(item["id"]) == child_id for item in existing):
            gh_api(endpoint, method="POST", payload={"sub_issue_id": child_id})
    except subprocess.CalledProcessError:
        print(
            f"Native sub-issue attachment unavailable for #{parent_number}; "
            "the generated checklist remains authoritative."
        )


def parent_status(phases: list[dict[str, Any]]) -> str:
    values = {str(phase.get("status", "planned")) for phase in phases}
    if values == {"complete"}:
        return "complete"
    if "blocked" in values:
        return "blocked"
    if values & {"complete", "partial", "reopened"}:
        return "partial"
    return "planned"


def _package_count(tracks: list[dict[str, Any]]) -> int:
    return sum(
        len(phase.get("work_packages", [])) for track in tracks for phase in track.get("phases", [])
    )


def _checklist(items: list[tuple[dict[str, Any], dict[str, Any]]]) -> str:
    return (
        "\n".join(
            f"- [{'x' if record.get('status') == 'complete' else ' '}] "
            f"#{issue['number']} — `{record.get('status', 'planned')}`"
            for record, issue in items
        )
        or "- No nested work packages are defined for this phase."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="edithatogo/pelican-bench")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tracks = manifest["tracks"]
    release_blockers = manifest.get("release_blockers", [])
    package_count = _package_count(tracks)
    phase_count = sum(len(track["phases"]) for track in tracks)
    summary = {
        "repository": args.repo,
        "mode": "apply" if args.apply else "dry-run",
        "parent_issues": len(tracks),
        "phase_issues": phase_count,
        "work_package_issues": package_count,
        "release_blocker_issues": len(release_blockers),
        "total_issues": len(tracks) + phase_count + package_count + len(release_blockers),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not args.apply:
        if not args.summary_only:
            for track in tracks:
                print(track["parent_title"])
                for phase in track["phases"]:
                    print(f"  {phase['title']}")
                    for package in phase.get("work_packages", []):
                        print(f"    {package['title']}")
            for blocker in release_blockers:
                print(blocker["title"])
        return 0
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI is required for --apply")
    run_json(["gh", "auth", "status", "--json", "hosts"])
    ensure_labels(args.repo, tracks)
    state: dict[str, Any] = {"repository": args.repo, "tracks": {}, "release_blockers": {}}
    for track in tracks:
        track_id = str(track["track_id"])
        phase_records: list[dict[str, Any]] = []
        phase_state: dict[str, Any] = {}
        for phase in track["phases"]:
            package_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for package in phase.get("work_packages", []):
                package_status = str(package.get("status", "planned"))
                package_issue = ensure_issue(
                    args.repo,
                    title=package["title"],
                    body=package["body"],
                    status=package_status,
                    issue_number=package.get("issue_number"),
                    labels=[
                        "conductor",
                        "work-package",
                        f"track:{track_id}",
                        f"phase:{phase['phase']}",
                        f"status:{package_status}",
                        f"evidence:{package.get('evidence_level', 'E0')}",
                    ],
                )
                package["issue_number"] = int(package_issue["number"])
                package_pairs.append((package, package_issue))
            status = str(phase.get("status", "planned"))
            phase_body = (
                phase["body"] + "\n\n## Nested work packages\n\n" + _checklist(package_pairs) + "\n"
            )
            phase_issue = ensure_issue(
                args.repo,
                title=phase["title"],
                body=phase_body,
                status=status,
                issue_number=phase.get("issue_number"),
                labels=[
                    "conductor",
                    "phase",
                    f"track:{track_id}",
                    f"phase:{phase['phase']}",
                    f"status:{status}",
                ],
            )
            phase["issue_number"] = int(phase_issue["number"])
            for _, package_issue in package_pairs:
                attach_native_sub_issue(
                    args.repo,
                    int(phase_issue["number"]),
                    int(package_issue["id"]),
                )
            phase_records.append(phase_issue)
            phase_state[phase["phase"]] = {
                "issue": int(phase_issue["number"]),
                "work_packages": {
                    package["id"]: int(package["issue_number"]) for package, _ in package_pairs
                },
            }
        checklist = "\n".join(
            f"- [{'x' if phase.get('status') == 'complete' else ' '}] #{issue['number']}"
            for phase, issue in zip(track["phases"], phase_records, strict=True)
        )
        status_summary = "\n".join(
            f"- **{phase['phase']}:** `{phase.get('status', 'planned')}`"
            for phase in track["phases"]
        )
        parent_body = (
            track["parent_body"]
            + "\n\n## Current maturity\n\n"
            + status_summary
            + "\n\n## Phase issues\n\n"
            + checklist
            + "\n"
        )
        current_parent_status = parent_status(track["phases"])
        parent = ensure_issue(
            args.repo,
            title=track["parent_title"],
            body=parent_body,
            status="complete" if current_parent_status == "complete" else "planned",
            issue_number=track.get("parent_issue"),
            labels=[
                "conductor",
                "track",
                f"track:{track_id}",
                f"status:{current_parent_status}",
            ],
        )
        track["parent_issue"] = int(parent["number"])
        for phase_issue in phase_records:
            attach_native_sub_issue(
                args.repo,
                int(parent["number"]),
                int(phase_issue["id"]),
            )
        state["tracks"][track_id] = {
            "parent": int(parent["number"]),
            "phases": phase_state,
        }
    for blocker in release_blockers:
        status = str(blocker.get("status", "planned"))
        issue = ensure_issue(
            args.repo,
            title=blocker["title"],
            body=blocker["body"],
            status=status,
            issue_number=blocker.get("issue_number"),
            labels=[
                "conductor",
                "release-blocker",
                f"status:{status}",
                f"evidence:{blocker.get('evidence_level', 'E0')}",
                *(f"track:{track}" for track in blocker.get("linked_tracks", [])),
            ],
        )
        blocker["issue_number"] = int(issue["number"])
        state["release_blockers"][blocker["id"]] = int(issue["number"])
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    STATE.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Synchronized {summary['total_issues']} issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
