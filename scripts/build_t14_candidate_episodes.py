#!/usr/bin/env python3
"""Build the non-normative T14 project-original candidate repair episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from functools import cache
from itertools import combinations
from operator import itemgetter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmark/fixtures/repair/candidate"
sys.path.insert(0, str(ROOT / "src"))

from pelicanbench.render import render_svg  # ruff: ignore[module-import-not-at-top-of-file]
from pelicanbench.svg import inspect_svg  # ruff: ignore[module-import-not-at-top-of-file]


@dataclass(frozen=True)
class Scene:
    scene_id: str
    palette_family: str
    vehicle: str
    body: str
    accent: str
    wheel: str
    shift_x: int
    shift_y: int


SCENES = (
    Scene("scene-01", "warm-cream", "bicycle", "#f5f1df", "#e8793e", "#263238", -8, 0),
    Scene("scene-02", "warm-cream", "tricycle", "#fff4cf", "#cc5a35", "#24424c", 0, -4),
    Scene("scene-03", "cool-blue", "bicycle", "#d8e7eb", "#d9903d", "#283845", 7, 2),
    Scene("scene-04", "golden", "step-through-cycle", "#f4e7a1", "#e0693e", "#31505b", -4, 5),
    Scene("scene-05", "neutral-gray", "bicycle", "#e7ecef", "#f08b3e", "#1f2d33", 5, -2),
    Scene("scene-06", "teal", "cargo-cycle", "#b9d4d0", "#d46b45", "#283b42", -6, 4),
    Scene("scene-07", "warm-cream", "step-through-cycle", "#f6e8cd", "#cf7042", "#384a52", 8, 1),
    Scene("scene-08", "cool-blue", "tricycle", "#dbe8ea", "#bd633f", "#263e49", -2, -5),
    Scene("scene-09", "golden", "cargo-cycle", "#f2df8c", "#e1773e", "#304b55", 4, 3),
    Scene("scene-10", "neutral-gray", "step-through-cycle", "#e1e8ec", "#f08a43", "#253740", -7, -1),
    Scene("scene-11", "teal", "bicycle", "#bdd7d2", "#ca6842", "#31434b", 2, 5),
    Scene("scene-12", "warm-cream", "cargo-cycle", "#f7ecd3", "#d87542", "#293f48", 7, -4),
)


DEFECTS = (
    ("missing-front-wheel", "severe", "Restore the missing front wheel without changing the bird."),
    ("displaced-rear-wheel", "severe", "Realign the rear wheel with the vehicle frame."),
    ("broken-frame", "severe", "Reconnect the broken load-bearing frame segment."),
    ("missing-eye", "moderate", "Restore the bird's visible eye without changing its bill."),
    ("missing-wing", "moderate", "Restore the visible wing while preserving body and bill."),
    ("missing-pedal-contact", "moderate", "Restore explicit foot-to-pedal contact."),
    ("missing-steering-contact", "moderate", "Restore explicit wing-to-handle contact."),
    ("interaction-occlusion", "severe", "Remove the obstruction hiding the riding interaction."),
)

DEFECT_OPERATIONS = {
    "missing-front-wheel": ("add", ["front", "wheel"]),
    "displaced-rear-wheel": ("move", ["rear", "wheel"]),
    "broken-frame": ("reconnect", ["frame", "brace"]),
    "missing-eye": ("add", ["eye"]),
    "missing-wing": ("add", ["wing"]),
    "missing-pedal-contact": ("move", ["foot", "pedal", "contact"]),
    "missing-steering-contact": ("reconnect", ["riding", "grip", "contact"]),
    "interaction-occlusion": ("remove", ["obstruction"]),
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@cache
def _render_hash(value: str) -> str:
    return render_svg(value).render_hash


def _svg(scene: Scene, defect: str | None) -> str:
    dx, dy = scene.shift_x, scene.shift_y
    rear_x, front_x, wheel_y = 132 + dx, 340 + dx, 252 + dy
    rear_y = wheel_y + 38 if defect == "displaced-rear-wheel" else wheel_y
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" viewBox="0 0 480 320">',
        '<rect width="480" height="320" fill="#ffffff"/>',
        '<path d="M24 276 H456" stroke="#c8d4d8" stroke-width="5"/>',
    ]
    if defect != "missing-front-wheel":
        pieces.append(
            f'<circle data-role="front-wheel" cx="{front_x}" cy="{wheel_y}" r="48" fill="none" stroke="{scene.wheel}" stroke-width="9"/>'
        )
    pieces.append(
        f'<circle data-role="rear-wheel" cx="{rear_x}" cy="{rear_y}" r="48" fill="none" stroke="{scene.wheel}" stroke-width="9"/>'
    )
    pieces.extend(
        [
            f'<path data-role="frame" d="M{rear_x} {wheel_y} L{222 + dx} {wheel_y} L{292 + dx} {184 + dy} L{front_x} {wheel_y} L{222 + dx} {wheel_y} L{184 + dx} {188 + dy}" fill="none" stroke="{scene.accent}" stroke-width="10" stroke-linejoin="round"/>',
            f'<path data-role="handlebar" d="M{292 + dx} {184 + dy} L{321 + dx} {145 + dy} L{347 + dx} {145 + dy}" fill="none" stroke="{scene.wheel}" stroke-width="8" stroke-linecap="round"/>',
            f'<circle data-role="pedal" cx="{222 + dx}" cy="{wheel_y}" r="13" fill="{scene.accent}" stroke="{scene.wheel}" stroke-width="5"/>',
        ]
    )
    if defect != "broken-frame":
        pieces.append(
            f'<path data-role="frame-brace" d="M{184 + dx} {188 + dy} L{292 + dx} {184 + dy}" stroke="{scene.accent}" stroke-width="10"/>'
        )
    pieces.extend(
        [
            f'<ellipse data-role="animal body pelican" cx="{210 + dx}" cy="{128 + dy}" rx="70" ry="49" fill="{scene.body}" stroke="{scene.wheel}" stroke-width="6"/>',
            f'<circle data-role="animal head" cx="{270 + dx}" cy="{88 + dy}" r="34" fill="{scene.body}" stroke="{scene.wheel}" stroke-width="6"/>',
            f'<path data-role="bill" d="M{298 + dx} {79 + dy} L{405 + dx} {96 + dy} L{300 + dx} {106 + dy} Z" fill="{scene.accent}" stroke="{scene.wheel}" stroke-width="5"/>',
        ]
    )
    if defect != "missing-eye":
        pieces.append(f'<circle data-role="eye" cx="{280 + dx}" cy="{79 + dy}" r="5" fill="{scene.wheel}"/>')
    pieces.append(
        f'<path data-role="gular pouch" d="M{299 + dx} {105 + dy} Q{350 + dx} {151 + dy} {397 + dx} {98 + dy} Q{345 + dx} {123 + dy} {299 + dx} {105 + dy} Z" fill="#f2aa72" stroke="{scene.wheel}" stroke-width="4"/>'
    )
    if defect != "missing-wing":
        pieces.append(
            f'<path data-role="wing" d="M{178 + dx} {115 + dy} Q{215 + dx} {88 + dy} {246 + dx} {133 + dy} Q{207 + dx} {161 + dy} {178 + dx} {115 + dy} Z" fill="#a9cbd0" stroke="{scene.wheel}" stroke-width="5"/>'
        )
    foot_end_x = 257 + dx if defect != "missing-pedal-contact" else 184 + dx
    foot_end_y = 244 + dy if defect != "missing-pedal-contact" else 224 + dy
    pieces.append(
        f'<path data-role="foot pedal contact" d="M{202 + dx} {164 + dy} L{212 + dx} {205 + dy} L{foot_end_x} {foot_end_y}" fill="none" stroke="{scene.wheel}" stroke-width="8" stroke-linecap="round"/>'
    )
    if defect != "missing-steering-contact":
        pieces.append(
            f'<path data-role="riding grip contact" d="M{244 + dx} {133 + dy} Q{286 + dx} {135 + dy} {326 + dx} {148 + dy}" fill="none" stroke="{scene.wheel}" stroke-width="8" stroke-linecap="round"/>'
        )
    if defect == "interaction-occlusion":
        pieces.append(
            f'<rect data-role="obstruction" x="{174 + dx}" y="{151 + dy}" width="142" height="105" rx="8" fill="#6d7780"/>'
        )
    pieces.append("</svg>")
    return "\n".join(pieces) + "\n"


def _selected_held_out_groups() -> set[str]:
    """Select three groups without outcomes, using a prespecified exhaustive rule."""
    palette_totals = Counter(scene.palette_family for scene in SCENES)
    vehicle_totals = Counter(scene.vehicle for scene in SCENES)
    all_shift_x = sum(scene.shift_x for scene in SCENES) / len(SCENES)
    all_shift_y = sum(scene.shift_y for scene in SCENES) / len(SCENES)
    ranked: list[tuple[tuple[object, ...], tuple[Scene, ...]]] = []
    for held_out in combinations(SCENES, 3):
        held_ids = {scene.scene_id for scene in held_out}
        development = tuple(scene for scene in SCENES if scene.scene_id not in held_ids)
        if {scene.palette_family for scene in development} != set(palette_totals):
            continue
        if {scene.vehicle for scene in development} != set(vehicle_totals):
            continue
        distinct = len({scene.palette_family for scene in held_out}) + len(
            {scene.vehicle for scene in held_out}
        )
        palette_counts = Counter(scene.palette_family for scene in held_out)
        vehicle_counts = Counter(scene.vehicle for scene in held_out)
        categorical_deviation = sum(
            (palette_counts[key] - value / 4) ** 2
            for key, value in palette_totals.items()
        ) + sum(
            (vehicle_counts[key] - value / 4) ** 2 for key, value in vehicle_totals.items()
        )
        shift_imbalance = abs(
            sum(scene.shift_x for scene in held_out) / 3 - all_shift_x
        ) + abs(sum(scene.shift_y for scene in held_out) / 3 - all_shift_y)
        identity = ",".join(sorted(held_ids))
        tie_break = hashlib.sha256(f"t14-72-24-v1\0{identity}".encode()).hexdigest()
        ranked.append(((-distinct, categorical_deviation, shift_imbalance, tie_break), held_out))
    selected = min(ranked, key=itemgetter(0))[1]
    return {scene.scene_id for scene in selected}


def _payload(
    *, recorded_render_hashes: dict[str, str] | None = None
) -> tuple[dict[str, object], dict[Path, str]]:
    assets: dict[Path, str] = {}
    episodes: list[dict[str, object]] = []
    held_out_groups = _selected_held_out_groups()
    for scene_index, scene in enumerate(SCENES, start=1):
        partition = (
            "proposed-held-out"
            if scene.scene_id in held_out_groups
            else "proposed-development"
        )
        for defect_index, (defect, severity, description) in enumerate(DEFECTS, start=1):
            repair_id = f"repair-t14-candidate-{scene_index:02d}-{defect_index:02d}"
            before_rel = Path("assets") / f"{repair_id}-before.svg"
            after_rel = Path("assets") / f"{repair_id}-after.svg"
            before = _svg(scene, defect)
            after = _svg(scene, None)
            before_sha256 = _sha256(before)
            after_sha256 = _sha256(after)
            before_roles = sorted(inspect_svg(before).features["declared_role_counts"])
            after_roles = sorted(inspect_svg(after).features["declared_role_counts"])
            operation, target_roles = DEFECT_OPERATIONS[defect]
            before_render_hash = (
                recorded_render_hashes.get(before_sha256, "missing-recorded-render-hash")
                if recorded_render_hashes is not None
                else _render_hash(before)
            )
            after_render_hash = (
                recorded_render_hashes.get(after_sha256, "missing-recorded-render-hash")
                if recorded_render_hashes is not None
                else _render_hash(after)
            )
            assets[before_rel] = before
            assets[after_rel] = after
            episodes.append(
                {
                    "repair_id": repair_id,
                    "task_id": f"pb:t14-candidate:{scene.scene_id}:{defect}",
                    "status": "candidate-development-only",
                    "scene_group_id": scene.scene_id,
                    "bird_family": "pelican",
                    "palette_family": scene.palette_family,
                    "vehicle_family": scene.vehicle,
                    "defect_family": defect,
                    "severity": severity,
                    "operation": operation,
                    "sampling_cell_id": f"{scene.palette_family}:{scene.vehicle}:{defect}:{severity}",
                    "proposed_partition": partition,
                    "before": f"benchmark/fixtures/repair/candidate/{before_rel.as_posix()}",
                    "after_reference": f"benchmark/fixtures/repair/candidate/{after_rel.as_posix()}",
                    "before_sha256": before_sha256,
                    "after_sha256": after_sha256,
                    "before_render_sha256": before_render_hash,
                    "after_render_sha256": after_render_hash,
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
                        "before_declared_roles": before_roles,
                        "after_declared_roles": after_roles,
                        "target_roles": target_roles,
                        "shared_reference_group": scene.scene_id,
                    },
                    "requirements": [
                        {
                            "defect_id": defect,
                            "description": description,
                            "preserve_roles": ["animal", "bill", "frame"],
                            "target_roles": target_roles,
                        }
                    ],
                }
            )
    manifest: dict[str, object] = {
        "schema_version": "1.0.0",
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
            "authorization_revision": "8dda8a4ecb07c18e9647cb6d97686ec625cbd458",
            "generator_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "split_policy": {
            "status": "proposed-not-frozen",
            "unit": "scene-group",
            "namespace": "t14-72-24-v1",
            "rule": "exhaustive 9/3 group allocation: preserve development coverage, maximize held-out categorical coverage, minimize categorical and x/y shift imbalance, SHA-256 tie-break",
            "leakage_control": "all defect variants and references from a scene remain in one partition",
            "selected_held_out_groups": sorted(held_out_groups),
            "development_count": 72,
            "held_out_count": 24,
        },
        "episode_count": 96,
        "scene_group_count": 12,
        "defect_family_count": 8,
        "episodes": episodes,
    }
    return manifest, assets


def _expected_files(output: Path, *, reuse_recorded_render_hashes: bool = False) -> dict[Path, str]:
    recorded_render_hashes: dict[str, str] | None = None
    manifest_path = output / "manifest.json"
    if reuse_recorded_render_hashes and manifest_path.is_file():
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
        recorded_render_hashes = {}
        for episode in recorded.get("episodes", []):
            recorded_render_hashes[str(episode["before_sha256"])] = str(
                episode["before_render_sha256"]
            )
            recorded_render_hashes[str(episode["after_sha256"])] = str(
                episode["after_render_sha256"]
            )
    manifest, assets = _payload(recorded_render_hashes=recorded_render_hashes)
    result = {output / path: value for path, value in assets.items()}
    result[output / "manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = _expected_files(
        args.output, reuse_recorded_render_hashes=args.check
    )
    if args.check:
        missing_or_changed = [
            str(path.relative_to(ROOT))
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        unexpected = []
        if args.output.exists():
            unexpected = [
                str(path.relative_to(ROOT))
                for path in args.output.rglob("*")
                if path.is_file() and path not in expected
            ]
        if missing_or_changed or unexpected:
            print(json.dumps({"missing_or_changed": missing_or_changed, "unexpected": unexpected}, indent=2))
            return 1
        print("T14 candidate episodes deterministic: 96 episodes, 72/24 proposed split")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Wrote {len(expected) - 1} SVG assets and manifest to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
