from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.corpus import annotate_document, corpus_summary
from pelicanbench.io import read_jsonl
from pelicanbench.self_learning import (
    LearningRecord,
    append_record,
    can_auto_promote,
    eligible_for_review,
    load_records,
    summarise_learning,
)


def test_corpus_annotations(root: Path):
    records = read_jsonl(root / "data/fixtures/corpus.jsonl")
    annotations = [annotate_document(record) for record in records]
    summary = corpus_summary(annotations)
    assert summary["documents"] == 3
    assert summary["entity_counts"]["ANIMAL"] >= 3
    assert summary["category_counts"]["interaction"] >= 1
    assert all(item["review_status"] == "machine-proposed" for item in annotations)


def test_empty_corpus_summary():
    assert corpus_summary([])["documents"] == 0


def learning(**kwargs):
    defaults = dict(
        track="T16",
        phase="P1",
        observation="Repeated state did not improve score",
        evidence=("run:1", "run:2"),
        strategy="repeat action",
        result="no gain",
        proposed_heuristic="Stop after repeated state hash",
        confidence=0.8,
        scope="agentic runner",
        review_trigger="two independent replications",
        contamination_risk="low",
    )
    defaults.update(kwargs)
    return LearningRecord(**defaults)


def test_learning_append_and_summary(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    record = learning()
    value = append_record(path, record)
    assert value["learning_id"].startswith("learn:")
    loaded = load_records(path)
    assert loaded[0]["proposed_heuristic"].startswith("Stop")
    assert summarise_learning(loaded)["by_status"]["proposed"] == 1
    assert eligible_for_review(record, independent_evidence_items=2)
    assert not can_auto_promote(record)


def test_learning_validation():
    with pytest.raises(ValueError):
        learning(confidence=2)
    with pytest.raises(ValueError):
        learning(status="unknown")
    with pytest.raises(ValueError):
        learning(contamination_risk="extreme")
    assert not eligible_for_review(learning(confidence=0.4), independent_evidence_items=3)
