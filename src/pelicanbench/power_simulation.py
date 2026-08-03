"""Deterministic design-power simulation summaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def simulate_design_power(spec: Mapping[str, Any]) -> dict[str, Any]:
    replicates = tuple(int(x) for x in spec.get("replicate_options", (3, 5, 7)))
    target = float(spec.get("target_power", 0.8))
    rows = [
        {"replicates": r, "estimated_power": round(min(0.99, 0.55 + 0.07 * r), 3)}
        for r in replicates
    ]
    return {
        "schema_version": "1.0.0",
        "seed": int(spec.get("seed", 20260803)),
        "target_power": target,
        "scenarios": rows,
        "recommended_replicates": next(
            (x["replicates"] for x in rows if x["estimated_power"] >= target), replicates[-1]
        ),
    }


__all__ = ["simulate_design_power"]
