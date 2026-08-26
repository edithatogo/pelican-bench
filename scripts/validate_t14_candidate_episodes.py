#!/usr/bin/env python3
"""Fail-closed validation for the non-normative T14 candidate package."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"
CANDIDATE_ROOT = MANIFEST.parent.resolve()
sys.path.insert(0, str(ROOT / "src"))

from pelicanbench.render import render_svg  # ruff: ignore[module-import-not-at-top-of-file]
from pelicanbench.svg import inspect_svg  # ruff: ignore[module-import-not-at-top-of-file]


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve_candidate_asset(relative: Path) -> Path:
    require(
        relative.parts[:4] == ("benchmark", "fixtures", "repair", "candidate"),
        f"asset path escapes candidate prefix: {relative}",
    )
    source_path = ROOT / relative
    path = source_path.resolve()
    require(
        CANDIDATE_ROOT in path.parents,
        f"asset resolves outside candidate root: {relative}",
    )
    require(
        path.is_file() and not source_path.is_symlink(),
        f"unsafe asset path: {relative}",
    )
    return path


@cache
def inspect_and_render(svg: str) -> tuple[frozenset[str], str, bool, tuple[str, ...]]:
    inspection = inspect_svg(svg)
    if not inspection.valid:
        return frozenset(), "", False, inspection.errors
    rendered = render_svg(svg, size=512, inspection=inspection)
    roles = frozenset(inspection.features["declared_role_counts"])
    return roles, rendered.render_hash, rendered.nonblank, ()


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(payload.get("status") == "candidate-development-only", "candidate status drift")
    require(payload.get("normative_sample_frozen") is False, "normative freeze is prohibited")
    require(payload.get("human_ratings_present") is False, "candidate package contains ratings")
    require(payload.get("agent_outputs_are_ratings") is False, "agent advice cannot be ratings")
    require(
        payload.get("score_promotion") == "prohibited-pending-steward-decision",
        "score-promotion boundary drift",
    )
    require(payload.get("publication_status") == "not-published", "publication boundary drift")
    provenance = payload.get("provenance", {})
    require(
        provenance.get("origin") == "project-original-deterministic-svg-generator",
        "project-original provenance missing",
    )
    require(provenance.get("external_source_material") is False, "external source material found")
    generator = ROOT / str(provenance.get("generator", ""))
    require(generator.is_file(), "generator path missing")
    require(
        hashlib.sha256(generator.read_bytes()).hexdigest()
        == provenance.get("generator_source_sha256"),
        "generator source commitment mismatch",
    )
    require(payload.get("split_policy", {}).get("status") == "proposed-not-frozen", "split frozen")
    episodes = payload.get("episodes", [])
    require(len(episodes) == payload.get("episode_count") == 96, "episode count must be 96")
    require(len({row.get("repair_id") for row in episodes}) == 96, "duplicate repair ID")
    require(len({row.get("task_id") for row in episodes}) == 96, "duplicate task ID")
    require(len({row.get("sampling_cell_id") for row in episodes}) == 96, "duplicate sampling cell")
    partitions = Counter(row.get("proposed_partition") for row in episodes)
    require(
        partitions == {"proposed-development": 72, "proposed-held-out": 24},
        "proposed split must be 72/24",
    )
    families = Counter(row.get("defect_family") for row in episodes)
    require(len(families) == payload.get("defect_family_count") == 8, "need 8 defect families")
    require(set(families.values()) == {12}, "every defect family must occur in 12 groups")
    require(
        set(Counter(row.get("severity") for row in episodes)) == {"moderate", "severe"},
        "severity strata drift",
    )
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in episodes:
        require(row.get("status") == "candidate-development-only", "episode status drift")
        intended = row.get("intended_edit", {})
        require(intended.get("defect_family") == row.get("defect_family"), "intended edit mismatch")
        require(intended.get("operation") == row.get("operation"), "operation mismatch")
        require(bool(intended.get("preserve")), "preservation annotation missing")
        require(
            intended.get("introduced_defect_expectation") == "none",
            "introduced-defect expectation missing",
        )
        groups[str(row.get("scene_group_id"))].append(row)
        observed_roles: dict[str, set[str]] = {}
        for path_key, byte_hash_key, render_hash_key in (
            ("before", "before_sha256", "before_render_sha256"),
            ("after_reference", "after_sha256", "after_render_sha256"),
        ):
            relative = Path(str(row.get(path_key, "")))
            require(
                relative.parts[:4] == ("benchmark", "fixtures", "repair", "candidate"),
                f"{path_key} escapes candidate root",
            )
            path = resolve_candidate_asset(relative)
            raw = path.read_bytes()
            require(
                hashlib.sha256(raw).hexdigest() == row.get(byte_hash_key),
                f"byte commitment mismatch: {relative}",
            )
            svg = raw.decode("utf-8")
            roles, render_hash, nonblank, errors = inspect_and_render(svg)
            require(not errors, f"unsafe SVG {relative}: {errors}")
            observed_roles[path_key] = set(roles)
            require(nonblank, f"blank canonical render: {relative}")
            require(
                render_hash == row.get(render_hash_key),
                f"render commitment mismatch: {relative}",
            )
        predicates = row.get("expected_predicates", {})
        require(
            observed_roles["before"] == set(predicates.get("before_declared_roles", [])),
            "before role predicate mismatch",
        )
        require(
            observed_roles["after_reference"] == set(predicates.get("after_declared_roles", [])),
            "after role predicate mismatch",
        )
        preserve_roles = set(row["requirements"][0]["preserve_roles"])
        require(
            preserve_roles <= observed_roles["before"] & observed_roles["after_reference"],
            "declared preservation role missing",
        )
        target_roles = set(predicates.get("target_roles", []))
        operation = row.get("operation")
        if operation in {"add", "reconnect"}:
            require(target_roles <= observed_roles["after_reference"], "repair target absent after")
            require(not target_roles <= observed_roles["before"], "repair target already complete before")
        elif operation == "remove":
            require(target_roles <= observed_roles["before"], "removal target absent before")
            require(not target_roles & observed_roles["after_reference"], "removal target remains after")
        elif operation == "move":
            require(
                target_roles <= observed_roles["before"] & observed_roles["after_reference"],
                "move target must exist in both states",
            )
        else:
            raise ValueError(f"unsupported operation: {operation}")
        require(row.get("before_sha256") != row.get("after_sha256"), "repair has no byte edit")
        require(
            row.get("before_render_sha256") != row.get("after_render_sha256"),
            "repair has no visible canonical edit",
        )
    require(len(groups) == payload.get("scene_group_count") == 12, "need 12 scene groups")
    group_partitions = Counter()
    for rows in groups.values():
        require(len(rows) == 8, "every scene group must contain 8 episodes")
        require(len({row.get("defect_family") for row in rows}) == 8, "defect family missing")
        assigned = {row.get("proposed_partition") for row in rows}
        require(len(assigned) == 1, "scene group crosses proposed partitions")
        group_partitions[next(iter(assigned))] += 1
    require(
        group_partitions == {"proposed-development": 9, "proposed-held-out": 3},
        "group allocation must be 9/3",
    )
    require(
        set(payload["split_policy"]["selected_held_out_groups"])
        == {
            group
            for group, rows in groups.items()
            if rows[0]["proposed_partition"] == "proposed-held-out"
        },
        "held-out group declaration mismatch",
    )
    for family in families:
        allocation = Counter(
            row.get("proposed_partition") for row in episodes if row.get("defect_family") == family
        )
        require(
            allocation == {"proposed-development": 9, "proposed-held-out": 3},
            f"unbalanced defect allocation: {family}",
        )
    print("T14 candidate package valid: 96 project-original episodes; proposed 72/24 group split")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
