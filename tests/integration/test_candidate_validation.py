from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pelicanbench.candidate import (
    candidate_commitment_payload,
    resolve_canary_tasks,
    validate_candidate,
)
from pelicanbench.pilot import load_tasks

ROOT = Path(__file__).parents[2]


def test_candidate_is_factorially_balanced_committed_and_empirically_bridged() -> None:
    report = validate_candidate(ROOT)
    assert report.passed, report.as_dict()
    assert report.task_count == 113
    assert report.scenario_count == 81
    assert report.prompt_count == 113
    assert report.canary_count == 9
    assert report.panel_counts == {
        "castillo-2026-factorial-bridge": 48,
        "heritage-anchor": 1,
        "pelicanbench-interface-confirmatory-v1": 64,
    }
    assert report.empirical_exact_prompt_coverage == 1.0


def test_candidate_commitment_payload_matches_checked_file() -> None:
    actual = candidate_commitment_payload(ROOT)
    expected = json.loads(
        (ROOT / "benchmark/tasks/v1-candidate-commitment.json").read_text(encoding="utf-8")
    )
    assert actual == expected


def test_canary_selectors_fail_closed_on_ambiguous_or_repeated_resolution() -> None:
    tasks = load_tasks(ROOT / "benchmark/tasks/v1-candidate.jsonl")
    with pytest.raises(ValueError, match="exactly one"):
        resolve_canary_tasks(tasks, [{"panel_id": "pelicanbench-interface-confirmatory-v1"}])
    with pytest.raises(ValueError, match="unique tasks"):
        resolve_canary_tasks(
            tasks,
            [
                {"task_id": "pb:heritage-pelican-bike-v1"},
                {"task_id": "pb:heritage-pelican-bike-v1"},
            ],
        )


def test_candidate_validator_detects_tampered_task_commitment(tmp_path: Path) -> None:
    for relative in (
        "benchmark/tasks/v1-candidate.jsonl",
        "benchmark/tasks/v1-candidate-design.json",
        "benchmark/tasks/v1-candidate-commitment.json",
        "benchmark/tasks/v1-candidate-canary.jsonl",
        "data/derived/castillo-2026-prompt-corpus.jsonl",
    ):
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    commitment = json.loads(
        (tmp_path / "benchmark/tasks/v1-candidate-commitment.json").read_text(encoding="utf-8")
    )
    commitment["commitment"] = "sha256:" + "0" * 64
    (tmp_path / "benchmark/tasks/v1-candidate-commitment.json").write_text(
        json.dumps(commitment), encoding="utf-8"
    )
    report = validate_candidate(tmp_path)
    assert not report.passed
    assert "task-commitment-mismatch" in {item.code for item in report.findings}
