#!/usr/bin/env python3
"""Create a bound, non-promotional T14 statistical analysis receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pelicanbench.t14_statistics import (  # ruff: ignore[module-import-not-at-top-of-file]
    auc,
    conservative_invalid_as_failure,
    evaluate_conjunctive_stopping,
    leave_one_scene_cluster_out,
    randomisation_sensitivity,
    scene_cluster_bootstrap,
    spearman,
)

DEFAULT_PLAN = ROOT / "benchmark/evidence/advisory/t14/prospective-statistical-analysis-plan.json"
DEFAULT_CANDIDATE = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"
ENVELOPE_KEYS = {
    "schema_version",
    "status",
    "plan_sha256",
    "candidate_manifest_sha256",
    "freeze",
    "collection",
    "rows",
}
FREEZE_KEYS = {"status", "receipt_sha256", "assignment_sha256", "held_out_episode_ids"}
COLLECTION_KEYS = {
    "workload_complete",
    "development_locked_before_held_out",
    "duplicate_consistency",
    "missingness_contingency_invoked",
}
ROW_KEYS = {
    "row_id",
    "episode_id",
    "scene_cluster",
    "partition",
    "target_correction",
    "no_new_defect",
    "target_correction_score",
    "no_new_defect_score",
    "preservation_rating",
    "edit_locality",
    "valid",
    "invalid_reason",
    "duplicate_of",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def validate_envelope(
    envelope: dict[str, Any],
    plan: dict[str, Any],
    candidate: dict[str, Any],
    *,
    plan_path: Path,
    candidate_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Validate bindings, locked denominator, strict rows, and completeness."""
    require(set(envelope) == ENVELOPE_KEYS, "analysis envelope schema drift")
    require(envelope["schema_version"] == "1.0.0", "analysis envelope version drift")
    require(
        envelope["status"] == "collected-ratings-bound-to-frozen-t14", "input is not freeze-bound"
    )
    require(envelope["plan_sha256"] == file_sha256(plan_path), "analysis plan binding drift")
    require(
        envelope["candidate_manifest_sha256"] == file_sha256(candidate_path),
        "candidate manifest binding drift",
    )
    require(
        plan["bindings"]["candidate_manifest_sha256"] == file_sha256(candidate_path),
        "plan candidate binding drift",
    )

    freeze = envelope["freeze"]
    require(isinstance(freeze, dict) and set(freeze) == FREEZE_KEYS, "freeze schema drift")
    require(freeze["status"] == "normative-sample-frozen", "normative assignment is not frozen")
    require(re.fullmatch(r"[0-9a-f]{64}", str(freeze["receipt_sha256"])), "invalid freeze receipt")
    locked_ids = sorted(str(value) for value in freeze["held_out_episode_ids"])
    require(
        len(locked_ids) == len(set(locked_ids)) == 24, "locked assignment denominator must be 24"
    )
    require(freeze["assignment_sha256"] == canonical_sha256(locked_ids), "assignment binding drift")

    candidate_rows = {str(row["repair_id"]): row for row in candidate["episodes"]}
    proposed_held_out = sorted(
        repair_id
        for repair_id, row in candidate_rows.items()
        if row["proposed_partition"] == "proposed-held-out"
    )
    require(
        locked_ids == proposed_held_out, "freeze assignment does not match candidate held-out set"
    )

    collection = envelope["collection"]
    require(
        isinstance(collection, dict) and set(collection) == COLLECTION_KEYS,
        "collection schema drift",
    )
    require(isinstance(collection["workload_complete"], bool), "invalid workload flag")
    require(
        isinstance(collection["development_locked_before_held_out"], bool),
        "invalid held-out lock flag",
    )
    require(_finite_number(collection["duplicate_consistency"]), "invalid duplicate consistency")
    require(
        isinstance(collection["missingness_contingency_invoked"], bool), "invalid missingness flag"
    )

    rows = envelope["rows"]
    require(isinstance(rows, list), "rows must be a list")
    row_ids: set[str] = set()
    base_by_episode: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for row in rows:
        require(isinstance(row, dict) and set(row) == ROW_KEYS, "rating row schema drift")
        row_id = str(row["row_id"])
        require(row_id and row_id not in row_ids, "duplicate row ID")
        row_ids.add(row_id)
        episode_id = str(row["episode_id"])
        require(episode_id in candidate_rows, "row episode absent from candidate")
        candidate_row = candidate_rows[episode_id]
        require(row["partition"] == "held-out", "non-held-out row supplied")
        require(
            candidate_row["proposed_partition"] == "proposed-held-out",
            "candidate partition mismatch",
        )
        require(row["scene_cluster"] == candidate_row["scene_group_id"], "candidate scene mismatch")
        require(isinstance(row["valid"], bool), "valid flag must be boolean")
        require(_finite_number(row["target_correction_score"]), "invalid target score")
        require(_finite_number(row["no_new_defect_score"]), "invalid new-defect score")
        require(_finite_number(row["edit_locality"]), "invalid edit locality")
        if row["valid"]:
            require(row["target_correction"] in {0, 1}, "target endpoint must be binary")
            require(row["no_new_defect"] in {0, 1}, "new-defect endpoint must be binary")
            require(_finite_number(row["preservation_rating"]), "invalid preservation rating")
            require(row["invalid_reason"] is None, "valid row has invalid reason")
        else:
            require(row["target_correction"] is None, "invalid row has target outcome")
            require(row["no_new_defect"] is None, "invalid row has new-defect outcome")
            require(row["preservation_rating"] is None, "invalid row has preservation rating")
            require(bool(str(row["invalid_reason"]).strip()), "invalid row lacks reason")
        if row["duplicate_of"] is None:
            require(episode_id not in base_by_episode, "multiple base rows for episode")
            base_by_episode[episode_id] = row
        else:
            duplicates.append(row)

    require(sorted(base_by_episode) == locked_ids, "base rows do not complete locked denominator")
    require(
        len(duplicates) >= math.ceil(len(locked_ids) * float(plan["design"]["duplicate_fraction"])),
        "duplicate assignment workload incomplete",
    )
    base_by_row_id = {row["row_id"]: row for row in base_by_episode.values()}
    for row in duplicates:
        original = base_by_row_id.get(row["duplicate_of"])
        require(original is not None, "duplicate does not reference a base row")
        require(original["episode_id"] == row["episode_id"], "duplicate episode mismatch")

    return (
        list(base_by_episode.values()),
        duplicates,
        {
            "locked_assignment_denominator": len(locked_ids),
            "received_base_rows": len(base_by_episode),
            "received_duplicate_rows": len(duplicates),
            "invalid_or_omitted": sum(not row["valid"] for row in base_by_episode.values()),
        },
    )


def _endpoint_analysis(
    rows: list[dict[str, Any]], endpoint: str, plan: dict[str, Any]
) -> dict[str, Any]:
    valid = [row for row in rows if row["valid"]]
    score_field = f"{endpoint}_score"

    def statistic(sample):
        values = [row for row in sample if row["valid"]]
        return auc(
            [int(row[endpoint]) for row in values], [float(row[score_field]) for row in values]
        )

    point = statistic(valid)
    bootstrap = scene_cluster_bootstrap(
        rows,
        statistic,
        samples=int(plan["analysis"]["bootstrap_replicates"]),
        seed=int(plan["analysis"]["bootstrap_seed"]),
        maximum_degenerate_fraction=float(plan["analysis"]["maximum_degenerate_fraction"]),
        minimum_valid_fraction=float(plan["analysis"]["minimum_valid_fraction"]),
    )
    return {
        "point": point,
        "class_counts": {
            str(label): sum(row[endpoint] == label for row in valid) for label in (0, 1)
        },
        "class_scene_cluster_counts": {
            str(label): len({row["scene_cluster"] for row in valid if row[endpoint] == label})
            for label in (0, 1)
        },
        "scene_cluster_bootstrap": bootstrap,
        "leave_one_scene_cluster_out": leave_one_scene_cluster_out(rows, statistic),
        "randomisation_sensitivity": randomisation_sensitivity(
            valid,
            score_field=score_field,
            outcome_field=endpoint,
            seed=int(plan["analysis"]["randomisation_seed"]),
        ),
    }


def analyze_envelope(
    envelope: dict[str, Any],
    plan: dict[str, Any],
    candidate: dict[str, Any],
    *,
    plan_path: Path,
    candidate_path: Path,
) -> dict[str, Any]:
    base_rows, duplicates, denominator = validate_envelope(
        envelope, plan, candidate, plan_path=plan_path, candidate_path=candidate_path
    )
    endpoints = {
        endpoint: _endpoint_analysis(base_rows, endpoint, plan)
        for endpoint in ("target_correction", "no_new_defect")
    }
    valid = [row for row in base_rows if row["valid"]]

    def preservation_statistic(sample):
        values = [row for row in sample if row["valid"]]
        return spearman(
            [float(row["preservation_rating"]) for row in values],
            [float(row["edit_locality"]) for row in values],
        )

    preservation_point = preservation_statistic(valid)
    preservation_bootstrap = scene_cluster_bootstrap(
        base_rows,
        preservation_statistic,
        samples=int(plan["analysis"]["bootstrap_replicates"]),
        seed=int(plan["analysis"]["bootstrap_seed"]),
        maximum_degenerate_fraction=float(plan["analysis"]["maximum_degenerate_fraction"]),
        minimum_valid_fraction=float(plan["analysis"]["minimum_valid_fraction"]),
    )
    conservative = conservative_invalid_as_failure(base_rows)
    conservative_results = {
        "denominator": len(conservative),
        "invalid_coded_as_failure": denominator["invalid_or_omitted"],
        "endpoints": {
            endpoint: auc(
                [int(row[endpoint]) for row in conservative],
                [float(row[f"{endpoint}_score"]) for row in conservative],
            )
            for endpoint in endpoints
        },
        "preservation_locality": spearman(
            [float(row["preservation_rating"]) for row in conservative],
            [float(row["edit_locality"]) for row in conservative],
        ),
    }
    auc_points = [item["point"] for item in endpoints.values()]
    valid_auc_points = [value for value in auc_points if value is not None]
    auc_lowers = [
        item["scene_cluster_bootstrap"]["interval"]["lower"]
        for item in endpoints.values()
        if item["scene_cluster_bootstrap"]["interval"] is not None
    ]
    preservation_interval = preservation_bootstrap["interval"]
    minimum_class_clusters = int(plan["class_support"]["minimum_held_out_scene_clusters_per_class"])
    class_support = all(
        all(
            count >= minimum_class_clusters for count in item["class_scene_cluster_counts"].values()
        )
        for item in endpoints.values()
    )
    bootstrap_policy_passed = (
        all(not item["scene_cluster_bootstrap"]["fail_closed"] for item in endpoints.values())
        and not preservation_bootstrap["fail_closed"]
    )
    stopping = evaluate_conjunctive_stopping(
        {
            "responses_received": denominator["locked_assignment_denominator"],
            "invalid_or_omitted": denominator["invalid_or_omitted"],
            "workload_complete": envelope["collection"]["workload_complete"],
            "clusters_complete": denominator["received_base_rows"]
            == denominator["locked_assignment_denominator"],
            "missingness_contingency_invoked": envelope["collection"][
                "missingness_contingency_invoked"
            ],
            "held_out_class_support": class_support,
            "auc_evaluable": all(value is not None for value in auc_points)
            and len(auc_lowers) == 2,
            "auc": min(valid_auc_points, default=-1),
            "auc_lower_bound": min(auc_lowers) if len(auc_lowers) == 2 else -1,
            "spearman": preservation_point if preservation_point is not None else -2,
            "spearman_lower_bound": preservation_interval["lower"] if preservation_interval else -2,
            "duplicate_consistency": envelope["collection"]["duplicate_consistency"],
            "bootstrap_within_degeneracy_policy": bootstrap_policy_passed,
            "development_locked_before_held_out": envelope["collection"][
                "development_locked_before_held_out"
            ],
        },
        plan["confirmatory_thresholds"],
    )
    payload = {
        "schema_version": "1.0.0",
        "status": "analysis-only-no-promotion",
        "bindings": {
            "plan_sha256": envelope["plan_sha256"],
            "candidate_manifest_sha256": envelope["candidate_manifest_sha256"],
            "freeze_receipt_sha256": envelope["freeze"]["receipt_sha256"],
            "assignment_sha256": envelope["freeze"]["assignment_sha256"],
        },
        "denominators": denominator,
        "duplicate_rows_are_repeated_measures": True,
        "endpoint_results": endpoints,
        "preservation_locality": {
            "point": preservation_point,
            "scene_cluster_bootstrap": preservation_bootstrap,
            "leave_one_scene_cluster_out": leave_one_scene_cluster_out(
                base_rows, preservation_statistic
            ),
        },
        "conservative_invalid_as_failure": conservative_results,
        "stopping": stopping,
        "normative_sample_frozen_by_analysis": False,
        "score_promotion": False,
        "duplicate_row_count": len(duplicates),
    }
    return {**payload, "receipt_sha256": canonical_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="strict freeze-bound T14 analysis envelope")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    envelope = json.loads(args.input.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = analyze_envelope(
        envelope, plan, candidate, plan_path=args.plan, candidate_path=args.candidate
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
