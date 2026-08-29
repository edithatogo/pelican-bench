#!/usr/bin/env python3
"""Validate the advisory T14 plan with a deterministic synthetic allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "benchmark/evidence/advisory/t14/prospective-statistical-analysis-plan.json"
DEFAULT_CANDIDATE = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def synthetic_allocation() -> list[dict[str, Any]]:
    """Return the fixed synthetic design; it never reads candidate outcomes."""
    rows: list[dict[str, Any]] = []
    occurrences: Counter[int] = Counter()
    for scene_number in range(24):
        subset_start = 0 if scene_number % 2 == 0 else 4
        subset_rotation = (scene_number // 2) % 4
        families = [subset_start + (slot + subset_rotation) % 4 for slot in range(4)]
        for slot, family_number in enumerate(families):
            index = scene_number * 4 + slot
            occurrence = occurrences[family_number]
            occurrences[family_number] += 1
            rows.append(
                {
                    "synthetic_id": f"synthetic-{index + 1:03d}",
                    "scene_cluster": f"synthetic-scene-{scene_number + 1:02d}",
                    "partition": "development" if index < 72 else "held-out",
                    "defect_family": f"synthetic-family-{family_number + 1:02d}",
                    "severity": "moderate" if slot < 2 else "severe",
                    "target-correction": "positive" if occurrence % 3 else "negative",
                    "no-new-defect": "negative" if occurrence % 3 == 1 else "positive",
                }
            )
    return rows


def candidate_allocation(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Project real candidate design fields into the joint-allocation validator."""
    partition_names = {
        "proposed-development": "development",
        "proposed-held-out": "held-out",
    }
    return [
        {
            "synthetic_id": str(row["repair_id"]),
            "scene_cluster": str(row["scene_group_id"]),
            "partition": partition_names[str(row["proposed_partition"])],
            "defect_family": str(row["defect_family"]),
            "severity": str(row["severity"]),
        }
        for row in candidate["episodes"]
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bindings(plan: dict[str, Any], candidate_path: Path) -> None:
    bindings = plan["bindings"]
    require(
        sha256(candidate_path) == bindings["candidate_manifest_sha256"], "candidate binding drift"
    )
    for relative, expected in bindings["implementation_source_sha256"].items():
        require(sha256(ROOT / relative) == expected, f"implementation binding drift: {relative}")


def validate(plan: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    design = plan["design"]
    require(plan["status"] == "prospective-advisory-not-frozen", "plan status may not freeze")
    require(
        plan["simulation"]
        == {
            "synthetic_only": True,
            "zero_cost": True,
            "external_calls": False,
            "seed": 20260829,
        },
        "simulation boundary drift",
    )
    require("held-out-threshold-tuning" in plan["prohibitions"], "held-out tuning prohibited")
    require(design["resampling_unit"] == "scene-cluster", "wrong resampling unit")
    require(len(rows) == design["episode_count"] == 96, "episode count drift")
    scenes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        scenes[row["scene_cluster"]].append(row)
    require(len(scenes) == design["scene_cluster_count"] == 24, "scene count drift")
    require({len(group) for group in scenes.values()} == {4}, "scene size drift")
    require(
        Counter(row["partition"] for row in rows) == {"development": 72, "held-out": 24},
        "partition episode allocation drift",
    )
    scene_partitions = Counter()
    for group in scenes.values():
        partitions = {row["partition"] for row in group}
        require(len(partitions) == 1, "scene crosses partitions")
        require(
            Counter(row["severity"] for row in group) == {"moderate": 2, "severe": 2},
            "scene severity allocation drift",
        )
        scene_partitions[next(iter(partitions))] += 1
    require(scene_partitions == {"development": 18, "held-out": 6}, "cluster split drift")

    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        families[row["defect_family"]].append(row)
    require(len(families) == design["defect_families"] == 8, "family count drift")
    for family, group in families.items():
        require(len(group) == 12, f"family allocation drift: {family}")
        require(
            Counter(row["partition"] for row in group) == {"development": 9, "held-out": 3},
            f"family partition drift: {family}",
        )
        require(
            Counter(row["severity"] for row in group) == {"moderate": 6, "severe": 6},
            f"severity confounding: {family}",
        )

    held_out = [row for row in rows if row["partition"] == "held-out"]
    minimum = plan["class_support"]["minimum_held_out_scene_clusters_per_class"]
    class_support: dict[str, dict[str, int]] = {}
    available_endpoints = set(rows[0]) if rows else set()
    for endpoint in plan["class_support"]["binary_endpoints"]:
        if endpoint not in available_endpoints:
            continue
        support = {
            label: len({row["scene_cluster"] for row in held_out if row[endpoint] == label})
            for label in plan["class_support"]["required_classes"]
        }
        require(
            all(count >= minimum for count in support.values()),
            f"class support failure: {endpoint}",
        )
        class_support[endpoint] = support

    require(plan["confirmatory_thresholds"]["conjunctive"] is True, "thresholds not conjunctive")
    require(plan["stopping"]["rule"] == "all-gates-conjunctive", "stopping rule drift")
    require(plan["stopping"]["no_early_efficacy_stop"] is True, "early efficacy stop allowed")
    require(
        design["duplicate_interpretation"] == "repeated-measure-not-independent-episode",
        "duplicate independence drift",
    )
    return {
        "status": "valid-prospective-allocation-not-frozen",
        "episodes": len(rows),
        "scene_clusters": len(scenes),
        "scene_cluster_split": dict(scene_partitions),
        "class_support": class_support,
        "normative_sample_frozen": False,
        "human_ratings_present": False,
        "score_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    validate_bindings(plan, args.candidate)
    synthetic_report = validate(plan, synthetic_allocation())
    candidate_report = validate(plan, candidate_allocation(candidate))
    report = {"synthetic": synthetic_report, "candidate": candidate_report}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("T14 prospective statistical plan valid: real candidate and synthetic 24x4; 18/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
