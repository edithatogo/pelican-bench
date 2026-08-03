"""Transparent precision and workload checks for the prospective study design.

This module does not manufacture empirical power from fixture data. It exposes the
assumptions under which the committed model and human-calibration designs are likely to
detect practically relevant differences. All calculations use standard closed-form
approximations or exact binomial sums and remain dependency-free and deterministic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from math import ceil, comb, sqrt
from statistics import NormalDist
from typing import Any


@dataclass(frozen=True, slots=True)
class PrecisionScenario:
    intraclass_correlation: float
    design_effect: float
    effective_n_per_model: float
    minimum_detectable_difference: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReplicationScenario:
    replicates: int
    trials_per_model: int
    worst_case_effective_n: float
    worst_case_minimum_detectable_difference: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DesignAssuranceReport:
    schema_version: str
    candidate_release: str
    confirmatory_tasks: int
    core_models: int
    replicates: int
    trials_per_model: int
    precision_scenarios: tuple[PrecisionScenario, ...]
    replication_sensitivity: tuple[ReplicationScenario, ...]
    recommended_replicates_for_target: int | None
    blinded_reassessment_required: bool
    human_target_artifacts: int
    public_ratings_per_artifact: int
    artifact_level_wilson_half_width: float
    rating_level_wilson_half_width: float
    duplicate_assignments: int
    pairwise_majority_power: dict[str, dict[str, float]]
    rater_reliability_requirements: dict[str, int]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["precision_scenarios"] = [item.as_dict() for item in self.precision_scenarios]
        value["replication_sensitivity"] = [item.as_dict() for item in self.replication_sensitivity]
        value["warnings"] = list(self.warnings)
        return value


def _z(confidence: float) -> float:
    if not 0 < confidence < 1:
        raise ValueError("confidence must be within (0,1)")
    return NormalDist().inv_cdf(0.5 + confidence / 2)


def wilson_interval(successes: int, total: int, *, confidence: float = 0.95) -> tuple[float, float]:
    if total < 1:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    z = _z(confidence)
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z * sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    )
    return max(0.0, centre - radius), min(1.0, centre + radius)


def worst_case_wilson_half_width(total: int, *, confidence: float = 0.95) -> float:
    lower, upper = wilson_interval(total // 2, total, confidence=confidence)
    return (upper - lower) / 2


def cluster_design_effect(cluster_size: int, intraclass_correlation: float) -> float:
    if cluster_size < 1:
        raise ValueError("cluster_size must be positive")
    if not 0 <= intraclass_correlation <= 1:
        raise ValueError("intraclass_correlation must be within [0,1]")
    return 1 + (cluster_size - 1) * intraclass_correlation


def effective_sample_size(total: int, *, cluster_size: int, intraclass_correlation: float) -> float:
    if total < 1:
        raise ValueError("total must be positive")
    return total / cluster_design_effect(cluster_size, intraclass_correlation)


def approximate_mde_two_proportions(
    n_per_group: float,
    *,
    baseline: float = 0.5,
    confidence: float = 0.95,
    power: float = 0.8,
) -> float:
    """Conservative normal-approximation MDE for two equally sized groups."""

    if n_per_group <= 0:
        raise ValueError("n_per_group must be positive")
    if not 0 < baseline < 1:
        raise ValueError("baseline must be within (0,1)")
    if not 0 < power < 1:
        raise ValueError("power must be within (0,1)")
    z_alpha = _z(confidence)
    z_power = NormalDist().inv_cdf(power)
    standard_error = sqrt(2 * baseline * (1 - baseline) / n_per_group)
    return min(1.0, (z_alpha + z_power) * standard_error)


def pairwise_majority_probability(votes: int, *, better_choice_probability: float) -> float:
    if votes < 1:
        raise ValueError("votes must be positive")
    if not 0 <= better_choice_probability <= 1:
        raise ValueError("better_choice_probability must be within [0,1]")
    probability = 0.0
    threshold = votes // 2 + 1
    for successes in range(threshold, votes + 1):
        probability += (
            comb(votes, successes)
            * better_choice_probability**successes
            * (1 - better_choice_probability) ** (votes - successes)
        )
    if votes % 2 == 0:
        ties = comb(votes, votes // 2) * (
            better_choice_probability ** (votes // 2)
            * (1 - better_choice_probability) ** (votes // 2)
        )
        probability += 0.5 * ties
    return probability


def spearman_brown_required_raters(
    single_rater_reliability: float,
    *,
    target_reliability: float = 0.8,
) -> int:
    if not 0 < single_rater_reliability < 1:
        raise ValueError("single_rater_reliability must be within (0,1)")
    if not single_rater_reliability < target_reliability < 1:
        raise ValueError("target reliability must exceed single-rater reliability and be below one")
    required = (
        target_reliability
        * (1 - single_rater_reliability)
        / (single_rater_reliability * (1 - target_reliability))
    )
    return max(1, ceil(required - 1e-12))


def _cohort_models(panel: Mapping[str, Any], cohort_id: str) -> tuple[str, ...]:
    for cohort in panel["cohorts"]:
        if str(cohort["cohort_id"]) == cohort_id:
            return tuple(str(item) for item in cohort["models"])
    raise ValueError(f"unknown cohort: {cohort_id}")


def build_design_assurance_report(
    tasks: Iterable[Mapping[str, Any]],
    model_panel: Mapping[str, Any],
    human_spec: Mapping[str, Any],
    assumptions: Mapping[str, Any],
) -> DesignAssuranceReport:
    task_values = tuple(tasks)
    panel_id = str(assumptions["confirmatory_panel_id"])
    confirmatory = [
        item for item in task_values if str(item.get("metadata", {}).get("panel_id")) == panel_id
    ]
    if not confirmatory:
        raise ValueError("confirmatory panel is empty")
    cohort_id = str(assumptions["core_cohort_id"])
    core_models = _cohort_models(model_panel, cohort_id)
    replicates = int(assumptions["replicates"])
    if replicates < 1:
        raise ValueError("replicates must be positive")
    trials_per_model = len(confirmatory) * replicates
    baseline = float(assumptions["binary_baseline"])
    confidence = float(assumptions["confidence"])
    power = float(assumptions["power"])

    precision: list[PrecisionScenario] = []
    correlations = tuple(float(item) for item in assumptions["intraclass_correlations"])
    for icc in correlations:
        design_effect = cluster_design_effect(replicates, icc)
        effective = effective_sample_size(
            trials_per_model,
            cluster_size=replicates,
            intraclass_correlation=icc,
        )
        precision.append(
            PrecisionScenario(
                intraclass_correlation=icc,
                design_effect=design_effect,
                effective_n_per_model=round(effective, 3),
                minimum_detectable_difference=round(
                    approximate_mde_two_proportions(
                        effective,
                        baseline=baseline,
                        confidence=confidence,
                        power=power,
                    ),
                    4,
                ),
            )
        )

    replication_sensitivity: list[ReplicationScenario] = []
    for option in sorted(
        {int(item) for item in assumptions.get("replicate_options", [replicates])}
    ):
        if option < replicates:
            raise ValueError("replicate options cannot be below the initial replicate count")
        option_trials = len(confirmatory) * option
        worst_icc = max(correlations)
        effective = effective_sample_size(
            option_trials,
            cluster_size=option,
            intraclass_correlation=worst_icc,
        )
        replication_sensitivity.append(
            ReplicationScenario(
                replicates=option,
                trials_per_model=option_trials,
                worst_case_effective_n=round(effective, 3),
                worst_case_minimum_detectable_difference=round(
                    approximate_mde_two_proportions(
                        effective,
                        baseline=baseline,
                        confidence=confidence,
                        power=power,
                    ),
                    4,
                ),
            )
        )

    target_artifacts = int(human_spec["target_artifacts"])
    public_panel = next(item for item in human_spec["panels"] if str(item["panel_id"]) == "public")
    public_ratings = int(public_panel["ratings_per_artifact"])
    duplicate_fraction = float(human_spec["duplicate_fraction"])
    pairwise = {
        str(votes): {
            f"p={probability:.2f}": round(
                pairwise_majority_probability(
                    int(votes),
                    better_choice_probability=float(probability),
                ),
                4,
            )
            for probability in assumptions["pairwise_choice_probabilities"]
        }
        for votes in assumptions["pairwise_vote_counts"]
    }
    reliability = {
        f"single={single:.2f}": spearman_brown_required_raters(
            float(single),
            target_reliability=float(assumptions["target_rater_reliability"]),
        )
        for single in assumptions["single_rater_reliabilities"]
    }

    warnings: list[str] = []
    if replicates < 5:
        warnings.append(
            "three replicates support denominator retention and variance estimation "
            "but provide limited within-cell precision"
        )
    worst_mde = max(item.minimum_detectable_difference for item in precision)
    desired_mde = float(assumptions["maximum_desired_mde"])
    recommended_replicates = next(
        (
            item.replicates
            for item in replication_sensitivity
            if item.worst_case_minimum_detectable_difference <= desired_mde
        ),
        None,
    )
    blinded_reassessment = recommended_replicates is None or recommended_replicates > replicates
    if worst_mde > desired_mde:
        warnings.append(
            "under the highest prespecified clustering assumption, the design may miss smaller model differences"
        )
    if blinded_reassessment:
        warnings.append(
            "retain three initial replicates, then apply the prespecified blinded "
            "pooled-variance reassessment before adding replicate waves"
        )
    artifact_margin = worst_case_wilson_half_width(target_artifacts, confidence=confidence)
    if artifact_margin > float(assumptions["maximum_artifact_margin"]):
        warnings.append(
            "artifact-level human calibration precision is wider than the preferred margin"
        )

    return DesignAssuranceReport(
        schema_version="1.0.0",
        candidate_release=str(assumptions["candidate_release"]),
        confirmatory_tasks=len(confirmatory),
        core_models=len(core_models),
        replicates=replicates,
        trials_per_model=trials_per_model,
        precision_scenarios=tuple(precision),
        replication_sensitivity=tuple(replication_sensitivity),
        recommended_replicates_for_target=recommended_replicates,
        blinded_reassessment_required=blinded_reassessment,
        human_target_artifacts=target_artifacts,
        public_ratings_per_artifact=public_ratings,
        artifact_level_wilson_half_width=round(artifact_margin, 4),
        rating_level_wilson_half_width=round(
            worst_case_wilson_half_width(
                target_artifacts * public_ratings,
                confidence=confidence,
            ),
            4,
        ),
        duplicate_assignments=ceil(target_artifacts * public_ratings * duplicate_fraction),
        pairwise_majority_power=pairwise,
        rater_reliability_requirements=reliability,
        warnings=tuple(warnings),
    )


__all__ = [
    "DesignAssuranceReport",
    "PrecisionScenario",
    "ReplicationScenario",
    "approximate_mde_two_proportions",
    "build_design_assurance_report",
    "cluster_design_effect",
    "effective_sample_size",
    "pairwise_majority_probability",
    "spearman_brown_required_raters",
    "wilson_interval",
    "worst_case_wilson_half_width",
]
