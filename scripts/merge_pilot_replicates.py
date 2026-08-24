#!/usr/bin/env python3
"""Merge pilot replicate waves and compute cross-replicate agreement.

Reads artifacts/nim-pilot/<model>/replicate-NN/results.jsonl and failures.jsonl,
joins per-task scorecard aggregates across replicates, and emits a summary JSON
with per-model means and per-task replicate spread.

Usage: python scripts/merge_pilot_replicates.py [--root artifacts/nim-pilot] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/nim-pilot"))
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument(
        "--out", type=Path, default=Path("artifacts/nim-pilot/replicate-agreement-summary.json")
    )
    args = parser.parse_args()

    models: dict[str, dict] = {}
    for model_dir in sorted(p for p in args.root.iterdir() if p.is_dir()):
        per_replicate: list[dict[str, float | None]] = []
        failures_total = 0
        for rep in range(1, args.replicates + 1):
            rdir = model_dir / f"replicate-{rep:02d}"
            rows = load_jsonl(rdir / "results.jsonl")
            fails = load_jsonl(rdir / "failures.jsonl")
            failures_total += len(fails)
            scores: dict[str, float | None] = {}
            for row in rows:
                task_id = str((row.get("task") or {}).get("task_id"))
                card = row.get("scorecard")
                scores[task_id] = None if card is None else float(card.get("aggregate", 0.0))
            per_replicate.append(scores)

        task_ids = sorted({t for scores in per_replicate for t in scores})
        tasks_out = []
        valid_scores: list[float] = []  # all replicates scored
        any_scores: list[float] = []
        for tid in task_ids:
            vals = [scores.get(tid) for scores in per_replicate]
            present = [v for v in vals if v is not None]
            complete = len(present) == args.replicates
            entry = {
                "task_id": tid,
                "scores": vals,
                "replicates_scored": len(present),
                "complete": complete,
            }
            if complete:
                entry["mean"] = round(statistics.fmean(present), 6)
                entry["stdev"] = round(statistics.pstdev(present), 6) if len(present) > 1 else 0.0
                entry["exact_agreement"] = len(set(present)) == 1
                valid_scores.extend(present)
            elif present:
                any_scores.extend(present)
            tasks_out.append(entry)

        models[model_dir.name] = {
            "replicate_waves_found": sum(1 for s in per_replicate if s),
            "tasks": len(task_ids),
            "tasks_complete_all_replicates": sum(1 for t in tasks_out if t.get("complete")),
            "failures_total": failures_total,
            "model_mean_complete_cases": (
                round(statistics.fmean(valid_scores), 6) if valid_scores else None
            ),
            "model_mean_any_scored": round(statistics.fmean(any_scores), 6) if any_scores else None,
            "exact_agreement_rate": (
                round(
                    sum(1 for t in tasks_out if t.get("exact_agreement"))
                    / max(1, sum(1 for t in tasks_out if t.get("complete"))),
                    4,
                )
                if any(t.get("complete") for t in tasks_out)
                else None
            ),
            "task_detail": tasks_out,
        }

    payload = {
        "schema_version": "1",
        "replicates_expected": args.replicates,
        "models": models,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    for name, m in models.items():
        print(
            f"  {name}: waves={m['replicate_waves_found']} "
            f"complete={m['tasks_complete_all_replicates']}/{m['tasks']} "
            f"failures={m['failures_total']} mean={m['model_mean_complete_cases']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
