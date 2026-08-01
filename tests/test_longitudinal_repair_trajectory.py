from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.io import read_json, read_jsonl
from pelicanbench.longitudinal import metric_trends, timeline_summary
from pelicanbench.models import HistoricalObservation, TrajectoryEvent
from pelicanbench.repair import RepairRequirement, score_repair
from pelicanbench.trajectory import evaluate_trajectory, trajectory_utility


def test_longitudinal_fixture(root: Path):
    observations = [HistoricalObservation.model_validate(item) for item in read_jsonl(root / "data/fixtures/historical-observations.jsonl")]
    summary = timeline_summary(observations)
    assert summary["observations"] == 3
    trends = {item.metric:item for item in metric_trends(observations)}
    assert trends["aggregate"].slope_per_observation > 0
    assert summary["first_observation"].startswith("2024")


def test_repair_score(root: Path, heritage):
    before = (root / "benchmark/fixtures/repair/pelican-bicycle-before.svg").read_text()
    after = (root / "benchmark/fixtures/repair/pelican-bicycle-after.svg").read_text()
    data = read_json(root / "benchmark/fixtures/repair/tasks.json")[0]
    requirements = [RepairRequirement(**item) for item in data["requirements"]]
    score = score_repair(heritage, before, after, requirements)
    assert score.after_score > score.before_score
    assert score.improvement > 0
    assert score.repaired_fraction > 0


def test_trajectory_metrics():
    events = [
        TrajectoryEvent(index=0,timestamp="t0",action={"type":"add"},state_hash="a",score=0.2),
        TrajectoryEvent(index=1,timestamp="t1",action={"type":"update"},state_hash="b",score=0.5),
        TrajectoryEvent(index=2,timestamp="t2",action={"type":"update"},state_hash="b",score=0.4),
        TrajectoryEvent(index=3,timestamp="t3",action={"type":"update"},state_hash="c",score=0.6),
        TrajectoryEvent(index=4,timestamp="t4",action={"type":"bad"},state_hash="c",error="failure"),
    ]
    metrics = evaluate_trajectory(events)
    assert metrics.steps == 5
    assert metrics.improvement == pytest.approx(0.4)
    assert metrics.regressions == 1
    assert metrics.recoveries == 1
    assert metrics.repeated_state_fraction > 0
    assert metrics.error_rate == 0.2
    assert trajectory_utility(metrics,cost=2) > 0


def test_empty_trajectory():
    metrics=evaluate_trajectory([])
    assert metrics.final_score is None
    assert trajectory_utility(metrics)==0
