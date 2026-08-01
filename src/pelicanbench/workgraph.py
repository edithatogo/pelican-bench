"""Deterministic Conductor-to-GitHub work-graph generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .timeutil import utc_now_iso

PHASE_NAMES = {
    "P0": "Contract",
    "P1": "Prototype",
    "P2": "Validated",
    "P3": "Hardened",
}


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def _track_summary(track_directory: Path) -> str:
    spec = (track_directory / "spec.md").read_text(encoding="utf-8")
    marker = "## Overview\n\n"
    if marker not in spec:
        raise ValueError(f"missing Overview section in {track_directory / 'spec.md'}")
    return spec.split(marker, 1)[1].split("\n\n", 1)[0].strip()


def _existing_numbers(manifest_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not manifest_path.exists():
        return {}, {}
    manifest = _read_object(manifest_path)
    tracks = {str(item.get("track_id")): item for item in manifest.get("tracks", [])}
    blockers = {str(item.get("id")): item for item in manifest.get("release_blockers", [])}
    return tracks, blockers


def _criterion_record(value: object, *, blocker_id: str, index: int) -> dict[str, Any]:
    if isinstance(value, str):
        return {
            "id": f"{blocker_id}-C{index}",
            "text": value,
            "status": "planned",
            "evidence": [],
        }
    if not isinstance(value, dict):
        raise TypeError(f"{blocker_id} closure criterion {index} must be text or an object")
    return {
        "id": str(value.get("id", f"{blocker_id}-C{index}")),
        "text": str(value["text"]),
        "status": str(value.get("status", "planned")),
        "evidence": list(map(str, value.get("evidence", []))),
    }


def _blocker_body(blocker: dict[str, Any]) -> str:
    criteria = [
        _criterion_record(value, blocker_id=str(blocker["id"]), index=index)
        for index, value in enumerate(blocker.get("closure_criteria", []), 1)
    ]
    checklist = "\n".join(
        f"- [{'x' if item['status'] == 'complete' else ' '}] "
        f"**{item['id']}** {item['text']} (`{item['status']}`)"
        for item in criteria
    )
    evidence_lines = "\n".join(f"- `{path}`" for path in blocker.get("evidence", []))
    criterion_evidence = []
    for item in criteria:
        for path in item["evidence"]:
            criterion_evidence.append(f"- **{item['id']}:** `{path}`")
    criterion_section = "\n".join(criterion_evidence) or "- No criterion-specific evidence yet."
    return (
        "## Cross-track release blocker\n\n"
        f"**Blocker:** {blocker['id']} — {blocker['title']}\n"
        f"**State:** `{blocker.get('status', 'planned')}`\n"
        f"**Evidence level:** `{blocker.get('evidence_level', 'E0')}`\n"
        f"**Linked tracks:** {', '.join(map(str, blocker.get('linked_tracks', [])))}\n\n"
        f"{blocker['summary']}\n\n"
        "## Closure criteria\n\n"
        f"{checklist}\n\n"
        "## Current evidence\n\n"
        f"{evidence_lines}\n\n"
        "## Criterion evidence\n\n"
        f"{criterion_section}\n\n"
        "This issue is managed from `conductor/release-blockers.json`.\n"
    )


def build_issue_manifest(
    root: str | Path,
    *,
    generated_at: str | None = None,
    preserve_numbers: bool = True,
) -> dict[str, Any]:
    """Build the complete parent/phase/blocker issue manifest from source records."""

    project = Path(root)
    manifest_path = project / ".github/issues/manifest.json"
    existing_tracks, existing_blockers = (
        _existing_numbers(manifest_path) if preserve_numbers else ({}, {})
    )
    tracks: list[dict[str, Any]] = []
    for metadata_path in sorted((project / "conductor/tracks").glob("*/metadata.json")):
        metadata = _read_object(metadata_path)
        track_id = str(metadata["track_id"])
        title = str(metadata["title"])
        slug = str(metadata["slug"])
        directory = metadata_path.parent
        relative = directory.relative_to(project).as_posix()
        previous = existing_tracks.get(track_id, {})
        previous_phases = {
            str(item.get("phase")): item for item in previous.get("phases", [])
        }
        phase_records: list[dict[str, Any]] = []
        for phase in ("P0", "P1", "P2", "P3"):
            status = str(metadata["phase_status"][phase])
            body = (
                "## Conductor phase\n\n"
                f"**Track:** {track_id} — {title}\n"
                f"**Phase:** {phase}\n"
                f"**State:** `{status}`\n"
                f"**Evidence level:** `{metadata.get('evidence_level', 'E0')}`\n"
                f"**Plan:** [`{relative}/plan.md`](../blob/main/{relative}/plan.md)\n\n"
                "### Exit criterion\n\n"
                "Complete the phase tasks with repository evidence, run `scripts/harness.sh`, "
                "update Conductor status, and record score-compatibility impact.\n"
            )
            if metadata.get("blocker") and phase in {"P2", "P3"} and status != "complete":
                body += f"\n### Constraint\n\n{metadata['blocker']}\n"
            phase_records.append(
                {
                    "phase": phase,
                    "title": f"[{track_id}/{phase}] {PHASE_NAMES[phase]}: {title}",
                    "status": status,
                    "body": body,
                    "issue_number": previous_phases.get(phase, {}).get("issue_number"),
                }
            )
        parent_body = (
            "## Conductor track\n\n"
            f"**Track:** {track_id} — {title}\n"
            f"**Specification:** [`{relative}/spec.md`](../blob/main/{relative}/spec.md)\n"
            f"**Plan:** [`{relative}/plan.md`](../blob/main/{relative}/plan.md)\n"
            f"**Evidence level:** `{metadata.get('evidence_level', 'E0')}`\n\n"
            "The parent remains open until P3 is complete. Phase issues are the executable "
            "maturity graph.\n"
        )
        tracks.append(
            {
                "track_id": track_id,
                "title": title,
                "summary": _track_summary(directory),
                "path": relative,
                "evidence_level": str(metadata.get("evidence_level", "E0")),
                "phase_status": metadata["phase_status"],
                "blocker": metadata.get("blocker"),
                "parent_title": f"[{track_id}] {title}",
                "parent_body": parent_body,
                "parent_issue": previous.get("parent_issue"),
                "phases": phase_records,
            }
        )

    blockers_value = _read_object(project / "conductor/release-blockers.json")
    blockers: list[dict[str, Any]] = []
    for blocker in blockers_value.get("blockers", []):
        blocker_id = str(blocker["id"])
        previous = existing_blockers.get(blocker_id, {})
        blockers.append(
            {
                "id": blocker_id,
                "title": f"[{blocker_id}] {blocker['title']}",
                "status": str(blocker.get("status", "planned")),
                "evidence_level": str(blocker.get("evidence_level", "E0")),
                "linked_tracks": list(map(str, blocker.get("linked_tracks", []))),
                "body": _blocker_body(blocker),
                "issue_number": previous.get("issue_number"),
            }
        )

    return {
        "schema_version": "1.2.0",
        "generated_at": generated_at or utc_now_iso(),
        "repository": "edithatogo/pelican-bench",
        "hierarchy": (
            f"{len(tracks)} parent track issues with "
            f"{sum(len(item['phases']) for item in tracks)} native phase sub-issues, "
            f"plus {len(blockers)} cross-track release blockers"
        ),
        "tracks": tracks,
        "release_blockers": blockers,
    }
