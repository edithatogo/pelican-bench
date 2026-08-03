from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pelicanbench.interoperability import (
    OntologyInteroperabilityProfile,
    OntologyPatternSource,
    load_ontology_interoperability_profile,
)
from pelicanbench.validation import _validate_ontology_interoperability


def _source(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "asset_id": "github:example/ontology",
        "role": "design-pattern",
        "semantic_import": False,
        "adopted_patterns": ["modularity"],
        "rationale": "fixture",
    }
    value.update(overrides)
    return value


def _profile(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.0.0",
        "namespace": "https://w3id.org/example/ontology#",
        "namespace_status": "registration-planned",
        "registration_target": "github:example/w3id.org",
        "registration_evidence": None,
        "representations": ["json", "json-ld", "shacl"],
        "validation_surfaces": [
            "benchmark/ontologies/context.jsonld",
            "benchmark/ontologies/shapes.ttl",
            "benchmark/ontology-tests/competency-cases.json",
        ],
        "competency_question_surface": "benchmark/ontology-tests/competency-cases.json",
        "semantic_import_policy": "Explicit review only.",
        "sources": [_source()],
    }
    value.update(overrides)
    return value


def _write_profile_root(tmp_path: Path, value: dict[str, object]) -> Path:
    root = tmp_path / "repo"
    profile = root / "benchmark/ontologies/interoperability-profile.json"
    profile.parent.mkdir(parents=True)
    profile.write_text(json.dumps(value), encoding="utf-8")
    return root


def test_pattern_source_semantic_import_invariants():
    with pytest.raises(ValidationError, match="must explicitly enable"):
        OntologyPatternSource.model_validate(_source(role="semantic-import"))
    with pytest.raises(ValidationError, match="may only be enabled"):
        OntologyPatternSource.model_validate(_source(semantic_import=True))
    imported = OntologyPatternSource.model_validate(
        _source(role="semantic-import", semantic_import=True)
    )
    assert imported.semantic_import


def test_profile_namespace_and_uniqueness_invariants():
    with pytest.raises(ValidationError, match="require a registration target"):
        OntologyInteroperabilityProfile.model_validate(_profile(registration_target=None))
    with pytest.raises(ValidationError, match="require registration evidence"):
        OntologyInteroperabilityProfile.model_validate(
            _profile(namespace_status="published", registration_evidence=None)
        )
    with pytest.raises(ValidationError, match="representations must be unique"):
        OntologyInteroperabilityProfile.model_validate(_profile(representations=["json", "json"]))
    duplicate = _source()
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        OntologyInteroperabilityProfile.model_validate(_profile(sources=[duplicate, duplicate]))
    published = OntologyInteroperabilityProfile.model_validate(
        _profile(namespace_status="published", registration_evidence="evidence.json")
    )
    assert published.namespace_status == "published"


def test_load_profile_and_validation_missing_profile(tmp_path: Path):
    root = tmp_path / "empty"
    root.mkdir()
    assert _validate_ontology_interoperability(root) == []

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(_profile()), encoding="utf-8")
    assert load_ontology_interoperability_profile(profile_path).registration_target


def test_interoperability_validation_reports_all_drift_classes(tmp_path: Path):
    value = _profile(registration_evidence="premature.json")
    root = _write_profile_root(tmp_path, value)

    context = root / "benchmark/ontologies/context.jsonld"
    context.write_text(json.dumps({"@context": {"pb": "https://wrong.example/#"}}))
    shapes = root / "benchmark/ontologies/shapes.ttl"
    shapes.write_text("@prefix pb: <https://wrong.example/#> .\n", encoding="utf-8")
    # Do not create the competency surface. This also exercises the generic missing
    # validation-surface finding for that declared path.

    findings = _validate_ontology_interoperability(root)
    codes = {item.code for item in findings}
    assert {
        "missing-ontology-validation-surface",
        "ontology-namespace-context-drift",
        "ontology-namespace-shacl-drift",
        "missing-ontology-competency-surface",
        "premature-ontology-registration-evidence",
    } <= codes


def test_interoperability_validation_catches_malformed_profile(tmp_path: Path):
    root = _write_profile_root(tmp_path, _profile(registration_target=None))
    findings = _validate_ontology_interoperability(root)
    assert [item.code for item in findings] == ["invalid-ontology-interoperability-profile"]


def test_interoperability_validation_accepts_coherent_surfaces(tmp_path: Path):
    value = _profile()
    root = _write_profile_root(tmp_path, value)
    context = root / "benchmark/ontologies/context.jsonld"
    context.write_text(json.dumps({"@context": {"pb": value["namespace"]}}))
    shapes = root / "benchmark/ontologies/shapes.ttl"
    shapes.write_text(f"@prefix pb: <{value['namespace']}> .\n", encoding="utf-8")
    competency = root / "benchmark/ontology-tests/competency-cases.json"
    competency.parent.mkdir(parents=True)
    competency.write_text("[]\n", encoding="utf-8")
    assert _validate_ontology_interoperability(root) == []
