#!/usr/bin/env python3
"""Analyze synthetic or later authorized T14 rows under the prespecified plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pelicanbench.t14_statistics import (  # ruff: ignore[module-import-not-at-top-of-file]
    auc,
    evaluate_conjunctive_stopping,
    randomisation_sensitivity,
    scene_cluster_bootstrap,
    spearman,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON array of explicitly supplied rows")
    parser.add_argument(
        "--plan",
        type=Path,
        default=ROOT / "benchmark/evidence/advisory/t14/prospective-statistical-analysis-plan.json",
    )
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    labels = [int(row["binary_outcome"]) for row in rows]
    scores = [float(row["automatic_score"]) for row in rows]
    preservation = [float(row["preservation_rating"]) for row in rows]
    locality = [float(row["edit_locality"]) for row in rows]
    auc_value = auc(labels, scores)
    correlation = spearman(preservation, locality)
    auc_bootstrap = scene_cluster_bootstrap(
        rows,
        lambda sample: auc(
            [int(row["binary_outcome"]) for row in sample],
            [float(row["automatic_score"]) for row in sample],
        ),
        samples=int(plan["analysis"]["bootstrap_replicates"]),
        seed=int(plan["analysis"]["bootstrap_seed"]),
    )
    spearman_bootstrap = scene_cluster_bootstrap(
        rows,
        lambda sample: spearman(
            [float(row["preservation_rating"]) for row in sample],
            [float(row["edit_locality"]) for row in sample],
        ),
        samples=int(plan["analysis"]["bootstrap_replicates"]),
        seed=int(plan["analysis"]["bootstrap_seed"]),
    )
    randomisation = randomisation_sensitivity(
        rows,
        score_field="automatic_score",
        outcome_field="binary_outcome",
        seed=int(plan["analysis"]["bootstrap_seed"]),
    )
    report = {
        "status": "analysis-only-no-promotion",
        "auc": auc_value,
        "spearman": correlation,
        "auc_scene_cluster_bootstrap": auc_bootstrap,
        "spearman_scene_cluster_bootstrap": spearman_bootstrap,
        "randomisation_sensitivity": randomisation,
        "stopping": evaluate_conjunctive_stopping(
            {
                "responses_received": len(rows),
                "auc": auc_value if auc_value is not None else -1,
                "spearman": correlation if correlation is not None else -2,
                "degenerate_bootstrap_replicates": auc_bootstrap["degenerate_replicates"],
            },
            plan["confirmatory_thresholds"],
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
