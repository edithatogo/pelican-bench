#!/usr/bin/env python3
"""Execute unchanged project SHACL shapes; missing optional engines are blocked."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from pelicanbench.ontology import Ontology

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "animal.json",
    "bicycle.json",
    "interface.json",
    "mobile-object.json",
    "pelican-bicycle.json",
    "pelican.json",
    "tuk-tuk.json",
)
CONTEXT = {
    "pb": "https://w3id.org/pelicanbench/ontology#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}


def assert_inline_context(value: dict[str, Any]) -> None:
    """Only the local export's fixed context is accepted; never dereference one."""
    if value.get("@context") != CONTEXT:
        raise ValueError("expected exact project inline context")

    def visit(node: Any, *, top: bool = False) -> None:
        if isinstance(node, dict):
            if not top and "@context" in node:
                raise ValueError("nested context rejected")
            if "@import" in node:
                raise ValueError("context import rejected")
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value, top=True)


def assert_focus_counts(observed: tuple[int, int], expected: tuple[int, int]) -> None:
    if observed != expected or sum(observed) == 0:
        raise ValueError("SHACL focus counts are missing or inconsistent")


def execute(root: Path = ROOT) -> dict[str, Any]:
    try:
        rdf = importlib.import_module("rdflib")
        engine = importlib.import_module("pyshacl")
    except ImportError as exc:
        raise RuntimeError("BLOCKED: optional rdflib/pyshacl engine unavailable") from exc
    directory = root / "benchmark/ontologies"
    shape_bytes = (directory / "shapes.ttl").read_bytes()
    shapes = rdf.Graph().parse(data=shape_bytes, format="turtle")
    pb = rdf.Namespace(CONTEXT["pb"])

    def conforms(graph: Any) -> bool:
        result, _, _ = engine.validate(
            graph,
            shacl_graph=shapes,
            inference="none",
            advanced=False,
            js=False,
            do_owl_imports=False,
            inplace=False,
        )
        if not isinstance(result, bool):
            raise RuntimeError("SHACL engine returned no boolean conformance result")
        return result

    results = []
    for name in FILES:
        source = (directory / name).read_bytes()
        ontology = Ontology.from_dict(json.loads(source))
        exported = ontology.to_jsonld()
        assert_inline_context(exported)
        export_bytes = json.dumps(exported, sort_keys=True).encode()
        dataset = rdf.Dataset(default_union=True)
        dataset.parse(data=export_bytes, format="json-ld")
        # @graph is named in the export. A plain Graph sees only two root triples.
        graph = rdf.Graph()
        for triple in dataset.triples((None, None, None)):
            graph.add(triple)
        counts = (
            len(set(graph.subjects(rdf.RDF.type, pb.Concept))),
            len(set(graph.subjects(rdf.RDF.type, pb.Relation))),
        )
        assert_focus_counts(counts, (len(ontology.concepts), len(ontology.relations)))
        if not conforms(graph):
            raise RuntimeError(f"project ontology failed existing shapes: {name}")
        results.append(
            {
                "path": f"benchmark/ontologies/{name}",
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "export_sha256": hashlib.sha256(export_bytes).hexdigest(),
                "concepts": counts[0],
                "relations": counts[1],
                "triples": len(graph),
                "conforms": True,
            }
        )
    negatives = {
        "missing-concept-id": "<urn:toy:c> a pb:Concept .",
        "multiple-concept-ids": '<urn:toy:c> a pb:Concept ; pb:identifier "a", "b" .',
        "non-string-id": "<urn:toy:c> a pb:Concept ; pb:identifier 1 .",
        "missing-relation-id": "<urn:toy:r> a pb:Relation .",
        "missing-feature": '<urn:toy:c> a pb:Concept ; pb:identifier "c" ; pb:featureRequirement [pb:tier "necessary"] .',
        "bad-tier": '<urn:toy:c> a pb:Concept ; pb:identifier "c" ; pb:featureRequirement [pb:feature "f";pb:tier "invalid"] .',
    }
    for name, body in negatives.items():
        graph = rdf.Graph().parse(data=f"@prefix pb: <{CONTEXT['pb']}> . {body}", format="turtle")
        if conforms(graph):
            raise RuntimeError(f"negative fixture unexpectedly conformed: {name}")
    return {
        "schema_version": "ontology-shacl-local-v1",
        "evidence_level": "E2",
        "status": "existing-shapes-fixture-verified",
        "engine_versions": {
            name: importlib.metadata.version(name)
            for name in (
                "pyshacl",
                "rdflib",
                "owlrl",
                "prettytable",
                "html5rdf",
                "pyparsing",
                "packaging",
                "wcwidth",
            )
        },
        "shape_sha256": hashlib.sha256(shape_bytes).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ontologies": results,
        "negative_fixtures_rejected": sorted(negatives),
        "limits": [
            "Existing shapes only; no expert or empirical validation.",
            "No namespace registration, semantic import or normative change.",
            "Not full-harness evidence or independent reproduction.",
        ],
    }


def main() -> None:
    try:
        receipt = execute()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
