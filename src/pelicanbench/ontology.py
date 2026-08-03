"""Ontology loading, validation, abstraction, JSON-LD export and scene composition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import read_json

FEATURE_TIERS = {
    "necessary",
    "diagnostic",
    "common",
    "optional",
    "style-dependent",
    "prohibited",
}


@dataclass(frozen=True, slots=True)
class Ontology:
    ontology_id: str
    version: str
    concepts: dict[str, dict[str, Any]]
    relations: dict[str, dict[str, Any]]
    competency_questions: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Ontology:
        result = cls(
            str(value["id"]),
            str(value["version"]),
            {str(item["id"]): item for item in value.get("concepts", [])},
            {str(item["id"]): item for item in value.get("relations", [])},
            tuple(value.get("competency_questions", [])),
        )
        result.validate()
        return result

    @classmethod
    def load(cls, path: str | Path) -> Ontology:
        value = read_json(path)
        if not isinstance(value, dict):
            raise TypeError("ontology root must be an object")
        return cls.from_dict(value)

    def validate(self) -> None:
        for concept_id, concept in self.concepts.items():
            parent = concept.get("parent")
            if parent is not None and parent not in self.concepts:
                raise ValueError(f"unknown parent {parent!r} for {concept_id!r}")
            for requirement in concept.get("feature_requirements", []):
                tier = str(requirement.get("tier", ""))
                if tier not in FEATURE_TIERS:
                    raise ValueError(f"unknown feature tier {tier!r} for {concept_id!r}")
        for relation_id, relation in self.relations.items():
            inverse = relation.get("inverse")
            if inverse is not None and inverse not in self.relations:
                raise ValueError(f"unknown inverse {inverse!r} for {relation_id!r}")
        question_ids = [str(item.get("id", "")) for item in self.competency_questions]
        if any(not item for item in question_ids) or len(question_ids) != len(set(question_ids)):
            raise ValueError("competency questions require unique non-empty identifiers")
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError(f"ontology inheritance cycle at {node}")
            if node in visited:
                return
            visiting.add(node)
            parent = self.concepts[node].get("parent")
            if parent is not None:
                visit(str(parent))
            visiting.remove(node)
            visited.add(node)

        for node in self.concepts:
            visit(node)

    def ancestors(self, concept_id: str) -> tuple[str, ...]:
        if concept_id not in self.concepts:
            raise KeyError(concept_id)
        output: list[str] = []
        current = self.concepts[concept_id].get("parent")
        while current is not None:
            output.append(str(current))
            current = self.concepts[str(current)].get("parent")
        return tuple(output)

    def required_feature_profile(self, concept_id: str) -> dict[str, str]:
        lineage = (*reversed(self.ancestors(concept_id)), concept_id)
        output: dict[str, str] = {}
        for item in lineage:
            concept = self.concepts[item]
            for feature in concept.get("required_features", []):
                output.setdefault(str(feature), "necessary")
            for requirement in concept.get("feature_requirements", []):
                output[str(requirement["feature"])] = str(requirement["tier"])
        return output

    def required_features(self, concept_id: str) -> tuple[str, ...]:
        profile = self.required_feature_profile(concept_id)
        return tuple(
            feature for feature, tier in profile.items() if tier in {"necessary", "diagnostic"}
        )

    def is_a(self, concept_id: str, parent_id: str) -> bool:
        return concept_id == parent_id or parent_id in self.ancestors(concept_id)

    def to_jsonld(self) -> dict[str, Any]:
        """Export a lightweight interoperable view without changing normative JSON."""

        base = "https://w3id.org/pelicanbench/ontology/"
        graph: list[dict[str, Any]] = []
        for concept_id, concept in self.concepts.items():
            node: dict[str, Any] = {
                "@id": f"{base}{self.ontology_id}/{concept_id}",
                "@type": "pb:Concept",
                "pb:identifier": concept_id,
                "rdfs:label": concept.get("label", concept_id),
            }
            if concept.get("parent"):
                node["rdfs:subClassOf"] = {"@id": f"{base}{self.ontology_id}/{concept['parent']}"}
            profile = self.required_feature_profile(concept_id)
            if profile:
                node["pb:featureRequirement"] = [
                    {"pb:feature": feature, "pb:tier": tier}
                    for feature, tier in sorted(profile.items())
                ]
            graph.append(node)
        for relation_id, relation in self.relations.items():
            graph.append(
                {
                    "@id": f"{base}{self.ontology_id}/relation/{relation_id}",
                    "@type": "pb:Relation",
                    "pb:identifier": relation_id,
                    "rdfs:label": relation.get("label", relation_id),
                    "pb:requiredFeature": relation.get("required_features", []),
                }
            )
        return {
            "@context": {
                "pb": "https://w3id.org/pelicanbench/ontology#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "@id": f"{base}{self.ontology_id}",
            "@type": "pb:Ontology",
            "pb:version": self.version,
            "@graph": graph,
        }


def merge_ontologies(
    ontologies: Iterable[Ontology],
    *,
    ontology_id: str,
    version: str,
) -> Ontology:
    concepts: dict[str, dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    questions: list[dict[str, Any]] = []
    for ontology in ontologies:
        for key, value in ontology.concepts.items():
            if key in concepts and concepts[key] != value:
                raise ValueError(f"conflicting concept {key}")
            concepts[key] = value
        for key, value in ontology.relations.items():
            if key in relations and relations[key] != value:
                raise ValueError(f"conflicting relation {key}")
            relations[key] = value
        questions.extend(ontology.competency_questions)
    result = Ontology(ontology_id, version, concepts, relations, tuple(questions))
    result.validate()
    return result


def compose_scene(
    animal: Ontology,
    mobile: Ontology,
    interface: Ontology,
    *,
    animal_id: str,
    mobile_id: str,
    relation_id: str,
) -> dict[str, Any]:
    if animal_id not in animal.concepts:
        raise KeyError(animal_id)
    if mobile_id not in mobile.concepts:
        raise KeyError(mobile_id)
    if relation_id not in interface.relations:
        raise KeyError(relation_id)
    relation = interface.relations[relation_id]
    allowed = set(relation.get("allowed_object_classes", []))
    object_class = mobile.concepts[mobile_id].get("class")
    if allowed and object_class not in allowed:
        raise ValueError(f"{relation_id} is not compatible with object class {object_class}")
    return {
        "animal": animal_id,
        "mobile_object": mobile_id,
        "relation": relation_id,
        "required_animal_features": animal.required_features(animal_id),
        "required_object_features": mobile.required_features(mobile_id),
        "required_interface_features": tuple(relation.get("required_features", [])),
        "animal_feature_profile": animal.required_feature_profile(animal_id),
        "object_feature_profile": mobile.required_feature_profile(mobile_id),
    }


@dataclass(frozen=True, slots=True)
class CompetencyCaseResult:
    case_id: str
    expected_compatible: bool
    observed_compatible: bool
    passed: bool
    error: str | None = None


def evaluate_competency_cases(
    animal: Ontology,
    mobile: Ontology,
    interface: Ontology,
    cases: Iterable[dict[str, Any]],
) -> tuple[CompetencyCaseResult, ...]:
    """Execute ontology compatibility competency cases.

    The function validates logical compatibility only. The natural-language question list
    remains a review aid and does not affect the observed result.
    """

    output: list[CompetencyCaseResult] = []
    seen: set[str] = set()
    for case in cases:
        case_id = str(case.get("id", ""))
        if not case_id or case_id in seen:
            raise ValueError("competency cases require unique non-empty identifiers")
        seen.add(case_id)
        expected = bool(case.get("expected_compatible"))
        error: str | None = None
        try:
            compose_scene(
                animal,
                mobile,
                interface,
                animal_id=str(case["animal"]),
                mobile_id=str(case["mobile_object"]),
                relation_id=str(case["relation"]),
            )
            observed = True
        except (KeyError, ValueError) as exc:
            observed = False
            error = str(exc)
        output.append(
            CompetencyCaseResult(
                case_id=case_id,
                expected_compatible=expected,
                observed_compatible=observed,
                passed=observed == expected,
                error=error,
            )
        )
    return tuple(output)


def abstract_specialised_ontology(
    value: dict[str, Any],
    *,
    new_id: str,
    parent_mapping: dict[str, str],
) -> dict[str, Any]:
    """Create a reviewable candidate abstraction; never mutate normative ontologies."""

    output = {
        "id": new_id,
        "version": "candidate-1",
        "status": "candidate-human-review-required",
        "concepts": [],
        "relations": value.get("relations", []),
        "competency_questions": value.get("competency_questions", []),
    }
    seen: set[str] = set()
    for concept in value.get("concepts", []):
        target = parent_mapping.get(concept["id"], concept["id"])
        if target in seen:
            continue
        seen.add(target)
        candidate = {**concept, "id": target}
        if candidate.get("parent") in parent_mapping:
            candidate["parent"] = parent_mapping[candidate["parent"]]
        output["concepts"].append(candidate)
    return output
