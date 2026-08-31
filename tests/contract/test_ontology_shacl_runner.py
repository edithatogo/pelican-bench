from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts/validate_ontology_shacl.py"
SPEC = importlib.util.spec_from_file_location("ontology_shacl_runner", PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_exact_inline_context():
    runner.assert_inline_context({"@context": runner.CONTEXT, "@graph": [{"@id": "urn:toy"}]})


@pytest.mark.parametrize("context", [None, "https://example.invalid/context", {}, {"@import": "x"}])
def test_remote_or_changed_context_rejected(context):
    with pytest.raises(ValueError, match="inline context"):
        runner.assert_inline_context({"@context": context})


@pytest.mark.parametrize(
    "node", [{"@context": runner.CONTEXT}, {"@import": "https://example.invalid"}]
)
def test_nested_resolution_rejected(node):
    with pytest.raises(ValueError):
        runner.assert_inline_context({"@context": runner.CONTEXT, "@graph": [node]})


@pytest.mark.parametrize(
    "observed,expected", [((0, 0), (0, 0)), ((0, 0), (22, 2)), ((22, 0), (22, 2))]
)
def test_vacuous_or_partial_graph_rejected(observed, expected):
    with pytest.raises(ValueError, match="focus counts"):
        runner.assert_focus_counts(observed, expected)


def test_nonvacuous_counts():
    runner.assert_focus_counts((22, 2), (22, 2))


def test_missing_engine_is_blocked(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(runner.importlib, "import_module", missing)
    with pytest.raises(RuntimeError, match="BLOCKED"):
        runner.execute()


@pytest.mark.filterwarnings(
    "ignore:Dataset.default_context is deprecated.*:DeprecationWarning:rdflib.graph"
)
@pytest.mark.filterwarnings(
    "ignore:ConjunctiveGraph is deprecated.*:DeprecationWarning:rdflib.plugins.parsers.jsonld"
)
def test_real_engine_when_available(monkeypatch):
    if importlib.util.find_spec("pyshacl") is None or importlib.util.find_spec("rdflib") is None:
        pytest.skip("optional genuine SHACL engine unavailable; not SHACL success")
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    receipt = runner.execute()
    assert len(receipt["ontologies"]) == 7
    assert sum(row["concepts"] for row in receipt["ontologies"]) == 76
    assert sum(row["relations"] for row in receipt["ontologies"]) == 22
    assert len(receipt["negative_fixtures_rejected"]) == 6
    assert receipt["evidence_level"] == "E2"
