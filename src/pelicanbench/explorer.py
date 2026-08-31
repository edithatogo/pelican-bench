"""Offline scorecard callback shared by the optional public explorer UI."""

from __future__ import annotations

import json

from .scoring import score_svg
from .taskgen import heritage_task


def evaluate(svg: str) -> tuple[str, str]:
    """Return the existing structural scorecard without starting a UI or service.

    The scorer retains its SVG preflight/resource limits. This supplies no
    semantic assessment and cannot imply human-calibrated benchmark success.
    """
    if not isinstance(svg, str):
        raise TypeError("SVG source must be text")
    card = score_svg(heritage_task(), svg, submission_id="interactive")
    summary = f"Aggregate: {card.aggregate:.3f} | Critical success: {card.valid}"
    return summary, json.dumps(card.model_dump(mode="json"), indent=2)
