from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/merge_pilot_replicates.py"
SPEC = importlib.util.spec_from_file_location("merge_pilot_replicates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_wave(
    root: Path, replicate: int, task_ids: tuple[str, ...], *, unscored: tuple[str, ...] = ()
) -> None:
    directory = root / "model-a" / f"replicate-{replicate:02d}"
    directory.mkdir(parents=True)
    rows = [
        {
            "task": {"task_id": task_id},
            "scorecard": None if task_id in unscored else {"aggregate": 0.5},
        }
        for task_id in task_ids
    ]
    (directory / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_prespecified_wave_coverage_and_complete_cases(tmp_path: Path) -> None:
    _write_wave(tmp_path, 1, ("a", "b", "c", "d", "e"))
    _write_wave(tmp_path, 2, ("a", "b", "c", "d"))
    _write_wave(tmp_path, 3, ("a", "b", "c", "d", "e"), unscored=("d", "e"))

    summary = MODULE.build_summary(tmp_path)
    model = summary["models"]["model-a"]

    assert model["eligible_replicate_waves"] == 2
    assert model["analysable"] is True
    assert model["tasks_complete_all_replicates"] == 4
    assert [row["eligible"] for row in model["replicate_wave_detail"]] == [True, True, False]
