#!/usr/bin/env python3
"""Create a non-promotional receipt for the bounded two-episode T14 rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE = ROOT / "benchmark/evidence/snapshots/t14-human-rating-response.json"
DEFAULT_OUTPUT = ROOT / "benchmark/evidence/snapshots/t14-steward-analysis.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_response_hash(payload: dict) -> str:
    unsigned = dict(payload)
    unsigned.pop("response_sha256", None)
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", type=Path, default=DEFAULT_RESPONSE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    # Homebrew's Cairo may be installed but not linked into the process search path.
    # Add the standard Apple Silicon prefix before importing cairocffi/CairoSVG.
    cairo_lib = Path("/opt/homebrew/opt/cairo/lib")
    if cairo_lib.is_dir():
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = f"{cairo_lib}:{existing}" if existing else str(cairo_lib)
    try:
        from pelicanbench.repair import score_repair_render

        render_error = None
    except (ImportError, OSError) as exc:
        score_repair_render = None
        render_error = f"render runtime unavailable: {exc}"
    response = json.loads(args.response.read_text(encoding="utf-8"))
    if response.get("response_sha256") != canonical_response_hash(response):
        raise ValueError("response_sha256 does not match the canonical response payload")
    manifest_path = ROOT / response["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if response.get("manifest_sha256") != digest(manifest_path):
        raise ValueError("response manifest_sha256 does not match the frozen manifest")
    tasks = {
        row["repair_id"]: row
        for row in json.loads(
            (ROOT / "benchmark/fixtures/repair/tasks.json").read_text(encoding="utf-8")
        )
    }
    rows = []
    for rating in response["responses"]:
        task = tasks[rating["episode_id"]]
        before = (ROOT / task["before"]).read_text(encoding="utf-8")
        after = (ROOT / task["after_reference"]).read_text(encoding="utf-8")
        metric = (
            score_repair_render(before, after, size=manifest["canvas_size"])
            if score_repair_render
            else None
        )
        rows.append(
            {
                "episode_id": rating["episode_id"],
                "human": {
                    key: rating[key]
                    for key in (
                        "target_corrected",
                        "preservation_score_1_to_5",
                        "introduced_defect",
                        "confidence_0_to_100",
                        "uncertain",
                        "repeat_observation",
                    )
                },
                "automatic_render_metrics": None
                if metric is None
                else {
                    "diff_pixel_fraction": metric.diff_pixel_fraction,
                    "foreground_retention_fraction": metric.foreground_retention_fraction,
                    "added_ink_fraction": metric.added_ink_fraction,
                    "edit_locality": metric.edit_locality,
                    "introduced_components": metric.introduced_components,
                },
            }
        )
    output = {
        "schema_version": "1.0.0",
        "study_id": response["study_id"],
        "status": "rehearsal-only-insufficient-sample",
        "created_at": datetime.now(UTC).isoformat(),
        "manifest_sha256": response["manifest_sha256"],
        "response_sha256": response["response_sha256"],
        "response_file_sha256": digest(args.response),
        "episode_count": len(rows),
        "rows": rows,
        "claims": {
            "human_calibration_complete": False,
            "e3_calibration": False,
            "score_compatibility": "none-until-normative-release",
        },
        "automatic_metrics_status": "unavailable-in-current-runtime"
        if render_error
        else "computed",
        "automatic_metrics_error": render_error,
        "limitations": [
            "Two development episodes are not the prespecified 72/24 development/held-out design.",
            "This receipt reports association only and does not establish metric validity or promotion.",
            "The ratings are steward responses, not agent ratings or independent review.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"T14 rehearsal analysis written: {args.output} ({len(rows)} episode(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
