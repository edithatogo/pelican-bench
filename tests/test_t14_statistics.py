from __future__ import annotations

import pytest

from pelicanbench.t14_statistics import (
    auc,
    evaluate_conjunctive_stopping,
    randomisation_sensitivity,
    scene_cluster_bootstrap,
    spearman,
)


def test_auc_and_spearman_are_tie_aware_and_fail_on_degenerate_margins() -> None:
    assert auc([0, 0, 1, 1], [0.1, 0.5, 0.5, 0.9]) == pytest.approx(0.875)
    assert auc([1, 1], [0.2, 0.8]) is None
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert spearman([1, 1, 1], [1, 2, 3]) is None


def test_scene_cluster_bootstrap_reports_full_degenerate_denominator() -> None:
    rows = [
        {"scene_cluster": "a", "label": 0, "score": 0.1},
        {"scene_cluster": "b", "label": 1, "score": 0.9},
    ]
    report = scene_cluster_bootstrap(
        rows,
        lambda sample: auc(
            [int(row["label"]) for row in sample],
            [float(row["score"]) for row in sample],
        ),
        samples=20,
        seed=3,
    )

    assert report["denominator"] == 20
    assert report["valid_replicates"] + report["degenerate_replicates"] == 20
    assert report["degenerate_replicates"] > 0
    assert report["fail_closed"] is True
    assert report["interval"] is None


def test_cluster_bootstrap_is_deterministic_when_all_resamples_are_evaluable() -> None:
    rows = [
        {"scene_cluster": cluster, "value": value}
        for cluster, value in (("a", 1.0), ("b", 2.0), ("c", 3.0))
    ]

    def statistic(sample):
        return sum(float(row["value"]) for row in sample) / len(sample)

    first = scene_cluster_bootstrap(rows, statistic, samples=50, seed=7)

    assert first == scene_cluster_bootstrap(rows, statistic, samples=50, seed=7)
    assert first["fail_closed"] is False
    assert first["valid_replicates"] == 50


def test_randomisation_sensitivity_declares_exact_and_monte_carlo_rules() -> None:
    six = [
        {"scene_cluster": f"s{index}", "score": index, "outcome": index % 2} for index in range(6)
    ]
    exact = randomisation_sensitivity(six, score_field="score", outcome_field="outcome")
    assert exact["method"] == "exact-enumeration"
    assert exact["exchangeability_unit"] == "scene-cluster"
    assert exact["denominator"] == 720

    nine = [
        {"scene_cluster": f"s{index}", "score": index, "outcome": index % 2} for index in range(9)
    ]
    monte_carlo = randomisation_sensitivity(
        nine,
        score_field="score",
        outcome_field="outcome",
        monte_carlo_samples=100,
        seed=11,
    )
    assert monte_carlo["method"] == "monte-carlo-plus-one"
    assert monte_carlo["denominator"] == 100
    assert monte_carlo["fixed_seed"] == 11
    assert monte_carlo == randomisation_sensitivity(
        nine,
        score_field="score",
        outcome_field="outcome",
        monte_carlo_samples=100,
        seed=11,
    )


def test_stopping_is_conjunctive_and_retains_missingness_denominator() -> None:
    thresholds = {
        "target_correction_no_new_defect_auc": 0.8,
        "target_correction_no_new_defect_auc_lower_cluster_bootstrap_bound": 0.7,
        "preservation_locality_spearman": 0.7,
        "preservation_locality_spearman_lower_cluster_bootstrap_bound": 0.5,
        "duplicate_consistency": 0.8,
        "maximum_invalid_or_omitted_fraction": 0.05,
    }
    analysis = {
        "responses_received": 100,
        "invalid_or_omitted": 5,
        "workload_complete": True,
        "clusters_complete": True,
        "held_out_class_support": True,
        "auc_evaluable": True,
        "auc": 0.8,
        "auc_lower_bound": 0.7,
        "spearman": 0.7,
        "spearman_lower_bound": 0.5,
        "duplicate_consistency": 0.8,
        "degenerate_bootstrap_replicates": 0,
        "development_locked_before_held_out": True,
    }
    passed = evaluate_conjunctive_stopping(analysis, thresholds)
    assert passed["ready_to_stop"] is True
    assert passed["invalid_or_omitted_fraction"] == 0.05

    analysis["invalid_or_omitted"] = 6
    failed = evaluate_conjunctive_stopping(analysis, thresholds)
    assert failed["ready_to_stop"] is False
    assert failed["failures"] == ["invalid-or-omitted-fraction"]
