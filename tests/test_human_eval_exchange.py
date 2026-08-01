from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pelicanbench.calibration import PairwiseCalibrationTask
from pelicanbench.human_eval import (
    export_pairwise_evaluation_batch,
    inter_rater_agreement,
    load_pairwise_votes_csv,
)


def _pairs():
    return [
        PairwiseCalibrationTask("p1", "t1", "a1", "a2", "m1", "m2", "overall-preference", 1),
        PairwiseCalibrationTask("p2", "t2", "a3", "a4", "m1", "m2", "animal-anatomy", 2),
    ]


def test_human_evaluation_batch_and_vote_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    batch = export_pairwise_evaluation_batch(_pairs(), tmp_path)
    assert batch.assignments == 2
    path = tmp_path / "assignments.csv"
    rows = list(csv.DictReader(path.open()))
    for index, row in enumerate(rows):
        row["winner"] = "A" if index == 0 else "tie"
        row["rater_hash"] = f"{index + 1:016x}"
        row["panel"] = "public"
        row["consent_version"] = "v1"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    votes = load_pairwise_votes_csv(path)
    assert len(votes) == 2
    assert votes[0].winner == "a1"


def test_vote_loader_rejects_direct_identifiers(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "pair_id,task_id,criterion,left_artifact_id,right_artifact_id,winner,rater_hash,email\n"
        "p,t,overall,a,b,A,0000000000000001,user@example.com\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="direct identifier"):
        load_pairwise_votes_csv(path)


def test_inter_rater_agreement(tmp_path: Path):
    path = tmp_path / "ratings.csv"
    path.write_text(
        "pair_id,task_id,criterion,left_artifact_id,right_artifact_id,winner,rater_hash\n"
        "p,t,overall,a,b,A,0000000000000001\n"
        "p,t,overall,a,b,A,0000000000000002\n"
        "q,u,overall,c,d,B,0000000000000001\n"
        "q,u,overall,c,d,A,0000000000000002\n",
        encoding="utf-8",
    )
    report = inter_rater_agreement(load_pairwise_votes_csv(path))
    assert report.items == 2
    assert report.observed_agreement == pytest.approx(0.5)
    assert -1 <= report.kappa <= 1
