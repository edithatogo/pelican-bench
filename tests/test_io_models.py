from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pelicanbench.io import (
    atomic_write_text,
    canonical_json,
    content_hash,
    file_hash,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from pelicanbench.models import BenchmarkTask, EntitySpec, RelationSpec
from pelicanbench.timeutil import utc_now, utc_now_iso


def test_canonical_json_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert content_hash({"a": 1}) == content_hash({"a": 1})
    assert content_hash(b"x").startswith("sha256:")


def test_atomic_json_and_jsonl_roundtrip(tmp_path: Path):
    text = tmp_path / "nested/value.txt"
    atomic_write_text(text, "hello\n")
    assert text.read_text() == "hello\n"
    json_path = write_json(tmp_path / "value.json", {"z": 1})
    assert read_json(json_path) == {"z": 1}
    jsonl_path = write_jsonl(tmp_path / "values.jsonl", [{"a": 1}, {"a": 2}])
    assert read_jsonl(jsonl_path) == [{"a": 1}, {"a": 2}]
    assert file_hash(json_path).startswith("sha256:")


def test_read_jsonl_ignores_blank_lines(tmp_path: Path):
    path = tmp_path / "x.jsonl"
    path.write_text('{"a":1}\n\n {"a":2}\n')
    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]


def test_task_relation_must_reference_entities():
    animal = EntitySpec(id="pelican", label="pelican", ontology_ref="x")
    obj = EntitySpec(id="bicycle", label="bicycle", ontology_ref="y")
    with pytest.raises(ValidationError):
        BenchmarkTask(
            task_id="bad",
            benchmark_release="PB",
            track="compositional-svg",
            prompt="x",
            animal=animal,
            mobile_object=obj,
            relations=(RelationSpec(predicate="rides_on", subject="cat", object="bicycle"),),
            seed=1,
        )


def test_models_are_frozen(heritage):
    with pytest.raises(ValidationError):
        heritage.prompt = "changed"
    with pytest.raises(ValidationError):
        EntitySpec(id="Bad ID", label="x", ontology_ref="x")


def test_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert utc_now().year == 1970
    assert utc_now_iso() == "1970-01-01T00:00:00Z"


def test_json_is_standard(tmp_path: Path):
    path = write_json(tmp_path / "x.json", {"unicode": "pelican 🐦"})
    assert json.loads(path.read_text())["unicode"].startswith("pelican")
