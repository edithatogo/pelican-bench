"""Synthetic exact-formula equivalence and deterministic mean-work accounting."""

from collections import defaultdict
from statistics import mean

import pytest

from pelicanbench import longitudinal
from pelicanbench.models import HistoricalObservation

pytestmark = pytest.mark.contract


def observation(index, annotations, date=None):
    return HistoricalObservation(
        observation_id=f"synthetic:{index}",
        source_id="project-original-toy",
        observed_at=date,
        annotations=annotations,
    )


def historical_formula(observations):
    metrics = defaultdict(list)
    for item in sorted(observations, key=lambda item: item.observed_at or ""):
        for key, value in item.annotations.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[key].append(float(value))
    output = []
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
        output.append(
            longitudinal.Trend(metric, len(series), series[0], series[-1], slope, mean(series))
        )
    return output


@pytest.mark.parametrize(
    "values", [[], [3.25], [0.1, 0.2, 0.3], [1e16, 1.0, -1e16], [-4, -4, -4], [0, 1, 8, 27]]
)
def test_exact_historical_formula(values):
    items = [observation(index, {"metric": value}) for index, value in enumerate(values)]
    assert longitudinal.metric_trends(iter(items)) == historical_formula(items)


def test_out_of_order_multiple_metrics_missing_dates_and_stable_ties():
    items = [
        observation(0, {"z": 7, "a": 0.1, "flag": True}, "2026-03-01"),
        observation(1, {"a": 0.2, "text": "7"}),
        observation(2, {"z": -3, "a": 0.7}, "2026-01-01"),
        observation(3, {"a": 0.9, "singleton": 4}, "2026-01-01"),
        observation(4, {"ignored": None}),
    ]
    actual = longitudinal.metric_trends(items)
    assert actual == historical_formula(items)
    assert [row.metric for row in actual] == ["a", "singleton", "z"]
    assert actual[0].first == 0.2 and actual[0].last == 0.1


@pytest.mark.parametrize("size", [1, 8, 64, 256])
def test_mean_work_is_linear_in_values_not_quadratic(monkeypatch, size):
    calls = []

    def counted_mean(values):
        calls.append(len(values))
        return mean(values)

    monkeypatch.setattr(longitudinal, "mean", counted_mean)
    items = [observation(index, {"a": index, "b": index / 3}) for index in range(size)]
    longitudinal.metric_trends(items)
    assert calls == [size, size]
    assert sum(calls) == 2 * size


def test_empty_input_never_computes_mean(monkeypatch):
    def unexpected_mean(_values):
        raise AssertionError("no numeric observations")

    monkeypatch.setattr(longitudinal, "mean", unexpected_mean)
    assert longitudinal.metric_trends([]) == []
    assert longitudinal.metric_trends([observation(0, {"flag": False})]) == []
