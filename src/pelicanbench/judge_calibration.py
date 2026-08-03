"""Fail-closed evaluation of judge-panel calibration observations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def evaluate_judge_panel(
    observations: Iterable[Mapping[str, Any]],
    policy: Mapping[str, Any],
    *,
    require_empirical: bool = False,
) -> dict[str, Any]:
    """Evaluate technical and empirical gates without upgrading fixture evidence."""
    rows = tuple(dict(row) for row in observations)
    if not rows:
        raise ValueError("judge calibration observations cannot be empty")
    by_judge: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_judge[str(row["judge_id"])].append(row)
    minimum = float(policy["minimum_human_agreement"])
    judges = []
    for judge_id in sorted(by_judge):
        values = by_judge[judge_id]
        agreement = sum(float(row["human_agreement"]) for row in values) / len(values)
        technical = all(
            bool(row[key])
            for row in values
            for key in ("schema_valid", "output_complete", "source_independent", "task_correct")
        ) and not any(bool(row["prompt_leakage"]) for row in values)
        empirical = agreement >= minimum
        judges.append(
            {
                "judge_id": judge_id,
                "observations": len(values),
                "mean_human_agreement": round(agreement, 6),
                "technical_gates_passed": technical,
                "empirical_gate_passed": empirical,
                "qualified": technical and (empirical if require_empirical else True),
            }
        )
    return {
        "schema_version": "1.0.0",
        "observation_count": len(rows),
        "require_empirical": require_empirical,
        "judges": judges,
        "panel_technically_qualified": all(item["technical_gates_passed"] for item in judges),
        "panel_empirically_qualified": all(item["empirical_gate_passed"] for item in judges),
        "panel_qualified": all(item["qualified"] for item in judges),
    }


__all__ = ["evaluate_judge_panel"]
