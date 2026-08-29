#!/usr/bin/env python3
"""Fail-closed validation for the non-normative T14 candidate package."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path

from defusedxml import ElementTree as ET  # nosec B405

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


def wheel_geometry(svg: str) -> dict[str, tuple[float, float, float]]:
    """Return unique, finite circle geometry for the two declared wheels."""
    root = ET.fromstring(svg)
    geometry: dict[str, tuple[float, float, float]] = {}
    for element in root.iter():
        role = element.attrib.get("data-role")
        if role not in {"front-wheel", "rear-wheel"}:
            continue
        require(role not in geometry, f"duplicate {role} geometry")
        try:
            values = tuple(float(element.attrib[key]) for key in ("cx", "cy", "r"))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid {role} geometry") from exc
        require(all(math.isfinite(value) for value in values), f"non-finite {role} geometry")
        require(values[2] > 0, f"non-positive {role} radius")
        geometry[role] = values
    require(set(geometry) == {"front-wheel", "rear-wheel"}, "wheel geometry incomplete")
    return geometry


def pedal_contact_geometry(svg: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the pedal centre and the terminal point of the declared foot-contact path."""
    root = ET.fromstring(svg)
    pedal: tuple[float, float] | None = None
    endpoint: tuple[float, float] | None = None
    for element in root.iter():
        role = element.attrib.get("data-role")
        if role == "pedal":
            require(pedal is None, "duplicate pedal geometry")
            try:
                pedal = (float(element.attrib["cx"]), float(element.attrib["cy"]))
            except (KeyError, ValueError) as exc:
                raise ValueError("invalid pedal geometry") from exc
        elif role == "foot pedal contact":
            require(endpoint is None, "duplicate foot-contact geometry")
            numbers = tuple(
                float(value)
                for value in re.findall(r"-?(?:\d+(?:\.\d*)?|\.\d+)", element.attrib.get("d", ""))
            )
            require(len(numbers) >= 2 and len(numbers) % 2 == 0, "invalid foot-contact path")
            endpoint = (numbers[-2], numbers[-1])
    require(pedal is not None and endpoint is not None, "pedal-contact geometry incomplete")
    require(
        all(math.isfinite(value) for point in (pedal, endpoint) for value in point),
        "non-finite pedal-contact geometry",
    )
    return pedal, endpoint


def scene_geometry_signature(svg: str) -> tuple[tuple[str, str], ...]:
    """Describe visible scene geometry without trusting manifest labels."""
    root = ET.fromstring(svg)
    geometry = []
    for element in root.iter():
        role = element.attrib.get("data-role", "")
        if role in {
            "front-wheel",
            "rear-wheel",
            "auxiliary-wheel",
            "frame",
            "ground",
            "cargo-platform",
        }:
            values = "|".join(
                element.attrib.get(key, "")
                for key in ("cx", "cy", "r", "x", "y", "width", "height", "d")
            )
            require(values.strip("|") != "", f"missing visible geometry for {role}")
            geometry.append((role, values))
    require(
        {"front-wheel", "rear-wheel", "frame", "ground"} <= {role for role, _ in geometry},
        "scene geometry incomplete",
    )
    return tuple(sorted(geometry))


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
        observed_svg: dict[str, str] = {}
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
            observed_svg[path_key] = svg
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
            require(
                not target_roles <= observed_roles["before"],
                "repair target already complete before",
            )
        elif operation == "remove":
            require(target_roles <= observed_roles["before"], "removal target absent before")
            require(
                not target_roles & observed_roles["after_reference"], "removal target remains after"
            )
        elif operation == "move":
            require(
                target_roles <= observed_roles["before"] & observed_roles["after_reference"],
                "move target must exist in both states",
            )
            if row.get("defect_family") == "displaced-rear-wheel":
                before_wheels = wheel_geometry(observed_svg["before"])
                after_wheels = wheel_geometry(observed_svg["after_reference"])
                require(
                    before_wheels["rear-wheel"][1] != before_wheels["front-wheel"][1],
                    "rear wheel is not displaced before repair",
                )
                require(
                    after_wheels["rear-wheel"][1] == after_wheels["front-wheel"][1],
                    "rear wheel is not aligned after repair",
                )
                require(
                    before_wheels["rear-wheel"] != after_wheels["rear-wheel"],
                    "rear-wheel geometry is unchanged",
                )
            elif row.get("defect_family") == "missing-pedal-contact":
                before_pedal, before_foot = pedal_contact_geometry(observed_svg["before"])
                after_pedal, after_foot = pedal_contact_geometry(observed_svg["after_reference"])
                require(before_pedal == after_pedal, "pedal moved during contact repair")
                require(before_foot != after_foot, "foot-contact geometry is unchanged")
                require(
                    math.dist(after_pedal, after_foot) < math.dist(before_pedal, before_foot),
                    "foot endpoint is not closer to pedal after repair",
                )
            else:
                raise ValueError(f"unsupported move defect family: {row.get('defect_family')}")
        else:
            raise ValueError(f"unsupported operation: {operation}")
        require(row.get("before_sha256") != row.get("after_sha256"), "repair has no byte edit")
        require(
            row.get("before_render_sha256") != row.get("after_render_sha256"),
            "repair has no visible canonical edit",
        )
    require(len(groups) == payload.get("scene_group_count") == 24, "need 24 scene groups")
    group_partitions = Counter()
    for rows in groups.values():
        require(len(rows) == 4, "every scene group must contain 4 episodes")
        require(len({row.get("defect_family") for row in rows}) == 4, "defect family missing")
        require(
            Counter(row.get("severity") for row in rows) == {"moderate": 2, "severe": 2},
            "scene severity must be 2/2",
        )
        assigned = {row.get("proposed_partition") for row in rows}
        require(len(assigned) == 1, "scene group crosses proposed partitions")
        group_partitions[next(iter(assigned))] += 1
    require(
        group_partitions == {"proposed-development": 18, "proposed-held-out": 6},
        "group allocation must be 18/6",
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
        severity = Counter(
            row.get("severity") for row in episodes if row.get("defect_family") == family
        )
        require(severity == {"moderate": 6, "severe": 6}, f"severity not crossed for {family}")
        moderate = {
            row.get("severity_parameter")
            for row in episodes
            if row.get("defect_family") == family and row.get("severity") == "moderate"
        }
        severe = {
            row.get("severity_parameter")
            for row in episodes
            if row.get("defect_family") == family and row.get("severity") == "severe"
        }
        require(
            len(moderate) == len(severe) == 1 and max(moderate) < min(severe),
            f"severity parameter ordering invalid: {family}",
        )
        vehicles = Counter(
            row.get("vehicle_family") for row in episodes if row.get("defect_family") == family
        )
        require(
            vehicles
            == {
                "bicycle": 3,
                "tricycle": 3,
                "step-through-cycle": 3,
                "cargo-cycle": 3,
            },
            f"defect family is confounded with vehicle: {family}",
        )
    signatures = {}
    for group, rows in groups.items():
        reference = resolve_candidate_asset(Path(str(rows[0]["after_reference"]))).read_text()
        signature = scene_geometry_signature(reference)
        require(signature not in signatures, f"duplicate visible scene geometry: {group}")
        signatures[signature] = group
    vehicle_signatures = defaultdict(set)
    for rows in groups.values():
        reference = resolve_candidate_asset(Path(str(rows[0]["after_reference"]))).read_text()
        vehicle_signatures[str(rows[0].get("vehicle_family"))].add(
            scene_geometry_signature(reference)
        )
    require(
        set(vehicle_signatures) == {"bicycle", "tricycle", "step-through-cycle", "cargo-cycle"},
        "vehicle topology coverage drift",
    )
    require(
        all(len(items) == 6 for items in vehicle_signatures.values()),
        "vehicle geometry is metadata-only",
    )
    held_out_rows = [
        row for row in episodes if row.get("proposed_partition") == "proposed-held-out"
    ]
    require(
        {row.get("vehicle_family") for row in held_out_rows}
        == {"bicycle", "tricycle", "step-through-cycle", "cargo-cycle"},
        "held-out vehicle coverage incomplete",
    )
    require(
        {row.get("layout_template_id") for row in held_out_rows}
        == {"level-wide", "rising-close", "falling-offset"},
        "held-out layout coverage incomplete",
    )
    require(
        {row.get("geometry_variant") for row in held_out_rows} == {0, 1},
        "held-out geometry variant coverage incomplete",
    )
    print("T14 candidate package valid: 96 episodes; proposed 72/24 split across 18/6 groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
