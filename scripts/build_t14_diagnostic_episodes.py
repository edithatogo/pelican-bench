#!/usr/bin/env python3
"""Build separate non-normative T14 adversarial diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmark/fixtures/repair/diagnostic"
sys.path.insert(0, str(ROOT / "src"))
from pelicanbench.render import render_svg  # ruff: ignore[module-import-not-at-top-of-file]

SPEC = importlib.util.spec_from_file_location(
    "t14_builder", ROOT / "scripts/build_t14_candidate_episodes.py"
)
assert SPEC and SPEC.loader
B = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = B
SPEC.loader.exec_module(B)
CLASSES = ("under-repair", "over-edit", "introduced-defect", "decision-boundary", "invalid")


def sha(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def mutate(reference: str, defect: str, kind: str, scene: object) -> str:
    if kind == "under-repair":
        return B._svg(scene, defect, "moderate")
    if kind == "introduced-defect":
        return B._svg(scene, "missing-wing" if defect == "missing-eye" else "missing-eye", "severe")
    if kind == "invalid":
        return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320"><rect width="480" height="320" fill="#fff"/></svg>\n'
    marker = f'<circle data-role="{"over-edit" if kind == "over-edit" else "boundary-artifact"}" cx="{18 if kind == "decision-boundary" else 430}" cy="{18 if kind == "decision-boundary" else 45}" r="{2 if kind == "decision-boundary" else 24}" fill="#c2185b"/>'
    return reference.replace("</svg>", marker + "\n</svg>")


def expected(output: Path) -> dict[Path, str]:
    assets = {}
    rows = []
    for di, (defect, _, _) in enumerate(B.DEFECTS):
        scene = B.SCENES[di]
        for ci, kind in enumerate(CLASSES):
            reference = B._svg(scene, None)
            artifact = mutate(reference, defect, kind, scene)
            rid = f"diagnostic-t14-{di + 1:02d}-{ci + 1:02d}"
            rel = Path("assets") / f"{rid}.svg"
            assets[rel] = artifact
            rows.append(
                {
                    "diagnostic_id": rid,
                    "status": "diagnostic-development-only",
                    "normative_eligible": False,
                    "diagnostic_class": kind,
                    "defect_family": defect,
                    "artifact": f"benchmark/fixtures/repair/diagnostic/{rel}",
                    "artifact_sha256": sha(artifact),
                    "artifact_render_sha256": render_svg(artifact).render_hash,
                    "expected_validity": kind != "invalid",
                    "expected_outcome": "reject-or-flag",
                    "project_original": True,
                }
            )
    manifest = {
        "schema_version": "1.0.0",
        "status": "diagnostic-development-only",
        "normative_eligible": False,
        "normative_sample_frozen": False,
        "human_ratings_present": False,
        "score_promotion": "prohibited",
        "publication_status": "not-published",
        "episode_count": 40,
        "diagnostic_classes": list(CLASSES),
        "defect_family_count": 8,
        "provenance": {
            "origin": "project-original-deterministic-svg-generator",
            "generator": "scripts/build_t14_diagnostic_episodes.py",
            "external_source_material": False,
            "generator_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "episodes": rows,
    }
    result = {output / p: v for p, v in assets.items()}
    result[output / "manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    exp = expected(a.output)
    if a.check:
        changed = [
            str(x.relative_to(ROOT))
            for x, v in exp.items()
            if not x.is_file() or x.read_text() != v
        ]
        unexpected = [
            str(x.relative_to(ROOT)) for x in a.output.rglob("*") if x.is_file() and x not in exp
        ]
        if changed or unexpected:
            print(json.dumps({"missing_or_changed": changed, "unexpected": unexpected}, indent=2))
            return 1
        print("T14 diagnostics deterministic: 40 non-normative cases")
        return 0
    for x, v in exp.items():
        x.parent.mkdir(parents=True, exist_ok=True)
        x.write_text(v)
    print("Wrote 40 separate diagnostic assets and manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
