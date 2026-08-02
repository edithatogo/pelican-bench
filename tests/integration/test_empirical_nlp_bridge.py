from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.empirical_nlp import (
    PromptRecord,
    annotate_prompt,
    annotate_prompt_corpus,
    empirical_nlp_report,
    task_design_coverage,
)
from pelicanbench.pilot import load_tasks

ROOT = Path(__file__).parents[2]
SOURCE_PATH = ROOT / "data/derived/castillo-2026-prompt-corpus.jsonl"
TASK_PATH = ROOT / "benchmark/tasks/v1-candidate.jsonl"
REPORT_SNAPSHOT = ROOT / "benchmark/evidence/snapshots/castillo-2026-empirical-nlp-report.json"
COVERAGE_SNAPSHOT = ROOT / "benchmark/evidence/snapshots/castillo-2026-design-coverage.json"
STATUS = "source-derived-exact-prompt-bridge-E2"


def _source_records() -> list[PromptRecord]:
    return [
        PromptRecord.from_mapping(json.loads(line))
        for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_castillo_empirical_nlp_report_matches_checked_evidence() -> None:
    annotations = annotate_prompt_corpus(_source_records())
    actual = empirical_nlp_report(annotations, evidence_status=STATUS)
    expected = json.loads(REPORT_SNAPSHOT.read_text(encoding="utf-8"))
    assert actual == expected


def test_castillo_bridge_has_exact_prompt_and_design_coverage() -> None:
    annotations = annotate_prompt_corpus(_source_records())
    actual = task_design_coverage(
        annotations,
        load_tasks(TASK_PATH),
        panel_id="castillo-2026-factorial-bridge",
        evidence_status=STATUS,
    )
    expected = json.loads(COVERAGE_SNAPSHOT.read_text(encoding="utf-8"))
    assert actual == expected


def test_annotation_extracts_aliases_relations_and_constraints() -> None:
    record = PromptRecord(
        source_id="fixture",
        record_id="fixture:1",
        prompt=(
            "Create an editable animated SVG: an octopus driving a tuk tuk in a "
            "three-quarter view, with 3 grouped layers and a text label"
        ),
    )
    annotation = annotate_prompt(record)
    assert {(mention.entity_type, mention.canonical_id) for mention in annotation.mentions} == {
        ("animal", "octopus"),
        ("mobile_object", "tuk-tuk"),
    }
    assert annotation.relations == ("drives",)
    assert annotation.viewpoints == ("three-quarter",)
    assert annotation.numeric_constraints == ("3",)
    assert annotation.asks_for_svg
    assert annotation.asks_for_animation
    assert annotation.asks_for_editability
    assert annotation.asks_for_text
    assert annotation.compositional


def test_annotation_prefers_longest_non_overlapping_alias() -> None:
    annotation = annotate_prompt(
        PromptRecord(
            source_id="fixture",
            record_id="fixture:2",
            prompt="Generate an SVG of a dog riding an electric scooter",
        )
    )
    object_mentions = [item for item in annotation.mentions if item.entity_type == "mobile_object"]
    assert len(object_mentions) == 1
    assert object_mentions[0].surface == "electric scooter"
    assert object_mentions[0].canonical_id == "electric-scooter"


def test_duplicate_record_ids_and_empty_reports_fail_closed() -> None:
    repeated = PromptRecord(source_id="fixture", record_id="duplicate", prompt="pelican bicycle")
    with pytest.raises(ValueError, match="identifiers must be unique"):
        annotate_prompt_corpus([repeated, repeated])
    with pytest.raises(ValueError, match="at least one annotation"):
        empirical_nlp_report([])
