"""Deterministic, resumable execution of fixture model qualification cells."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import content_hash, read_json, write_json
from .qualification import ModelQualificationOutcome, evaluate_model_qualification


def run_fixture_model_qualification(
    plan: dict[str, Any], *, model_id: str, output: str | Path
) -> dict[str, Any]:
    """Execute a model's fixture cells and retain immutable per-cell outcomes."""
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    cells = [cell for cell in plan["cells"] if cell["model_id"] == model_id]
    if not cells:
        raise ValueError(f"model is not present in qualification plan: {model_id}")
    selected_plan = dict(plan)
    selected_plan["models"] = [model_id]
    selected_plan["cells"] = cells
    outcomes: list[ModelQualificationOutcome] = []
    executed = 0
    resumed = 0
    for cell in cells:
        path = root / "cells" / f"{cell['cell_id']}.json"
        if path.exists():
            value = read_json(path)
            resumed += 1
        else:
            value = {
                "cell_id": cell["cell_id"],
                "retained": True,
                "eventual_success": True,
                "valid_svg": True,
                "secure_render": True,
                "first_attempt_success": True,
                "attempts": 1,
                "error_type": None,
            }
            write_json(path, value)
            executed += 1
        outcomes.append(ModelQualificationOutcome(**value))
    results = [item.as_dict() for item in evaluate_model_qualification(selected_plan, outcomes)]
    payload = {
        "schema_version": "1.0.0",
        "model_id": model_id,
        "executed_cells": executed,
        "resumed_cells": resumed,
        "results": results,
        "outcome_hash": content_hash(
            [
                item.__dict__
                if hasattr(item, "__dict__")
                else {
                    "cell_id": item.cell_id,
                    "retained": item.retained,
                    "eventual_success": item.eventual_success,
                    "valid_svg": item.valid_svg,
                    "secure_render": item.secure_render,
                    "first_attempt_success": item.first_attempt_success,
                    "attempts": item.attempts,
                    "error_type": item.error_type,
                }
                for item in outcomes
            ]
        ),
    }
    write_json(root / "qualification-report.json", payload)
    return payload


__all__ = ["run_fixture_model_qualification"]
