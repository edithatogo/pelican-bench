#!/usr/bin/env python3
"""Fail-closed validation for separate T14 diagnostics."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from defusedxml import ElementTree as ET  # nosec B405

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/fixtures/repair/diagnostic/manifest.json"
BASE = MANIFEST.parent.resolve()
sys.path.insert(0, str(ROOT / "src"))
from pelicanbench.render import render_svg  # ruff: ignore[module-import-not-at-top-of-file]
from pelicanbench.svg import inspect_svg  # ruff: ignore[module-import-not-at-top-of-file]

CLASSES = {"under-repair", "over-edit", "introduced-defect", "decision-boundary", "invalid"}


def require(c: object, m: str) -> None:
    if not c:
        raise ValueError(m)


def resolve(path: Path) -> Path:
    require(
        path.parts[:4] == ("benchmark", "fixtures", "repair", "diagnostic"),
        "diagnostic path prefix invalid",
    )
    source = ROOT / path
    target = source.resolve()
    require(
        BASE in target.parents and target.is_file() and not source.is_symlink(),
        "diagnostic path escapes root",
    )
    return target


def main() -> int:
    p = json.loads(MANIFEST.read_text())
    require(p.get("status") == "diagnostic-development-only", "diagnostic status drift")
    require(
        p.get("normative_eligible") is False and p.get("normative_sample_frozen") is False,
        "diagnostics became normative",
    )
    require(
        p.get("human_ratings_present") is False
        and p.get("score_promotion") == "prohibited"
        and p.get("publication_status") == "not-published",
        "governance boundary drift",
    )
    provenance = p.get("provenance", {})
    require(
        provenance.get("origin") == "project-original-deterministic-svg-generator"
        and provenance.get("external_source_material") is False
        and provenance.get("rights_status") == "project-original",
        "diagnostic provenance boundary drift",
    )
    for path_key, hash_key in (
        ("generator", "generator_source_sha256"),
        ("candidate_generator", "candidate_generator_source_sha256"),
    ):
        source = ROOT / str(provenance.get(path_key, ""))
        require(source.is_file(), f"missing provenance dependency: {path_key}")
        require(
            hashlib.sha256(source.read_bytes()).hexdigest() == provenance.get(hash_key),
            f"provenance dependency drift: {path_key}",
        )
    rows = p.get("episodes", [])
    require(len(rows) == p.get("episode_count") == 40, "need 40 diagnostics")
    require(len({r.get("diagnostic_id") for r in rows}) == 40, "duplicate diagnostic ID")
    require(len({r.get("artifact") for r in rows}) == 40, "duplicate diagnostic path")
    require(
        Counter(r.get("diagnostic_class") for r in rows) == dict.fromkeys(CLASSES, 8),
        "diagnostic class balance drift",
    )
    require(
        len({r.get("defect_family") for r in rows}) == p.get("defect_family_count") == 8,
        "need eight families",
    )
    for family in {r["defect_family"] for r in rows}:
        require(
            {r["diagnostic_class"] for r in rows if r["defect_family"] == family} == CLASSES,
            f"missing diagnostic class: {family}",
        )
    candidate = json.loads((ROOT / "benchmark/fixtures/repair/candidate/manifest.json").read_text())
    candidate_bytes = {
        digest
        for row in candidate["episodes"]
        for digest in (row["before_sha256"], row["after_sha256"])
    }
    candidate_renders = {
        digest
        for row in candidate["episodes"]
        for digest in (row["before_render_sha256"], row["after_render_sha256"])
    }
    diagnostic_bytes: set[str] = set()
    diagnostic_renders: set[str] = set()
    for r in rows:
        require(
            r.get("normative_eligible") is False
            and r.get("status") == "diagnostic-development-only"
            and r.get("project_original") is True,
            "diagnostic row became normative",
        )
        raw = resolve(Path(r["artifact"])).read_bytes()
        require(
            hashlib.sha256(raw).hexdigest() == r.get("artifact_sha256"),
            "diagnostic byte commitment mismatch",
        )
        svg = raw.decode()
        inspection = inspect_svg(svg)
        require(inspection.valid, "unsafe diagnostic SVG")
        require(
            render_svg(svg, inspection=inspection).render_hash == r.get("artifact_render_sha256"),
            "diagnostic render commitment mismatch",
        )
        require(
            r.get("expected_validity") == (r.get("diagnostic_class") != "invalid"),
            "expected validity drift",
        )
        roles = {
            token
            for element in ET.fromstring(svg).iter()
            for token in element.attrib.get("data-role", "").split()
        }
        kind = str(r.get("diagnostic_class"))
        require(f"diagnostic-{kind}" in roles, f"missing class predicate: {kind}")
        if kind == "over-edit":
            require("unrelated-over-edit" in roles, "over-edit lacks unrelated geometry")
        elif kind == "introduced-defect":
            require(not ({"eye", "wing"} <= roles), "introduced defect is absent")
        elif kind == "invalid":
            require("animal" not in roles and "frame" not in roles, "invalid artifact is semantic")
        elif kind == "under-repair":
            require(
                "residual-defect" in roles,
                "under-repair has no residual defect",
            )
        byte_hash = str(r["artifact_sha256"])
        render_hash = str(r["artifact_render_sha256"])
        require(byte_hash not in candidate_bytes, "diagnostic byte overlaps candidate")
        require(render_hash not in candidate_renders, "diagnostic render overlaps candidate")
        require(byte_hash not in diagnostic_bytes, "duplicate diagnostic bytes")
        require(render_hash not in diagnostic_renders, "duplicate diagnostic render")
        diagnostic_bytes.add(byte_hash)
        diagnostic_renders.add(render_hash)
    print("T14 diagnostic package valid: 40 separate non-normative cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
