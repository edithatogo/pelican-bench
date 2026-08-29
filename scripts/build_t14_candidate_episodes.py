#!/usr/bin/env python3
"""Build the unfrozen, project-original T14 repair candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from functools import cache
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmark/fixtures/repair/candidate"
sys.path.insert(0, str(ROOT / "src"))
from pelicanbench.render import render_svg  # ruff: ignore[module-import-not-at-top-of-file]
from pelicanbench.svg import inspect_svg  # ruff: ignore[module-import-not-at-top-of-file]


@dataclass(frozen=True)
class Scene:
    scene_id: str
    vehicle: str
    layout: str
    variant: int
    body: str
    accent: str
    ink: str


VEHICLES = ("bicycle", "tricycle", "step-through-cycle", "cargo-cycle")
LAYOUTS = ("level-wide", "rising-close", "falling-offset")
PALETTES = (
    ("#f5f1df", "#e8793e", "#263238"),
    ("#d8e7eb", "#d9903d", "#283845"),
    ("#f4e7a1", "#e0693e", "#31505b"),
    ("#b9d4d0", "#d46b45", "#283b42"),
)
SCENES = tuple(
    Scene(
        f"scene-{i + 1:02d}",
        VEHICLES[i % 4],
        LAYOUTS[(i // 4) % 3],
        i // 12,
        *PALETTES[(i * 3 + i // 4) % 4],
    )
    for i in range(24)
)
DEFECTS = (
    ("missing-front-wheel", "add", ("front", "wheel")),
    ("displaced-rear-wheel", "move", ("rear", "wheel")),
    ("broken-frame", "reconnect", ("frame", "brace")),
    ("missing-eye", "add", ("eye",)),
    ("missing-wing", "add", ("wing",)),
    ("missing-pedal-contact", "move", ("foot", "pedal", "contact")),
    ("missing-steering-contact", "reconnect", ("riding", "grip", "contact")),
    ("interaction-occlusion", "remove", ("obstruction",)),
)
PARAMETERS = {
    "missing-front-wheel": (24, 48),
    "displaced-rear-wheel": (24, 48),
    "broken-frame": (22, 58),
    "missing-eye": (3, 6),
    "missing-wing": (34, 68),
    "missing-pedal-contact": (31, 66),
    "missing-steering-contact": (30, 72),
    "interaction-occlusion": (60, 110),
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@cache
def _render(value: str) -> str:
    return render_svg(value).render_hash


def _parameter(defect: str, severity: str) -> int:
    return PARAMETERS[defect][severity == "severe"]


def _defect_block(scene_index: int) -> tuple[int, ...]:
    """Return a complementary BIB block: every family occurs 3x per vehicle."""
    vehicle = scene_index % 4
    replicate = scene_index // 4
    start = vehicle + 2 * (replicate // 2)
    first = {(start + offset) % 8 for offset in range(4)}
    block = first if replicate % 2 == 0 else set(range(8)) - first
    return tuple(sorted(block))


def _severity_assignment() -> dict[tuple[int, int], str]:
    """Choose two severe cells per group and six per family, deterministically."""
    blocks = [_defect_block(index) for index in range(24)]
    counts = [0] * 8
    selected: dict[int, tuple[int, int]] = {}

    def visit(group: int) -> bool:
        if group == 24:
            return counts == [6] * 8
        remaining = Counter(defect for block in blocks[group:] for defect in block)
        if any(counts[d] > 6 or counts[d] + remaining[d] < 6 for d in range(8)):
            return False
        for pair in combinations(blocks[group], 2):
            if any(counts[d] == 6 for d in pair):
                continue
            for defect in pair:
                counts[defect] += 1
            selected[group] = pair
            if visit(group + 1):
                return True
            for defect in pair:
                counts[defect] -= 1
        return False

    if not visit(0):
        raise RuntimeError("no balanced severity assignment")
    return {
        (group, defect): "severe" if defect in selected[group] else "moderate"
        for group, block in enumerate(blocks)
        for defect in block
    }


def _selected_held_out_groups(severity: dict[tuple[int, int], str]) -> set[str]:
    """Exhaustively select six groups from design factors, without outcomes."""
    ranked = []
    for chosen in combinations(range(24), 6):
        family = Counter(d for group in chosen for d in _defect_block(group))
        if set(family.values()) != {3} or len(family) != 8:
            continue
        vehicles = Counter(SCENES[g].vehicle for g in chosen)
        layouts = Counter(SCENES[g].layout for g in chosen)
        variants = Counter(SCENES[g].variant for g in chosen)
        severe = Counter(d for g in chosen for d in _defect_block(g) if severity[g, d] == "severe")
        coverage_penalty = (
            len(VEHICLES) - len(vehicles) + len(LAYOUTS) - len(layouts) + 2 - len(variants)
        )
        balance = sum((vehicles[key] - 1.5) ** 2 for key in VEHICLES)
        balance += sum((layouts[key] - 2) ** 2 for key in LAYOUTS)
        balance += sum((variants[key] - 3) ** 2 for key in (0, 1))
        severity_imbalance = sum(abs(severe[d] - 1.5) for d in range(8))
        identity = ",".join(f"{g:02d}" for g in chosen)
        tie = hashlib.sha256(f"t14-72-24-v3\0{identity}".encode()).hexdigest()
        ranked.append(((coverage_penalty, balance, severity_imbalance, tie), chosen))
    if not ranked:
        raise RuntimeError("no balanced held-out allocation")
    return {SCENES[index].scene_id for index in min(ranked)[1]}


def _layout(s: Scene) -> tuple[int, int, int, int, int]:
    n = LAYOUTS.index(s.layout)
    dx = (-18, 4, 20)[n] + s.variant * 5
    dy = (0, -13, 10)[n] + s.variant * 3
    rear = 128 + dx
    return rear, rear + (202, 184, 218)[n], 250 + dy, dx, dy


def _svg(s: Scene, defect: str | None, severity: str = "moderate") -> str:
    rear, front, wy, _dx, dy = _layout(s)
    p = _parameter(defect, severity) if defect else 0
    ry = wy + p if defect == "displaced-rear-wheel" else wy
    mid = (rear + front) // 2
    fy = 188 + dy
    bx = mid - 10
    by = 128 + dy
    q = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" viewBox="0 0 480 320">',
        '<rect width="480" height="320" fill="#ffffff"/>',
        f'<path data-role="ground" d="M20 {280 + dy // 4} L460 {276 - dy // 4}" stroke="#c8d4d8" stroke-width="5"/>',
    ]
    if defect == "missing-front-wheel" and severity == "moderate":
        q.append(
            f'<path data-role="component-damaged" d="M{front - p} {wy} A48 48 0 0 1 {front} {wy - p}" fill="none" stroke="{s.ink}" stroke-width="9"/>'
        )
    elif defect != "missing-front-wheel":
        q.append(
            f'<circle data-role="front-wheel" cx="{front}" cy="{wy}" r="48" fill="none" stroke="{s.ink}" stroke-width="9"/>'
        )
    q.append(
        f'<circle data-role="rear-wheel" cx="{rear}" cy="{ry}" r="48" fill="none" stroke="{s.ink}" stroke-width="9"/>'
    )
    if s.vehicle == "tricycle":
        q.append(
            f'<circle data-role="auxiliary-wheel" cx="{rear - 34}" cy="{wy + 8}" r="34" fill="none" stroke="{s.ink}" stroke-width="7"/>'
        )
    frame = (
        f"M{rear} {wy} L{mid} {wy} Q{mid + 18} {fy + 35} {front - 38} {fy} L{front} {wy}"
        if s.vehicle == "step-through-cycle"
        else f"M{rear} {wy} L{mid} {wy} L{front - 48} {fy} L{front} {wy} L{mid} {wy} L{rear + 50} {fy + 4}"
    )
    q += [
        f'<path data-role="frame" d="{frame}" fill="none" stroke="{s.accent}" stroke-width="10"/>',
        f'<path data-role="handlebar" d="M{front - 48} {fy} L{front - 20} {145 + dy} L{front + 8} {145 + dy}" fill="none" stroke="{s.ink}" stroke-width="8"/>',
        f'<circle data-role="pedal" cx="{mid}" cy="{wy}" r="13" fill="{s.accent}" stroke="{s.ink}" stroke-width="5"/>',
    ]
    if s.vehicle == "cargo-cycle":
        q.append(
            f'<rect data-role="cargo-platform" x="{rear - 38}" y="{fy - 22}" width="92" height="24" fill="{s.accent}" stroke="{s.ink}" stroke-width="5"/>'
        )
    if defect == "broken-frame":
        q.append(
            f'<path data-role="frame-damaged" d="M{rear + 50} {fy + 4} L{mid - p // 2} {fy} M{mid + p // 2} {fy} L{front - 48} {fy}" stroke="{s.accent}" stroke-width="10"/>'
        )
    else:
        q.append(
            f'<path data-role="frame-brace" d="M{rear + 50} {fy + 4} L{front - 48} {fy}" stroke="{s.accent}" stroke-width="10"/>'
        )
    q += [
        f'<ellipse data-role="animal body pelican" cx="{bx}" cy="{by}" rx="{66 + s.variant * 4}" ry="49" fill="{s.body}" stroke="{s.ink}" stroke-width="6"/>',
        f'<circle data-role="animal head" cx="{bx + 60}" cy="{88 + dy}" r="34" fill="{s.body}" stroke="{s.ink}" stroke-width="6"/>',
        f'<path data-role="bill" d="M{bx + 88} {79 + dy} L{bx + 190} {96 + dy} L{bx + 90} {106 + dy} Z" fill="{s.accent}" stroke="{s.ink}" stroke-width="5"/>',
    ]
    if defect == "missing-eye" and severity == "moderate":
        q.append(
            f'<circle data-role="component-damaged" cx="{bx + 70}" cy="{79 + dy}" r="1" fill="{s.ink}"/>'
        )
    elif defect != "missing-eye":
        q.append(f'<circle data-role="eye" cx="{bx + 70}" cy="{79 + dy}" r="5" fill="{s.ink}"/>')
    q.append(
        f'<path data-role="gular pouch" d="M{bx + 89} {105 + dy} Q{bx + 140} {151 + dy} {bx + 187} {98 + dy} Q{bx + 135} {123 + dy} {bx + 89} {105 + dy} Z" fill="#f2aa72" stroke="{s.ink}" stroke-width="4"/>'
    )
    if defect == "missing-wing" and severity == "moderate":
        q.append(
            f'<path data-role="component-damaged" d="M{bx - 32} {115 + dy} Q{bx} {100 + dy} {bx + p // 2} {133 + dy}" fill="none" stroke="{s.ink}" stroke-width="5"/>'
        )
    elif defect != "missing-wing":
        q.append(
            f'<path data-role="wing" d="M{bx - 32} {115 + dy} Q{bx + 5} {88 + dy} {bx + 36} {133 + dy} Q{bx - 3} {161 + dy} {bx - 32} {115 + dy} Z" fill="#a9cbd0" stroke="{s.ink}" stroke-width="5"/>'
        )
    footx = mid + 8 if defect != "missing-pedal-contact" else mid - p
    footy = wy - 3 if defect != "missing-pedal-contact" else wy - p // 3
    q.append(
        f'<path data-role="foot pedal contact" d="M{bx - 8} {164 + dy} L{mid - 10} {205 + dy} L{footx} {footy}" fill="none" stroke="{s.ink}" stroke-width="8"/>'
    )
    if defect == "missing-steering-contact":
        q.append(
            f'<path data-role="steering-incomplete" d="M{bx + 34} {133 + dy} Q{bx + 52} {135 + dy} {front - p} {148 + dy}" fill="none" stroke="{s.ink}" stroke-width="8"/>'
        )
    else:
        q.append(
            f'<path data-role="riding grip contact" d="M{bx + 34} {133 + dy} Q{bx + 76} {135 + dy} {front - 14} {148 + dy}" fill="none" stroke="{s.ink}" stroke-width="8"/>'
        )
    if defect == "interaction-occlusion":
        q.append(
            f'<rect data-role="obstruction" x="{mid - p // 2}" y="{151 + dy}" width="{p}" height="{p * 3 // 4}" rx="8" fill="#6d7780"/>'
        )
    return "\n".join([*q, "</svg>"]) + "\n"


def _payload(recorded: dict[str, str] | None = None) -> tuple[dict[str, object], dict[Path, str]]:
    assets = {}
    episodes = []
    severity_assignment = _severity_assignment()
    held = _selected_held_out_groups(severity_assignment)
    for si, s in enumerate(SCENES):
        for di in _defect_block(si):
            defect, operation, targets = DEFECTS[di]
            severity = severity_assignment[si, di]
            p = _parameter(defect, severity)
            rid = f"repair-t14-candidate-{si + 1:02d}-{di + 1:02d}"
            br = Path("assets") / f"{rid}-before.svg"
            ar = Path("assets") / f"{rid}-after.svg"
            before, after = _svg(s, defect, severity), _svg(s, None)
            assets[br] = before
            assets[ar] = after
            bh, ah = _sha(before), _sha(after)

            def get(value: str, digest: str) -> str:
                return (recorded or {}).get(digest, _render(value))

            partition = "proposed-held-out" if s.scene_id in held else "proposed-development"

            def roles(value: str) -> list[str]:
                return sorted(inspect_svg(value).features["declared_role_counts"])

            episodes.append(
                {
                    "repair_id": rid,
                    "task_id": f"pb:t14-candidate:{s.scene_id}:{defect}",
                    "status": "candidate-development-only",
                    "scene_group_id": s.scene_id,
                    "geometry_template_id": s.vehicle,
                    "layout_template_id": s.layout,
                    "geometry_variant": s.variant,
                    "bird_family": "pelican",
                    "vehicle_family": s.vehicle,
                    "defect_family": defect,
                    "severity": severity,
                    "severity_parameter": p,
                    "operation": operation,
                    "sampling_cell_id": f"{s.scene_id}:{defect}:{severity}",
                    "proposed_partition": partition,
                    "before": f"benchmark/fixtures/repair/candidate/{br}",
                    "after_reference": f"benchmark/fixtures/repair/candidate/{ar}",
                    "before_sha256": bh,
                    "after_sha256": ah,
                    "before_render_sha256": get(before, bh),
                    "after_render_sha256": get(after, ah),
                    "canonical_render": {
                        "method": "render_svg-v1",
                        "canvas_px": 512,
                        "background": "opaque-white",
                    },
                    "intended_edit": {
                        "defect_family": defect,
                        "operation": operation,
                        "allowed_scope": "repair the declared defect only",
                        "preserve": ["animal identity", "bill", "vehicle identity", "canvas"],
                        "introduced_defect_expectation": "none",
                    },
                    "expected_predicates": {
                        "before_declared_roles": roles(before),
                        "after_declared_roles": roles(after),
                        "target_roles": list(targets),
                        "shared_reference_group": s.scene_id,
                    },
                    "requirements": [
                        {
                            "defect_id": defect,
                            "description": f"Repair {defect}.",
                            "preserve_roles": ["animal", "bill", "frame"],
                            "target_roles": list(targets),
                        }
                    ],
                }
            )
    manifest = {
        "schema_version": "2.0.0",
        "status": "candidate-development-only",
        "normative_sample_frozen": False,
        "human_ratings_present": False,
        "agent_outputs_are_ratings": False,
        "score_promotion": "prohibited-pending-steward-decision",
        "publication_status": "not-published",
        "provenance": {
            "origin": "project-original-deterministic-svg-generator",
            "generator": "scripts/build_t14_candidate_episodes.py",
            "external_source_material": False,
            "rights_status": "project-original",
            "generator_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "split_policy": {
            "status": "proposed-not-frozen",
            "unit": "scene-group",
            "namespace": "t14-72-24-v3",
            "rule": "exhaustive six-of-24 outcome-free allocation: exact 9/3 family balance; maximize vehicle, layout and variant coverage; minimize factor and severity imbalance; SHA-256 tie-break",
            "leakage_control": "all variants from a scene remain in one partition",
            "selected_held_out_groups": sorted(held),
            "development_count": 72,
            "held_out_count": 24,
        },
        "episode_count": 96,
        "scene_group_count": 24,
        "episodes_per_scene_group": 4,
        "defect_family_count": 8,
        "episodes": episodes,
    }
    return manifest, assets


def _expected_files(output: Path, *, reuse_recorded_render_hashes: bool = False) -> dict[Path, str]:
    recorded = None
    mp = output / "manifest.json"
    if reuse_recorded_render_hashes and mp.is_file():
        recorded = {}
        for r in json.loads(mp.read_text())["episodes"]:
            recorded[r["before_sha256"]] = r["before_render_sha256"]
            recorded[r["after_sha256"]] = r["after_render_sha256"]
    manifest, assets = _payload(recorded)
    result = {output / p: v for p, v in assets.items()}
    result[mp] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    expected = _expected_files(a.output, reuse_recorded_render_hashes=a.check)
    if a.check:
        changed = [
            str(x.relative_to(ROOT))
            for x, v in expected.items()
            if not x.is_file() or x.read_text() != v
        ]
        unexpected = [
            str(x.relative_to(ROOT))
            for x in a.output.rglob("*")
            if x.is_file() and x not in expected
        ]
        if changed or unexpected:
            print(json.dumps({"missing_or_changed": changed, "unexpected": unexpected}, indent=2))
            return 1
        print("T14 candidate deterministic: 96 episodes; proposed 72/24 split across 18/6 groups")
        return 0
    for x, v in expected.items():
        x.parent.mkdir(parents=True, exist_ok=True)
        x.write_text(v)
    for path in a.output.rglob("*"):
        if path.is_file() and path not in expected:
            path.unlink()
    print(f"Wrote {len(expected) - 1} SVG assets and candidate manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
