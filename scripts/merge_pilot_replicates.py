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


def build_summary(root: Path, *, replicates: int = 3, minimum_wave_coverage: float = 0.8) -> dict:
    """Apply the prespecified wave-coverage and complete-case rules."""
    models: dict[str, dict] = {}
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        per_replicate: list[dict[str, float | None]] = []
        failures_total = 0
        for rep in range(1, replicates + 1):
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
        wave_detail = []
        for index, scores in enumerate(per_replicate, start=1):
            tasks_scored = sum(value is not None for value in scores.values())
            coverage = tasks_scored / len(task_ids) if task_ids else 0.0
            wave_detail.append(
                {
                    "replicate": index,
                    "tasks_scored": tasks_scored,
                    "coverage": round(coverage, 6),
                    "eligible": bool(task_ids and coverage >= minimum_wave_coverage),
                }
            )
        eligible_indexes = [index for index, detail in enumerate(wave_detail) if detail["eligible"]]
        tasks_out = []
        valid_scores: list[float] = []
        any_scores: list[float] = []
        for tid in task_ids:
            vals = [scores.get(tid) for scores in per_replicate]
            eligible_vals = [vals[index] for index in eligible_indexes]
            present = [v for v in eligible_vals if v is not None]
            complete = bool(eligible_indexes) and len(present) == len(eligible_indexes)
            entry = {
                "task_id": tid,
                "scores": vals,
                "replicates_scored": len(present),
                "eligible_replicates_expected": len(eligible_indexes),
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
            "replicate_wave_detail": wave_detail,
            "eligible_replicate_waves": len(eligible_indexes),
            "minimum_wave_coverage": minimum_wave_coverage,
            "analysable": len(eligible_indexes) >= 2,
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

    return {
        "schema_version": "1",
        "replicates_expected": replicates,
        "minimum_wave_coverage": minimum_wave_coverage,
        "models": models,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/nim-pilot"))
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--minimum-wave-coverage", type=float, default=0.8)
    parser.add_argument(
        "--out", type=Path, default=Path("artifacts/nim-pilot/replicate-agreement-summary.json")
    )
    args = parser.parse_args()
    if not 0 < args.minimum_wave_coverage <= 1:
        parser.error("--minimum-wave-coverage must be in (0, 1]")
    payload = build_summary(
        args.root,
        replicates=args.replicates,
        minimum_wave_coverage=args.minimum_wave_coverage,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    for name, m in payload["models"].items():
        print(
            f"  {name}: waves={m['replicate_waves_found']} "
            f"eligible={m['eligible_replicate_waves']} analysable={m['analysable']} "
            f"complete={m['tasks_complete_all_replicates']}/{m['tasks']} "
            f"failures={m['failures_total']} mean={m['model_mean_complete_cases']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
