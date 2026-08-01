"""Deterministic human-readable views of the Conductor source records."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

PHASES = ("P0", "P1", "P2", "P3")
PHASE_NAMES = {
    "P0": "Contract",
    "P1": "Prototype",
    "P2": "Validated",
    "P3": "Hardened",
}


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _tracks(project: Path) -> list[dict[str, Any]]:
    records = [
        _read_object(path)
        for path in sorted((project / "conductor/tracks").glob("*/metadata.json"))
    ]
    return sorted(records, key=lambda item: str(item["track_id"]))


def _blockers(project: Path) -> list[dict[str, Any]]:
    return list(_read_object(project / "conductor/release-blockers.json").get("blockers", []))


def _summary(track_directory: Path) -> str:
    text = (track_directory / "spec.md").read_text(encoding="utf-8")
    marker = "## Overview\n\n"
    if marker not in text:
        raise ValueError(f"missing Overview section in {track_directory / 'spec.md'}")
    return text.split(marker, 1)[1].split("\n\n", 1)[0].strip()


def render_track_registry(project: str | Path) -> str:
    root = Path(project)
    tracks = _tracks(root)
    blockers = _blockers(root)
    phase_count = len(tracks) * len(PHASES)
    lines = [
        "# Track registry",
        "",
        (
            f"PelicanBench has {len(tracks)} capability tracks, {phase_count} maturity "
            f"phases and {len(blockers)} cross-track release blockers. Status is "
            "evidence-based; a parent track remains open until P3 is complete."
        ),
        "",
    ]
    for item in tracks:
        slug = str(item["slug"])
        track_id = str(item["track_id"])
        title = str(item["title"])
        summary = _summary(root / "conductor/tracks" / slug)
        phases = ", ".join(
            f"{phase} {item['phase_status'][phase]}" for phase in PHASES
        )
        lines.append(
            f"- [ ] **{track_id}: {title}** — [{summary}](tracks/{slug}/index.md) "
            f"`{item.get('evidence_level', 'E0')}`; {phases}."
        )
    lines.extend(
        [
            "",
            "## Cross-track release blockers",
            "",
            "| Blocker | State | Evidence | Linked tracks |",
            "|---|---|---:|---|",
        ]
    )
    for blocker in blockers:
        lines.append(
            f"| {blocker['id']}: {blocker['title']} | {blocker.get('status', 'planned')} "
            f"| {blocker.get('evidence_level', 'E0')} | "
            f"{', '.join(map(str, blocker.get('linked_tracks', [])))} |"
        )
    lines.extend(
        [
            "",
            "The blocker definitions and closure evidence are authoritative in "
            "[`release-blockers.json`](release-blockers.json).",
            "",
        ]
    )
    return "\n".join(lines)


def render_status(project: str | Path) -> str:
    root = Path(project)
    tracks = _tracks(root)
    blockers = _blockers(root)
    phase_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    for item in tracks:
        phase_counts.update(map(str, item.get("phase_status", {}).values()))
        evidence_counts[str(item.get("evidence_level", "E0"))] += 1

    lines = [
        "# Conductor status",
        "",
        (
            "Status is generated from track metadata. `complete` means that the declared "
            "phase exit criteria are met at the stated evidence level; it does not convert "
            "fixture evidence into empirical, human or production validation."
        ),
        "",
        "| Track | Capability | P0 | P1 | P2 | P3 | Evidence | Current constraint |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in tracks:
        phase_status = item["phase_status"]
        constraint = str(item.get("blocker") or "No declared cross-phase constraint.")
        lines.append(
            f"| {item['track_id']} | {item['title']} | "
            f"{phase_status['P0']} | {phase_status['P1']} | {phase_status['P2']} | "
            f"{phase_status['P3']} | {item.get('evidence_level', 'E0')} | {constraint} |"
        )

    lines.extend(
        [
            "",
            "## Programme totals",
            "",
            f"- Tracks: {len(tracks)}.",
            f"- Phases: {len(tracks) * len(PHASES)}.",
            "- Phase states: "
            + ", ".join(f"{key} {phase_counts[key]}" for key in sorted(phase_counts))
            + ".",
            "- Track evidence: "
            + ", ".join(f"{key} {evidence_counts[key]}" for key in sorted(evidence_counts))
            + ".",
            "- Planned GitHub work items: "
            f"{len(tracks)} parent tracks + {len(tracks) * len(PHASES)} phase issues + "
            f"{len(blockers)} release blockers = "
            f"{len(tracks) * (len(PHASES) + 1) + len(blockers)}.",
            "",
            "## Release blockers",
            "",
            "| Blocker | State | Evidence | Open criteria |",
            "|---|---|---:|---:|",
        ]
    )
    for blocker in blockers:
        criteria = blocker.get("closure_criteria", [])
        open_count = sum(
            1
            for criterion in criteria
            if isinstance(criterion, dict) and criterion.get("status") != "complete"
        )
        lines.append(
            f"| {blocker['id']}: {blocker['title']} | {blocker.get('status', 'planned')} "
            f"| {blocker.get('evidence_level', 'E0')} | {open_count} |"
        )

    lines.extend(
        [
            "",
            "## Verification contract",
            "",
            "The local evidence gate is `scripts/harness.sh` (run with Bash). It verifies tests and "
            "coverage, schemas, issue-manifest freshness, rights controls, ontology "
            "competency cases, release assurance, pilot commitments, scorer metamorphism, "
            "the renderer bridge when available, deterministic replay and the SBOM.",
            "",
            "Remote CI, attestations, GitHub publication, Hugging Face publication, human "
            "calibration and prospective model runs are not inferred from local files. They "
            "remain open until their release-blocker criteria contain the resulting evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def generated_documents(project: str | Path) -> dict[Path, str]:
    root = Path(project)
    return {
        root / "conductor/tracks.md": render_track_registry(root),
        root / "conductor/status.md": render_status(root),
    }
