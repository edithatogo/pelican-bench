"""Benchmark, judge, and score-distribution drift checks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import log
from statistics import mean


@dataclass(frozen=True, slots=True)
class DriftReport:
    baseline_mean: float
    candidate_mean: float
    mean_shift: float
    population_stability_index: float
    maximum_bin_shift: float
    action: str


def _histogram(values: list[float], bins: int) -> list[float]:
    counts = [0 for _ in range(bins)]
    for value in values:
        index = min(bins - 1, max(0, int(value * bins)))
        counts[index] += 1
    return [count / max(1, len(values)) for count in counts]


def compare_distributions(
    baseline: Iterable[float],
    candidate: Iterable[float],
    *,
    bins: int = 10,
    warn_threshold: float = 0.1,
    bridge_threshold: float = 0.25,
) -> DriftReport:
    first = list(baseline)
    second = list(candidate)
    if not first or not second:
        raise ValueError("both distributions are required")
    if any(not 0 <= value <= 1 for value in first + second):
        raise ValueError("scores must be within [0,1]")
    first_hist = _histogram(first, bins)
    second_hist = _histogram(second, bins)
    epsilon = 1e-6
    psi = sum(
        (candidate_bin - baseline_bin) * log((candidate_bin + epsilon) / (baseline_bin + epsilon))
        for baseline_bin, candidate_bin in zip(first_hist, second_hist, strict=True)
    )
    maximum_shift = max(abs(a - b) for a, b in zip(first_hist, second_hist, strict=True))
    action = "none"
    if psi >= bridge_threshold:
        action = "new-major-release-and-bridge-study"
    elif psi >= warn_threshold:
        action = "investigate-and-recalibrate"
    return DriftReport(
        baseline_mean=mean(first),
        candidate_mean=mean(second),
        mean_shift=mean(second) - mean(first),
        population_stability_index=psi,
        maximum_bin_shift=maximum_shift,
        action=action,
    )
