"""Prespecified, dependency-aware statistics for the prospective T14 calibration."""

from __future__ import annotations

import itertools
import math
import random
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def auc(labels: Sequence[int], scores: Sequence[float]) -> float | None:
    """Return tie-aware binary AUC, or None when either class is absent."""
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must have the same non-zero length")
    positives = [score for label, score in zip(labels, scores, strict=True) if label == 1]
    negatives = [score for label, score in zip(labels, scores, strict=True) if label == 0]
    if len(positives) + len(negatives) != len(labels):
        raise ValueError("labels must be binary integers")
    if not positives or not negatives:
        return None
    wins = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return wins / (len(positives) * len(negatives))


def _ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for index in ordered[start:end]:
            ranks[index] = average
        start = end
    return ranks


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Return tie-aware Spearman correlation, or None for a constant margin."""
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("inputs must have the same length of at least two")
    x = _ranks(left)
    y = _ranks(right)
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    x_ss = sum((a - x_mean) ** 2 for a in x)
    y_ss = sum((b - y_mean) ** 2 for b in y)
    if x_ss == 0 or y_ss == 0:
        return None
    return numerator / math.sqrt(x_ss * y_ss)


def scene_cluster_bootstrap(
    rows: Sequence[Mapping[str, Any]],
    statistic: Callable[[Sequence[Mapping[str, Any]]], float | None],
    *,
    samples: int,
    seed: int,
    cluster_field: str = "scene_cluster",
    maximum_degenerate_fraction: float = 0.10,
    minimum_valid_fraction: float = 0.90,
) -> dict[str, Any]:
    """Bootstrap whole scenes and condition intervals on valid replicates."""
    if samples < 1:
        raise ValueError("samples must be positive")
    if not 0 <= maximum_degenerate_fraction <= 1:
        raise ValueError("maximum_degenerate_fraction must be within [0,1]")
    if not 0 <= minimum_valid_fraction <= 1:
        raise ValueError("minimum_valid_fraction must be within [0,1]")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[cluster_field])].append(row)
    clusters = sorted(grouped)
    if len(clusters) < 2:
        raise ValueError("at least two scene clusters are required")
    rng = random.Random(seed)
    estimates: list[float] = []
    degenerate = 0
    for _ in range(samples):
        sampled: list[Mapping[str, Any]] = []
        for _cluster in clusters:
            sampled.extend(grouped[rng.choice(clusters)])
        estimate = statistic(sampled)
        if estimate is None or not math.isfinite(estimate):
            degenerate += 1
        else:
            estimates.append(estimate)
    valid_fraction = len(estimates) / samples
    degenerate_fraction = degenerate / samples
    fail_closed = (
        degenerate_fraction > maximum_degenerate_fraction or valid_fraction < minimum_valid_fraction
    )
    report: dict[str, Any] = {
        "requested_replicates": samples,
        "valid_replicates": len(estimates),
        "degenerate_replicates": degenerate,
        "denominator": samples,
        "valid_fraction": valid_fraction,
        "degenerate_fraction": degenerate_fraction,
        "maximum_degenerate_fraction": maximum_degenerate_fraction,
        "minimum_valid_fraction": minimum_valid_fraction,
        "interval_conditioning": "valid-whole-scene-cluster-replicates-only",
        "fail_closed": fail_closed,
        "interval": None,
    }
    if estimates and not fail_closed:
        estimates.sort()
        valid_denominator = len(estimates)
        report["interval"] = {
            "lower": estimates[int(0.025 * (valid_denominator - 1))],
            "upper": estimates[int(0.975 * (valid_denominator - 1))],
            "denominator": valid_denominator,
        }
    return report


def leave_one_scene_cluster_out(
    rows: Sequence[Mapping[str, Any]],
    statistic: Callable[[Sequence[Mapping[str, Any]]], float | None],
    *,
    cluster_field: str = "scene_cluster",
) -> dict[str, Any]:
    """Execute the prespecified leave-one-scene-cluster-out sensitivity."""
    clusters = sorted({str(row[cluster_field]) for row in rows})
    estimates = []
    for omitted in clusters:
        estimate = statistic([row for row in rows if str(row[cluster_field]) != omitted])
        estimates.append({"omitted_scene_cluster": omitted, "estimate": estimate})
    degenerate = sum(item["estimate"] is None for item in estimates)
    return {
        "exchangeability_unit": "scene-cluster",
        "denominator": len(clusters),
        "valid_estimates": len(clusters) - degenerate,
        "degenerate_estimates": degenerate,
        "fail_closed": degenerate > 0,
        "estimates": estimates,
    }


def conservative_invalid_as_failure(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Code invalid human outcomes as failures without changing the denominator."""
    values: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if not bool(row["valid"]):
            row["target_correction"] = 0
            row["no_new_defect"] = 0
            row["preservation_rating"] = 0.0
        values.append(row)
    return values


def randomisation_sensitivity(
    rows: Sequence[Mapping[str, Any]],
    *,
    score_field: str,
    outcome_field: str,
    cluster_field: str = "scene_cluster",
    exact_max_permutations: int = 100_000,
    monte_carlo_samples: int = 10_000,
    seed: int = 20260829,
) -> dict[str, Any]:
    """Permute cluster-level outcomes using a prespecified Spearman statistic."""
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[cluster_field])].append(row)
    clusters = sorted(grouped)
    scores = [
        sum(float(row[score_field]) for row in grouped[key]) / len(grouped[key]) for key in clusters
    ]
    outcomes = [
        sum(float(row[outcome_field]) for row in grouped[key]) / len(grouped[key])
        for key in clusters
    ]
    observed = spearman(scores, outcomes)
    if observed is None:
        return {
            "statistic": "absolute-spearman-of-scene-cluster-means",
            "exchangeability_unit": "scene-cluster",
            "evaluable": False,
            "reason": "constant-cluster-margin",
        }
    total = math.factorial(len(clusters))
    if total <= exact_max_permutations:
        permutations = itertools.permutations(outcomes)
        extreme = sum(
            abs(value) >= abs(observed)
            for permutation in permutations
            if (value := spearman(scores, permutation)) is not None
        )
        denominator = total
        method = "exact-enumeration"
        p_value = extreme / denominator
    else:
        rng = random.Random(seed)
        extreme = 0
        for _ in range(monte_carlo_samples):
            permutation = rng.sample(outcomes, k=len(outcomes))
            value = spearman(scores, permutation)
            extreme += value is not None and abs(value) >= abs(observed)
        denominator = monte_carlo_samples
        method = "monte-carlo-plus-one"
        p_value = (extreme + 1) / (denominator + 1)
    return {
        "statistic": "absolute-spearman-of-scene-cluster-means",
        "exchangeability_unit": "scene-cluster",
        "evaluable": True,
        "method": method,
        "fixed_seed": seed,
        "observed": observed,
        "extreme": extreme,
        "denominator": denominator,
        "p_value": p_value,
    }


def evaluate_conjunctive_stopping(
    analysis: Mapping[str, Any], thresholds: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate every prespecified stopping and calibration gate conjunctively."""
    received = int(analysis.get("responses_received", 0))
    invalid = int(analysis.get("invalid_or_omitted", 0))
    invalid_fraction = invalid / received if received else 1.0
    gates = {
        "workload-complete": bool(analysis.get("workload_complete", False)),
        "cluster-completeness-or-contingency": bool(
            analysis.get("clusters_complete", False)
            or analysis.get("missingness_contingency_invoked", False)
        ),
        "class-support": bool(analysis.get("held_out_class_support", False)),
        "auc-evaluable": bool(analysis.get("auc_evaluable", False)),
        "auc-point": float(analysis.get("auc", -1))
        >= float(thresholds["target_correction_no_new_defect_auc"]),
        "auc-lower-bound": float(analysis.get("auc_lower_bound", -1))
        >= float(thresholds["target_correction_no_new_defect_auc_lower_cluster_bootstrap_bound"]),
        "spearman-point": float(analysis.get("spearman", -2))
        >= float(thresholds["preservation_locality_spearman"]),
        "spearman-lower-bound": float(analysis.get("spearman_lower_bound", -2))
        >= float(thresholds["preservation_locality_spearman_lower_cluster_bootstrap_bound"]),
        "duplicate-consistency": float(analysis.get("duplicate_consistency", -1))
        >= float(thresholds["duplicate_consistency"]),
        "invalid-or-omitted-fraction": invalid_fraction
        <= float(thresholds["maximum_invalid_or_omitted_fraction"]),
        "bootstrap-degeneracy-within-policy": bool(
            analysis.get("bootstrap_within_degeneracy_policy", False)
        ),
        "development-lock-before-held-out": bool(
            analysis.get("development_locked_before_held_out", False)
        ),
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    return {
        "ready_to_stop": not failures,
        "gates": dict(sorted(gates.items())),
        "failures": failures,
        "responses_received": received,
        "invalid_or_omitted": invalid,
        "invalid_or_omitted_fraction": invalid_fraction,
    }


__all__ = [
    "auc",
    "conservative_invalid_as_failure",
    "evaluate_conjunctive_stopping",
    "leave_one_scene_cluster_out",
    "randomisation_sensitivity",
    "scene_cluster_bootstrap",
    "spearman",
]
