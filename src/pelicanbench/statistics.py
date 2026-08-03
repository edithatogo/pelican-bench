"""Factorial analyses, clustered uncertainty and a Pelicanmaxxing interaction index."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, pstdev, pvariance


@dataclass(frozen=True, slots=True)
class Observation:
    model_id: str
    animal: str
    mobile_object: str
    score: float
    relation: str = "rides_on"
    interface_class: str = ""
    scenario_id: str = ""
    prompt_id: str = ""
    condition_id: str = ""
    trial_id: str = ""
    replicate: int = 1
    prompt_version: str = "v1"
    judge_id: str = "structural"
    rater_id: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be within [0,1]")

    @property
    def cluster_id(self) -> str:
        if self.scenario_id:
            return self.scenario_id
        return "|".join(
            (
                self.animal,
                self.mobile_object,
                self.relation,
                self.prompt_version,
            )
        )

    @property
    def cell_id(self) -> tuple[str, str, str, str, str]:
        return (
            self.animal,
            self.mobile_object,
            self.relation,
            self.prompt_version,
            self.judge_id,
        )


@dataclass(frozen=True, slots=True)
class InteractionEstimate:
    model_id: str
    animal: str
    mobile_object: str
    relation: str
    observed: float
    expected: float
    interaction: float
    standard_error: float
    ci_low: float
    ci_high: float
    replicates: int
    bootstrap_unit: str = "stratified-cell"


@dataclass(frozen=True, slots=True)
class ShrunkInteractionEstimate:
    model_id: str
    raw_interaction: float
    shrunk_interaction: float
    pooled_interaction: float
    shrinkage_weight: float
    between_model_variance: float


@dataclass(frozen=True, slots=True)
class ReliabilitySummary:
    cells: int
    observations: int
    mean_replicates: float
    within_cell_variance: float
    between_cell_variance: float
    reliability: float


def _expected_additive(
    rows: list[Observation],
    animal: str,
    mobile_object: str,
    relation: str,
) -> float:
    grand = mean(row.score for row in rows)
    animal_rows = [row.score for row in rows if row.animal == animal]
    object_rows = [row.score for row in rows if row.mobile_object == mobile_object]
    relation_rows = [row.score for row in rows if row.relation == relation]
    if not animal_rows or not object_rows or not relation_rows:
        raise ValueError("target animal, mobile object and relation require marginal observations")
    expected = mean(animal_rows) + mean(object_rows) + mean(relation_rows) - 2 * grand
    return min(1.0, max(0.0, expected))


def _stratified_resample(rows: list[Observation], rng: random.Random) -> list[Observation]:
    """Resample trials within each semantic/prompt/judge cell.

    This preserves factorial margins while respecting that repeated samples of one task
    are not independent benchmark items.  A later empirical study can add a second
    scenario-level bootstrap when multiple scenarios exist in every factor cell.
    """

    cells: dict[tuple[str, str, str, str, str], list[Observation]] = {}
    for row in rows:
        cells.setdefault(row.cell_id, []).append(row)
    sampled: list[Observation] = []
    for cell_rows in cells.values():
        sampled.extend(cell_rows[rng.randrange(len(cell_rows))] for _ in cell_rows)
    return sampled


def estimate_interaction(
    observations: Iterable[Observation],
    *,
    animal: str = "pelican",
    mobile_object: str = "bicycle",
    relation: str = "rides_on",
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
            if row.animal == animal
            and row.mobile_object == mobile_object
            and row.relation == relation
        ]
        if not target:
            continue
        observed = mean(target)
        expected = _expected_additive(rows, animal, mobile_object, relation)
        interaction = observed - expected
        bootstraps: list[float] = []
        for _ in range(max(0, bootstrap_samples)):
            sampled = _stratified_resample(rows, rng)
            sampled_target = [
                row.score
                for row in sampled
                if row.animal == animal
                and row.mobile_object == mobile_object
                and row.relation == relation
            ]
            if not sampled_target:
                continue
            try:
                bootstraps.append(
                    mean(sampled_target)
                    - _expected_additive(sampled, animal, mobile_object, relation)
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
                relation=relation,
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


def hierarchical_shrink_interactions(
    estimates: Iterable[InteractionEstimate],
) -> list[ShrunkInteractionEstimate]:
    """Empirical-Bayes partial pooling of model-specific interaction effects."""

    values = list(estimates)
    if not values:
        return []
    variances = [max(item.standard_error**2, 1e-8) for item in values]
    fixed_weights = [1 / variance for variance in variances]
    fixed_mean = sum(
        weight * item.interaction for weight, item in zip(fixed_weights, values, strict=False)
    ) / sum(fixed_weights)
    q = sum(
        weight * (item.interaction - fixed_mean) ** 2
        for weight, item in zip(fixed_weights, values, strict=False)
    )
    c = sum(fixed_weights) - sum(weight**2 for weight in fixed_weights) / sum(fixed_weights)
    tau2 = max(0.0, (q - (len(values) - 1)) / c) if c > 0 and len(values) > 1 else 0.0
    random_weights = [1 / (variance + tau2) for variance in variances]
    pooled = sum(
        weight * item.interaction for weight, item in zip(random_weights, values, strict=False)
    ) / sum(random_weights)
    output: list[ShrunkInteractionEstimate] = []
    for item, variance in zip(values, variances, strict=False):
        weight = tau2 / (tau2 + variance) if tau2 > 0 else 0.0
        shrunk = weight * item.interaction + (1 - weight) * pooled
        output.append(
            ShrunkInteractionEstimate(
                model_id=item.model_id,
                raw_interaction=item.interaction,
                shrunk_interaction=shrunk,
                pooled_interaction=pooled,
                shrinkage_weight=weight,
                between_model_variance=tau2,
            )
        )
    return output


def replicate_reliability(observations: Iterable[Observation]) -> ReliabilitySummary:
    values = list(observations)
    if not values:
        raise ValueError("reliability requires observations")
    cells: dict[tuple[str, str, str, str, str, str], list[float]] = {}
    for row in values:
        key = (row.model_id, *row.cell_id)
        cells.setdefault(key, []).append(row.score)
    cell_means = [mean(scores) for scores in cells.values()]
    within_variances = [pvariance(scores) for scores in cells.values() if len(scores) > 1]
    within = mean(within_variances) if within_variances else 0.0
    between = pvariance(cell_means) if len(cell_means) > 1 else 0.0
    reliability = between / (between + within) if between + within > 0 else 1.0
    return ReliabilitySummary(
        cells=len(cells),
        observations=len(values),
        mean_replicates=mean(len(scores) for scores in cells.values()),
        within_cell_variance=within,
        between_cell_variance=between,
        reliability=min(1.0, max(0.0, reliability)),
    )


def superiority_probabilities(
    estimates: Iterable[InteractionEstimate],
) -> dict[tuple[str, str], float]:
    """Approximate pairwise superiority using independent normal uncertainty."""

    values = list(estimates)
    output: dict[tuple[str, str], float] = {}
    for left in values:
        for right in values:
            if left.model_id == right.model_id:
                continue
            difference = left.interaction - right.interaction
            standard_error = math.sqrt(left.standard_error**2 + right.standard_error**2)
            if standard_error <= 0:
                probability = 1.0 if difference > 0 else 0.0 if difference < 0 else 0.5
            else:
                z = difference / standard_error
                probability = 0.5 * (1 + math.erf(z / math.sqrt(2)))
            output[(left.model_id, right.model_id)] = probability
    return output


def rank_with_uncertainty(
    estimates: Iterable[InteractionEstimate],
) -> list[InteractionEstimate]:
    return sorted(
        estimates,
        key=lambda item: (item.interaction, -item.standard_error),
        reverse=True,
    )
