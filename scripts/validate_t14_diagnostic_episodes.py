#!/usr/bin/env python3
"""Fail-closed validation for separate T14 diagnostics."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

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
    rows = p.get("episodes", [])
    require(len(rows) == p.get("episode_count") == 40, "need 40 diagnostics")
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
    for r in rows:
        require(
            r.get("normative_eligible") is False
            and r.get("status") == "diagnostic-development-only",
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
    print("T14 diagnostic package valid: 40 separate non-normative cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
