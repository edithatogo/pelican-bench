"""Metrics for agentic drawing trajectories and governed skill acquisition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from .models import TrajectoryEvent


@dataclass(frozen=True, slots=True)
class TrajectoryMetrics:
    steps: int
    scored_steps: int
    initial_score: float | None
    final_score: float | None
    best_score: float | None
    improvement: float | None
    area_under_curve: float | None
    regressions: int
    recoveries: int
    repeated_state_fraction: float
    error_rate: float


def evaluate_trajectory(events: Iterable[TrajectoryEvent]) -> TrajectoryMetrics:
    values = list(events)
    scores = [event.score for event in values if event.score is not None]
    regressions = 0
    recoveries = 0
    previous: float | None = None
    best = float("-inf")
    was_below_best = False
    for score in scores:
        assert score is not None
        if previous is not None and score < previous:
            regressions += 1
        if score < best:
            was_below_best = True
        elif was_below_best and score >= best:
            recoveries += 1
            was_below_best = False
        best = max(best, score)
        previous = score
    state_hashes = [event.state_hash for event in values]
    repeated = len(state_hashes) - len(set(state_hashes))
    initial = scores[0] if scores else None
    final = scores[-1] if scores else None
    return TrajectoryMetrics(
        steps=len(values),
        scored_steps=len(scores),
        initial_score=initial,
        final_score=final,
        best_score=max(scores) if scores else None,
        improvement=(final - initial) if final is not None and initial is not None else None,
        area_under_curve=mean(scores) if scores else None,
        regressions=regressions,
        recoveries=recoveries,
        repeated_state_fraction=repeated / max(1, len(state_hashes)),
        error_rate=sum(event.error is not None for event in values) / max(1, len(values)),
    )


def trajectory_utility(
    metrics: TrajectoryMetrics,
    *,
    cost: float = 0.0,
    alpha_improvement: float = 0.5,
    beta_cost: float = 0.01,
    gamma_regression: float = 0.02,
) -> float:
    auc = metrics.area_under_curve or 0.0
    improvement = metrics.improvement or 0.0
    return (
        auc
        + alpha_improvement * improvement
        - beta_cost * cost
        - gamma_regression * metrics.regressions
    )
