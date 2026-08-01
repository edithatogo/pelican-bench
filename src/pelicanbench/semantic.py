"""Semantic-judge contracts, atomic questions, and calibration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Protocol

from .models import BenchmarkTask


@dataclass(frozen=True, slots=True)
class AtomicQuestion:
    question_id: str
    text: str
    dimension: str
    critical: bool
    dependency: str | None = None


@dataclass(frozen=True, slots=True)
class JudgeAnswer:
    question_id: str
    probability_yes: float
    rationale: str
    judge_id: str
    judge_revision: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability_yes <= 1.0:
            raise ValueError("probability_yes must be within [0,1]")


class VisualJudge(Protocol):
    judge_id: str
    judge_revision: str

    def answer(self, *, image: bytes, question: AtomicQuestion) -> JudgeAnswer: ...


def questions_for_task(task: BenchmarkTask) -> tuple[AtomicQuestion, ...]:
    questions: list[AtomicQuestion] = [
        AtomicQuestion(
            "animal-present",
            f"Is a {task.animal.label} visibly present?",
            "recognisability",
            True,
        ),
        AtomicQuestion(
            "object-present",
            f"Is a {task.mobile_object.label} visibly present?",
            "recognisability",
            True,
        ),
    ]
    for feature in task.animal.required_features:
        questions.append(
            AtomicQuestion(
                f"animal-feature:{feature}",
                f"Does the {task.animal.label} visibly have the feature '{feature}'?",
                "animal_anatomy",
                False,
                "animal-present",
            )
        )
    for feature in task.mobile_object.required_features:
        questions.append(
            AtomicQuestion(
                f"object-feature:{feature}",
                f"Does the {task.mobile_object.label} visibly have the component '{feature}'?",
                "vehicle_mechanics",
                False,
                "object-present",
            )
        )
    for relation in task.relations:
        questions.append(
            AtomicQuestion(
                f"relation:{relation.predicate}",
                f"Is the {task.animal.label} actually in the relation '{relation.predicate}' with the {task.mobile_object.label}?",
                "interaction",
                relation.required,
                "object-present",
            )
        )
    return tuple(questions)


def aggregate_judges(
    answers: list[JudgeAnswer],
    *,
    family_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    grouped: dict[str, list[tuple[float, float]]] = {}
    for answer in answers:
        weight = (family_weights or {}).get(answer.judge_id, 1.0)
        grouped.setdefault(answer.question_id, []).append((answer.probability_yes, weight))
    output: dict[str, float] = {}
    for question_id, values in grouped.items():
        denominator = sum(weight for _, weight in values)
        if denominator <= 0:
            raise ValueError("judge weights must sum to a positive value")
        output[question_id] = sum(value * weight for value, weight in values) / denominator
    return output


def calibration_error(predictions: list[float], outcomes: list[int], *, bins: int = 10) -> float:
    if len(predictions) != len(outcomes) or not predictions:
        raise ValueError("predictions and outcomes must be non-empty and aligned")
    if bins < 1:
        raise ValueError("bins must be positive")
    weighted_errors: list[float] = []
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        selected = [
            item
            for item, prediction in enumerate(predictions)
            if low <= prediction < high or (index == bins - 1 and prediction == 1.0)
        ]
        if not selected:
            continue
        confidence = mean(predictions[item] for item in selected)
        accuracy = mean(outcomes[item] for item in selected)
        weighted_errors.extend([abs(confidence - accuracy)] * len(selected))
    return mean(weighted_errors)
