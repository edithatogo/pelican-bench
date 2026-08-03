"""Longitudinal summaries of historical model outputs and commentary."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from .models import HistoricalObservation


@dataclass(frozen=True, slots=True)
class Trend:
    metric: str
    count: int
    first: float
    last: float
    slope_per_observation: float
    mean: float


def _numeric_annotations(observation: HistoricalObservation) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in observation.annotations.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def metric_trends(observations: Iterable[HistoricalObservation]) -> list[Trend]:
    values = list(observations)
    values.sort(key=lambda item: item.observed_at or "")
    metrics: dict[str, list[float]] = defaultdict(list)
    for observation in values:
        for key, value in _numeric_annotations(observation).items():
            metrics[key].append(value)
    output: list[Trend] = []
    for metric, series in sorted(metrics.items()):
        if len(series) < 2:
            slope = 0.0
        else:
            x_mean = (len(series) - 1) / 2
            denominator = sum((index - x_mean) ** 2 for index in range(len(series)))
            slope = (
                sum((index - x_mean) * (value - mean(series)) for index, value in enumerate(series))
                / denominator
                if denominator
                else 0.0
            )
        output.append(Trend(metric, len(series), series[0], series[-1], slope, mean(series)))
    return output


def timeline_summary(observations: Iterable[HistoricalObservation]) -> dict[str, Any]:
    values = list(observations)
    models = Counter(item.model_id or "unknown" for item in values)
    rights = Counter(item.rights_status for item in values)
    dated = [
        datetime.fromisoformat(item.observed_at.replace("Z", "+00:00"))
        for item in values
        if item.observed_at
    ]
    return {
        "observations": len(values),
        "models": dict(sorted(models.items())),
        "rights_statuses": dict(sorted(rights.items())),
        "first_observation": min(dated).isoformat() if dated else None,
        "last_observation": max(dated).isoformat() if dated else None,
        "metrics": [asdict(trend) for trend in metric_trends(values)],
    }
