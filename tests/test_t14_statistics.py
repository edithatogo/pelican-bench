from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pelicanbench.t14_statistics import (
    auc,
    evaluate_conjunctive_stopping,
    randomisation_sensitivity,
    scene_cluster_bootstrap,
    spearman,
)

ROOT = Path(__file__).resolve().parents[1]


def load_analysis_module():
    path = ROOT / "scripts/analyze_t14_prospective_statistics.py"
    spec = importlib.util.spec_from_file_location("analyze_t14_prospective_statistics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_bound_envelope(tmp_path: Path):
    module = load_analysis_module()
    candidate_source = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"
    plan_source = (
        ROOT / "benchmark/evidence/advisory/t14/prospective-statistical-analysis-plan.json"
    )
    candidate = json.loads(candidate_source.read_text(encoding="utf-8"))
    plan = json.loads(plan_source.read_text(encoding="utf-8"))
    plan["analysis"]["bootstrap_replicates"] = 50
    candidate_path = tmp_path / "candidate.json"
    plan_path = tmp_path / "plan.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    plan["bindings"]["candidate_manifest_sha256"] = module.file_sha256(candidate_path)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    held_out = [
        row for row in candidate["episodes"] if row["proposed_partition"] == "proposed-held-out"
    ]
    rows = []
    for index, episode in enumerate(held_out):
        outcome = index % 2
        rows.append(
            {
                "row_id": f"row-{index:02d}",
                "episode_id": episode["repair_id"],
                "scene_cluster": episode["scene_group_id"],
                "partition": "held-out",
                "target_correction": outcome,
                "no_new_defect": outcome,
                "preservation_rating": float(index),
                "valid": True,
                "invalid_reason": None,
                "duplicate_of": None,
            }
        )
    for index in range(3):
        duplicate = dict(rows[index])
        duplicate["row_id"] = f"duplicate-{index:02d}"
        duplicate["duplicate_of"] = rows[index]["row_id"]
        rows.append(duplicate)
    locked_ids = sorted(row["repair_id"] for row in held_out)
    method = {"method_id": "synthetic-test-scorer", "revision": "v1", "source_sha256": "b" * 64}
    score_manifest = {
        "schema_version": "1.0.0",
        "status": "locked-automatic-score-inputs",
        "candidate_manifest_sha256": module.file_sha256(candidate_path),
        "method": method,
        "method_commitment_sha256": module.canonical_sha256(method),
        "entries": [
            {
                "episode_id": episode["repair_id"],
                "before_sha256": episode["before_sha256"],
                "after_sha256": episode["after_sha256"],
                "target_correction_score": float(index % 2),
                "no_new_defect_score": float(index % 2),
                "edit_locality": float(index),
            }
            for index, episode in enumerate(held_out)
        ],
    }
    score_manifest_path = tmp_path / "scores.json"
    score_manifest_path.write_text(json.dumps(score_manifest), encoding="utf-8")
    envelope = {
        "schema_version": "1.0.0",
        "status": "collected-ratings-bound-to-frozen-t14",
        "plan_sha256": module.file_sha256(plan_path),
        "candidate_manifest_sha256": module.file_sha256(candidate_path),
        "score_manifest_sha256": module.file_sha256(score_manifest_path),
        "freeze": {
            "status": "normative-sample-frozen",
            "receipt_sha256": "a" * 64,
            "assignment_sha256": module.canonical_sha256(locked_ids),
            "held_out_episode_ids": locked_ids,
        },
        "collection": {
            "workload_complete": True,
            "development_locked_before_held_out": True,
            "missingness_contingency_invoked": False,
        },
        "rows": rows,
    }
    return (
        module,
        envelope,
        plan,
        candidate,
        score_manifest,
        plan_path,
        candidate_path,
        score_manifest_path,
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


def test_cluster_bootstrap_conditions_on_valid_replicates_within_locked_policy() -> None:
    rows = [
        {"scene_cluster": cluster, "value": value}
        for cluster, value in (("a", 1.0), ("b", 2.0), ("c", 3.0))
    ]
    calls = 0

    def statistic(sample):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return sum(float(row["value"]) for row in sample) / len(sample)

    report = scene_cluster_bootstrap(rows, statistic, samples=10, seed=7)

    assert report["degenerate_replicates"] == 1
    assert report["valid_fraction"] == 0.9
    assert report["degenerate_fraction"] == 0.1
    assert report["fail_closed"] is False
    assert report["interval"]["denominator"] == 9


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
        "bootstrap_within_degeneracy_policy": True,
        "development_locked_before_held_out": True,
    }
    passed = evaluate_conjunctive_stopping(analysis, thresholds)
    assert passed["ready_to_stop"] is True
    assert passed["invalid_or_omitted_fraction"] == 0.05

    analysis["invalid_or_omitted"] = 6
    failed = evaluate_conjunctive_stopping(analysis, thresholds)
    assert failed["ready_to_stop"] is False
    assert failed["failures"] == ["invalid-or-omitted-fraction"]


def test_end_to_end_analysis_receipt_is_bound_and_complete(tmp_path: Path) -> None:
    module, envelope, plan, candidate, scores, plan_path, candidate_path, scores_path = (
        make_bound_envelope(tmp_path)
    )

    receipt = module.analyze_envelope(
        envelope,
        plan,
        candidate,
        scores,
        plan_path=plan_path,
        candidate_path=candidate_path,
        score_manifest_path=scores_path,
    )

    assert receipt["denominators"] == {
        "locked_assignment_denominator": 24,
        "received_base_rows": 24,
        "received_duplicate_rows": 3,
        "invalid_or_omitted": 0,
    }
    assert set(receipt["endpoint_results"]) == {"target_correction", "no_new_defect"}
    assert (
        receipt["endpoint_results"]["target_correction"]["leave_one_scene_cluster_out"][
            "denominator"
        ]
        == 6
    )
    assert receipt["duplicate_rows_are_repeated_measures"] is True
    assert receipt["duplicate_consistency"]["value"] == 1.0
    assert receipt["receipt_sha256"] == module.canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    assert receipt["normative_sample_frozen_by_analysis"] is False
    assert receipt["score_promotion"] is False


def test_duplicate_consistency_is_computed_not_caller_supplied(tmp_path: Path) -> None:
    module, envelope, plan, candidate, scores, plan_path, candidate_path, scores_path = (
        make_bound_envelope(tmp_path)
    )
    envelope["rows"][-1]["preservation_rating"] = -1.0

    receipt = module.analyze_envelope(
        envelope,
        plan,
        candidate,
        scores,
        plan_path=plan_path,
        candidate_path=candidate_path,
        score_manifest_path=scores_path,
    )

    assert receipt["duplicate_consistency"]["denominator"] == 3
    assert receipt["duplicate_consistency"]["exact_agreements"] == 2
    assert receipt["duplicate_consistency"]["value"] == pytest.approx(2 / 3)
    assert "duplicate-consistency" in receipt["stopping"]["failures"]


def test_score_manifest_is_content_and_candidate_bound(tmp_path: Path) -> None:
    module, envelope, plan, candidate, scores, plan_path, candidate_path, scores_path = (
        make_bound_envelope(tmp_path)
    )
    scores["entries"][0]["before_sha256"] = "0" * 64
    scores_path.write_text(json.dumps(scores), encoding="utf-8")
    envelope["score_manifest_sha256"] = module.file_sha256(scores_path)

    with pytest.raises(ValueError, match="before hash"):
        module.analyze_envelope(
            envelope,
            plan,
            candidate,
            scores,
            plan_path=plan_path,
            candidate_path=candidate_path,
            score_manifest_path=scores_path,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda envelope: envelope["freeze"].__setitem__("status", "proposed"), "not frozen"),
        (lambda envelope: envelope["rows"][0].pop("no_new_defect"), "row schema"),
        (lambda envelope: envelope["rows"].pop(20), "locked denominator"),
        (lambda envelope: envelope["rows"][0].__setitem__("scene_cluster", "wrong"), "scene"),
    ],
)
def test_analysis_envelope_fails_closed_on_binding_and_completeness_drift(
    tmp_path: Path, mutation, message: str
) -> None:
    module, envelope, plan, candidate, _scores, plan_path, candidate_path, _scores_path = (
        make_bound_envelope(tmp_path)
    )
    changed = deepcopy(envelope)
    mutation(changed)

    with pytest.raises(ValueError, match=message):
        module.validate_envelope(
            changed,
            plan,
            candidate,
            plan_path=plan_path,
            candidate_path=candidate_path,
        )
