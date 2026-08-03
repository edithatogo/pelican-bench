"""Transparent scorecards that separate source, render and semantic evidence."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import cast

from .models import BenchmarkTask, DimensionScore, EvidenceLevel, ScoreCard, SemanticAssessment
from .render import RenderedSVG, SVGRenderError, render_svg
from .semantic import validate_semantic_assessment
from .svg import SVGInspection, inspect_svg

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


def _dimension(name: str, value: float, method: str, *evidence: str) -> DimensionScore:
    return DimensionScore(
        name=name,
        value=min(1.0, max(0.0, float(value))),
        method=method,
        evidence=tuple(evidence),
    )


def _range_score(
    value: float, *, low: float, ideal_low: float, ideal_high: float, high: float
) -> float:
    if value <= low or value >= high:
        return 0.0
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        return (value - low) / max(1e-12, ideal_low - low)
    return (high - value) / max(1e-12, high - ideal_high)


def _semantic_values(assessment: SemanticAssessment | None) -> dict[str, float]:
    return assessment.probabilities() if assessment is not None else {}


def _entity_score(
    probabilities: dict[str, float],
    *,
    present_id: str,
    feature_prefix: str,
    required_features: Iterable[str],
) -> float:
    present = probabilities.get(present_id, 0.0)
    feature_ids = [f"{feature_prefix}:{feature}" for feature in required_features]
    feature_score = (
        _mean(probabilities.get(item, 0.0) for item in feature_ids) if feature_ids else 1.0
    )
    # Presence is conjunctive: a list of plausible parts cannot compensate for the
    # absence of a recognisable entity.
    return present * (0.5 + 0.5 * feature_score)


def score_svg(
    task: BenchmarkTask,
    svg: str,
    *,
    submission_id: str,
    semantic_assessment: SemanticAssessment | None = None,
    inspection: SVGInspection | None = None,
    rendered: RenderedSVG | None = None,
    scorer_version: str = "svg-multilayer/0.2.0",
) -> ScoreCard:
    """Score SVG source, canonical render and optional source-independent semantics.

    SVG labels, IDs, classes, comments and metadata never contribute to animal,
    vehicle, interaction or instruction scores.  Without a matching semantic
    assessment those dimensions remain unassessed and critical gates fail.
    """

    checked = inspection or inspect_svg(svg)
    warnings = list(checked.warnings)
    rendered_value = rendered
    if checked.valid and rendered_value is None:
        try:
            rendered_value = render_svg(svg, inspection=checked)
        except SVGRenderError as exc:
            warnings.append(str(exc))

    assessment = semantic_assessment
    assessment_errors: tuple[str, ...] = ()
    if assessment is not None and rendered_value is not None:
        assessment_errors = validate_semantic_assessment(task, rendered_value, assessment)
        if assessment_errors:
            warnings.extend(assessment_errors)
            assessment = None
    elif assessment is not None:
        assessment_errors = ("semantic assessment cannot be matched because rendering failed",)
        warnings.extend(assessment_errors)
        assessment = None

    probabilities = _semantic_values(assessment)
    animal = _entity_score(
        probabilities,
        present_id="animal-present",
        feature_prefix="animal-feature",
        required_features=task.animal.required_features,
    )
    vehicle = _entity_score(
        probabilities,
        present_id="object-present",
        feature_prefix="object-feature",
        required_features=task.mobile_object.required_features,
    )
    relation_ids = [
        f"relation:{relation.predicate}" for relation in task.relations if relation.required
    ]
    relation_score = _mean(probabilities.get(item, 0.0) for item in relation_ids)
    interaction = relation_score * min(
        probabilities.get("animal-present", 0.0),
        probabilities.get("object-present", 0.0),
    )

    render_composition = 0.0
    if rendered_value is not None and rendered_value.nonblank:
        foreground = _range_score(
            rendered_value.foreground_fraction,
            low=0.0001,
            ideal_low=0.02,
            ideal_high=0.80,
            high=0.995,
        )
        occupied = _range_score(
            rendered_value.bounding_box_fraction,
            low=0.001,
            ideal_low=0.08,
            ideal_high=0.95,
            high=1.0001,
        )
        render_composition = _mean((foreground, occupied))
    composition = (
        _mean(
            (
                render_composition,
                probabilities.get("scene-coherent", 0.0),
            )
        )
        if assessment is not None
        else render_composition * 0.5
    )

    features = checked.features
    visible_shapes = int(features.get("visible_shape_count", 0))
    hidden_shapes = int(features.get("hidden_shape_count", 0))
    visible_ratio = visible_shapes / max(1, visible_shapes + hidden_shapes)
    element_count = int(features.get("element_count", 0))
    complexity_score = (
        1.0 if 3 <= element_count <= 1_500 else 0.5 if element_count <= 5_000 else 0.0
    )
    path_score = 1.0 if int(features.get("path_characters", 0)) < 100_000 else 0.5
    grouping_score = min(1.0, int(features.get("group_count", 0)) / max(1, visible_shapes / 8))
    vector_quality = _mean(
        (
            1.0 if checked.valid else 0.0,
            visible_ratio,
            complexity_score,
            path_score,
            grouping_score,
        )
    )

    semantic_question_ids = [
        "animal-present",
        "object-present",
        *[f"animal-feature:{item}" for item in task.animal.required_features],
        *[f"object-feature:{item}" for item in task.mobile_object.required_features],
        *relation_ids,
    ]
    instruction_coverage = _mean(probabilities.get(item, 0.0) for item in semantic_question_ids)

    integrity = 1.0 if checked.valid else 0.0
    dimensions = (
        _dimension(
            "submission_integrity",
            integrity,
            "bounded XML and source-security gate",
            *checked.errors,
        ),
        _dimension(
            "animal_anatomy",
            animal,
            "source-independent atomic visual questions",
            *task.animal.required_features,
        ),
        _dimension(
            "vehicle_mechanics",
            vehicle,
            "source-independent atomic visual questions",
            *task.mobile_object.required_features,
        ),
        _dimension(
            "interaction",
            interaction,
            "source-independent required-relation questions",
            *relation_ids,
        ),
        _dimension(
            "composition",
            composition,
            "canonical-render occupancy plus source-independent scene question",
            f"render_composition={render_composition:.6f}",
        ),
        _dimension(
            "vector_quality",
            vector_quality,
            "source hygiene, visible structure and bounded editability diagnostics",
            f"visible_shapes={visible_shapes}",
            f"hidden_shapes={hidden_shapes}",
        ),
        _dimension(
            "instruction_coverage",
            instruction_coverage,
            "mean source-independent required concept coverage",
            *semantic_question_ids,
        ),
    )
    dimension_values = {item.name: item.value for item in dimensions}
    aggregate = sum(DEFAULT_WEIGHTS[name] * dimension_values[name] for name in DEFAULT_WEIGHTS)

    semantic_complete = assessment is not None and not assessment_errors
    gates = {
        "safe_and_parseable": checked.valid,
        "nonblank_render": bool(rendered_value and rendered_value.nonblank),
        "source_independent_semantics": bool(assessment and assessment.source_independent),
        "semantic_assessment_complete": semantic_complete,
        "animal_minimum": animal >= 0.25,
        "vehicle_minimum": vehicle >= 0.25,
        "interaction_minimum": interaction >= 0.25,
    }
    if semantic_assessment is None:
        warnings.append(
            "semantic dimensions are unassessed; SVG source labels are deliberately ignored"
        )
    if features.get("text_character_count", 0):
        warnings.append("visible text may create a visual semantic shortcut")
    if hidden_shapes:
        warnings.append("hidden or non-rendered shapes are excluded from visual evidence")
    if not math.isfinite(aggregate):
        aggregate = 0.0
        warnings.append("non-finite aggregate replaced with zero")

    evidence_level = (
        "E3"
        if assessment and assessment.calibration_version not in {None, "fixture-only"}
        else "E2"
    )
    return ScoreCard(
        task_id=task.task_id,
        submission_id=submission_id,
        render_hash=rendered_value.render_hash if rendered_value else None,
        semantic_assessment_id=assessment.assessment_id if assessment else None,
        dimensions=dimensions,
        critical_gates=gates,
        valid=all(gates.values()),
        aggregate=round(aggregate, 6),
        scorer_version=scorer_version,
        evidence_level=cast(EvidenceLevel, evidence_level),
        warnings=tuple(dict.fromkeys(warnings)),
    )
