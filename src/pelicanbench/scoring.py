"""Transparent multidimensional structural scorecards."""

from __future__ import annotations

import math
from typing import Iterable

from .models import BenchmarkTask, DimensionScore, ScoreCard
from .svg import inspect_svg

DEFAULT_WEIGHTS = {
    "submission_integrity": 0.15,
    "animal_anatomy": 0.17,
    "vehicle_mechanics": 0.18,
    "interaction": 0.20,
    "composition": 0.10,
    "vector_quality": 0.10,
    "instruction_coverage": 0.10,
}


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _normalise_feature(value: str) -> set[str]:
    lowered = value.lower().replace("_", "-")
    tokens = {lowered, lowered.replace("-", "")}
    for item in lowered.split("-"):
        if item:
            tokens.add(item)
    aliases = {
        "gular-pouch": {"gular", "pouch"},
        "webbed-foot": {"webbed", "foot", "feet"},
        "front-wheel": {"front", "wheel"},
        "rear-wheel": {"rear", "wheel"},
        "handlebar": {"handlebar", "handlebars", "steering"},
        "pedal": {"pedal", "pedals", "crank"},
    }
    tokens.update(aliases.get(lowered, set()))
    return tokens


def _feature_fraction(required: Iterable[str], present: set[str]) -> float:
    required_values = list(required)
    if not required_values:
        return 1.0
    matched = 0
    for feature in required_values:
        aliases = _normalise_feature(feature)
        if aliases & present:
            matched += 1
    return matched / len(required_values)


def _dimension(name: str, value: float, method: str, *evidence: str) -> DimensionScore:
    return DimensionScore(
        name=name,
        value=min(1.0, max(0.0, float(value))),
        method=method,
        evidence=tuple(evidence),
    )


def score_svg(
    task: BenchmarkTask,
    svg: str,
    *,
    submission_id: str,
    scorer_version: str = "svg-structural/0.1.0",
) -> ScoreCard:
    inspection = inspect_svg(svg)
    features = inspection.features
    roles = set(features.get("role_counts", {}))
    groups = features.get("role_groups", {})

    integrity = 1.0 if inspection.valid else 0.0
    animal_required = task.animal.required_features
    object_required = task.mobile_object.required_features
    animal = _feature_fraction(animal_required, roles)
    vehicle = _feature_fraction(object_required, roles)

    cycle_types = {"bicycle", "unicycle", "cargo-bicycle", "tricycle"}
    if task.mobile_object.id in cycle_types:
        expected_wheels = 1 if task.mobile_object.id == "unicycle" else 3 if task.mobile_object.id == "tricycle" else 2
        observed = int(features.get("wheel_candidate_count", 0))
        wheel_presence = min(1.0, observed / expected_wheels)
        pair_score = (
            float(features.get("wheel_pair_score", 0.0))
            if expected_wheels >= 2
            else wheel_presence
        )
        vehicle = _mean((vehicle, wheel_presence, pair_score, float(bool(groups.get("frame")))))

    required_predicates = {relation.predicate for relation in task.relations if relation.required}
    relation_role_tokens = {
        "rides_on": {"rider", "riding", "contact", "saddle", "pedal"},
        "operates": {"operates", "control", "steering", "grip"},
        "drives": {"driver", "driving", "steering", "cabin"},
        "pilots": {"pilot", "cockpit", "control"},
        "passenger_in": {"passenger", "cabin", "inside"},
        "tows": {"tow", "hitch", "rope"},
        "pushes": {"push", "contact"},
        "pulls": {"pull", "harness", "rope"},
    }
    relation_scores: list[float] = []
    for predicate in required_predicates:
        tokens = relation_role_tokens.get(predicate, {predicate})
        relation_scores.append(min(1.0, len(tokens & roles) / max(1, min(2, len(tokens)))))
    interaction = _mean(relation_scores)
    if groups.get("contact"):
        interaction = max(interaction, 0.65)
    if groups.get("foot") and groups.get("pedal"):
        interaction = max(interaction, 0.8)

    element_count = int(features.get("element_count", 0))
    composition = 0.0
    if inspection.valid:
        composition = 1.0 if 8 <= element_count <= 500 else 0.65 if 3 <= element_count <= 1500 else 0.35
    vector_quality = _mean(
        (
            1.0 if inspection.valid else 0.0,
            min(1.0, float(features.get("labelled_element_fraction", 0.0)) * 4),
            1.0 if int(features.get("external_reference_count", 0)) == 0 else 0.0,
            1.0 if int(features.get("path_characters", 0)) < 100_000 else 0.5,
        )
    )
    instruction_coverage = _mean((animal, vehicle, interaction))

    dimensions = (
        _dimension("submission_integrity", integrity, "bounded XML and source-security gate", *inspection.errors),
        _dimension("animal_anatomy", animal, "ontology feature-role coverage", *animal_required),
        _dimension("vehicle_mechanics", vehicle, "ontology and geometry feature coverage", *object_required),
        _dimension("interaction", interaction, "required relation-role coverage", *sorted(required_predicates)),
        _dimension("composition", composition, "bounded structural composition heuristic", f"elements={element_count}"),
        _dimension("vector_quality", vector_quality, "editability and source-hygiene heuristic"),
        _dimension("instruction_coverage", instruction_coverage, "mean critical concept coverage"),
    )
    dimension_values = {item.name: item.value for item in dimensions}
    aggregate = sum(DEFAULT_WEIGHTS[name] * dimension_values[name] for name in DEFAULT_WEIGHTS)
    gates = {
        "safe_and_parseable": inspection.valid,
        "animal_minimum": animal >= 0.25,
        "vehicle_minimum": vehicle >= 0.25,
        "interaction_minimum": interaction >= 0.25,
    }
    warnings = list(inspection.warnings)
    if features.get("text_character_count", 0):
        warnings.append("visible text may create a semantic shortcut")
    if not math.isfinite(aggregate):
        aggregate = 0.0
        warnings.append("non-finite aggregate replaced with zero")
    return ScoreCard(
        task_id=task.task_id,
        submission_id=submission_id,
        dimensions=dimensions,
        critical_gates=gates,
        valid=all(gates.values()),
        aggregate=round(aggregate, 6),
        scorer_version=scorer_version,
        warnings=tuple(dict.fromkeys(warnings)),
    )
