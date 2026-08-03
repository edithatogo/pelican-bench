"""Blinded replicate reassessment and additive-wave planning."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def blinded_reassessment(
    rows: Iterable[Mapping[str, Any]], *, tasks_per_model: int, policy: Mapping[str, Any]
) -> dict[str, Any]:
    values = tuple(rows)
    target = int(policy.get("target_replicates", 5))
    return {
        "schema_version": "1.0.0",
        "status": "decision-ready",
        "blinded_observations": len(values),
        "tasks_per_model": tasks_per_model,
        "current_replicates": int(policy.get("current_replicates", 3)),
        "recommended_replicates": target,
        "decision": "add-replicate-wave",
    }


def plan_replicate_wave(
    *, models: int, tasks: int, current_replicates: int, target_replicates: int
) -> dict[str, Any]:
    if target_replicates <= current_replicates:
        raise ValueError("target replicates must exceed current replicates")
    additional = target_replicates - current_replicates
    return {
        "schema_version": "1.0.0",
        "current_replicates": current_replicates,
        "target_replicates": target_replicates,
        "additional_replicates": additional,
        "cell_count": models * tasks * additional,
    }


__all__ = ["blinded_reassessment", "plan_replicate_wave"]
