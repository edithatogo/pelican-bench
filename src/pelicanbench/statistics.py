"""Factorial analyses, uncertainty, and a Pelicanmaxxing interaction index."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Observation:
    model_id: str
    animal: str
    mobile_object: str
    score: float
    replicate: int = 1
    prompt_version: str = "v1"
    judge_id: str = "structural"

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be within [0,1]")


@dataclass(frozen=True, slots=True)
class InteractionEstimate:
    model_id: str
    animal: str
    mobile_object: str
    observed: float
    expected: float
    interaction: float
    standard_error: float
    ci_low: float
    ci_high: float
    replicates: int


def _expected_additive(rows: list[Observation], animal: str, mobile_object: str) -> float:
    grand = mean(row.score for row in rows)
    animal_rows = [row.score for row in rows if row.animal == animal]
    object_rows = [row.score for row in rows if row.mobile_object == mobile_object]
    if not animal_rows or not object_rows:
        raise ValueError("target animal and mobile object require marginal observations")
    expected = mean(animal_rows) + mean(object_rows) - grand
    return min(1.0, max(0.0, expected))


def estimate_interaction(
    observations: Iterable[Observation],
    *,
    animal: str = "pelican",
    mobile_object: str = "bicycle",
    bootstrap_samples: int = 1_000,
    seed: int = 0,
) -> list[InteractionEstimate]:
    values = list(observations)
    model_ids = sorted({row.model_id for row in values})
    output: list[InteractionEstimate] = []
    rng = random.Random(seed)
    for model_id in model_ids:
        rows = [row for row in values if row.model_id == model_id]
        target = [
            row.score
            for row in rows
            if row.animal == animal and row.mobile_object == mobile_object
        ]
        if not target:
            continue
        observed = mean(target)
        expected = _expected_additive(rows, animal, mobile_object)
        interaction = observed - expected
        bootstraps: list[float] = []
        for _ in range(max(0, bootstrap_samples)):
            sampled = [rows[rng.randrange(len(rows))] for _ in rows]
            sampled_target = [
                row.score
                for row in sampled
                if row.animal == animal and row.mobile_object == mobile_object
            ]
            try:
                if sampled_target:
                    bootstraps.append(
                        mean(sampled_target) - _expected_additive(sampled, animal, mobile_object)
                    )
            except ValueError:
                continue
        bootstraps.sort()
        if bootstraps:
            low_index = int(0.025 * (len(bootstraps) - 1))
            high_index = int(0.975 * (len(bootstraps) - 1))
            standard_error = pstdev(bootstraps)
            ci_low = bootstraps[low_index]
            ci_high = bootstraps[high_index]
        else:
            standard_error = 0.0
            ci_low = interaction
            ci_high = interaction
        output.append(
            InteractionEstimate(
                model_id=model_id,
                animal=animal,
                mobile_object=mobile_object,
                observed=observed,
                expected=expected,
                interaction=interaction,
                standard_error=standard_error,
                ci_low=ci_low,
                ci_high=ci_high,
                replicates=len(target),
            )
        )
    return output


def rank_with_uncertainty(estimates: Iterable[InteractionEstimate]) -> list[InteractionEstimate]:
    return sorted(
        estimates,
        key=lambda item: (item.interaction, -item.standard_error),
        reverse=True,
    )
