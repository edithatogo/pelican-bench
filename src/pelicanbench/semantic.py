"""Source-independent semantic-judge contracts and calibration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Mapping, Protocol

from .io import content_hash
from .models import BenchmarkTask, QuestionAssessment, SemanticAssessment
from .render import RenderedSVG


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


class SemanticAssessor(Protocol):
    assessor_id: str
    assessor_revision: str

    def assess(self, task: BenchmarkTask, rendered: RenderedSVG) -> SemanticAssessment: ...


def questions_for_task(task: BenchmarkTask) -> tuple[AtomicQuestion, ...]:
    questions: list[AtomicQuestion] = [
        AtomicQuestion(
            "animal-present",
            f"Is a {task.animal.label} visibly present?",
            "animal_anatomy",
            True,
        ),
        AtomicQuestion(
            "object-present",
            f"Is a {task.mobile_object.label} visibly present?",
            "vehicle_mechanics",
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
                (
                    f"Is the {task.animal.label} actually in the relation "
                    f"'{relation.predicate}' with the {task.mobile_object.label}?"
                ),
                "interaction",
                relation.required,
                "object-present",
            )
        )
    questions.append(
        AtomicQuestion(
            "scene-coherent",
            "Is the requested scene visually coherent and compositionally readable?",
            "composition",
            False,
        )
    )
    return tuple(questions)


def build_semantic_assessment(
    task: BenchmarkTask,
    rendered: RenderedSVG,
    answers: list[JudgeAnswer],
    *,
    method: str,
    source_independent: bool = True,
    calibration_version: str | None = None,
) -> SemanticAssessment:
    """Freeze visual-judge answers against the exact canonical render."""

    known = {question.question_id: question for question in questions_for_task(task)}
    if len({answer.question_id for answer in answers}) != len(answers):
        raise ValueError("judge answers must contain unique question identifiers")
    assessments: list[QuestionAssessment] = []
    for answer in answers:
        if answer.question_id not in known:
            raise ValueError(f"unknown atomic question: {answer.question_id}")
        question = known[answer.question_id]
        assessments.append(
            QuestionAssessment(
                question_id=answer.question_id,
                dimension=question.dimension,
                probability_yes=answer.probability_yes,
                method=method,
                evidence=(answer.rationale,) if answer.rationale else (),
                judge_id=answer.judge_id,
                judge_revision=answer.judge_revision,
            )
        )
    payload = {
        "task_id": task.task_id,
        "render_hash": rendered.render_hash,
        "source_independent": source_independent,
        "questions": [item.model_dump(mode="json") for item in assessments],
        "calibration_version": calibration_version,
    }
    return SemanticAssessment(
        assessment_id="sem:" + content_hash(payload).split(":", 1)[1][:24],
        task_id=task.task_id,
        render_hash=rendered.render_hash,
        source_independent=source_independent,
        questions=tuple(assessments),
        calibration_version=calibration_version,
    )


class EnsembleSemanticAssessor:
    """Source-independent ensemble over one or more visual judges.

    Judges receive only canonical PNG bytes and one atomic question. Their individual
    answers are aggregated by question, then frozen into one render-bound assessment.
    """

    def __init__(
        self,
        judges: tuple[VisualJudge, ...],
        *,
        family_weights: Mapping[str, float] | None = None,
        calibration_version: str | None = None,
    ) -> None:
        if not judges:
            raise ValueError("at least one visual judge is required")
        identifiers = [(judge.judge_id, judge.judge_revision) for judge in judges]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("visual judge identity and revision pairs must be unique")
        self._judges = judges
        self._family_weights = dict(family_weights or {})
        self._calibration_version = calibration_version
        manifest = {
            "judges": identifiers,
            "weights": self._family_weights,
            "calibration_version": calibration_version,
        }
        digest = content_hash(manifest).split(":", 1)[1]
        self.assessor_id = "pelicanbench/visual-ensemble"
        self.assessor_revision = digest[:16]

    def assess(self, task: BenchmarkTask, rendered: RenderedSVG) -> SemanticAssessment:
        raw_answers: list[JudgeAnswer] = []
        questions = questions_for_task(task)
        for question in questions:
            for judge in self._judges:
                answer = judge.answer(image=rendered.png, question=question)
                if answer.question_id != question.question_id:
                    raise ValueError(
                        f"judge {judge.judge_id} answered {answer.question_id!r} "
                        f"for {question.question_id!r}"
                    )
                if answer.judge_id != judge.judge_id or answer.judge_revision != judge.judge_revision:
                    raise ValueError("judge answer identity does not match the configured judge")
                raw_answers.append(answer)
        aggregated = aggregate_judges(raw_answers, family_weights=self._family_weights)
        member_manifest = ", ".join(
            f"{judge.judge_id}@{judge.judge_revision}" for judge in self._judges
        )
        answers = [
            JudgeAnswer(
                question_id=question.question_id,
                probability_yes=aggregated[question.question_id],
                rationale=f"aggregated source-independent visual judges: {member_manifest}",
                judge_id=self.assessor_id,
                judge_revision=self.assessor_revision,
            )
            for question in questions
        ]
        return build_semantic_assessment(
            task,
            rendered,
            answers,
            method="visual-judge-ensemble",
            source_independent=True,
            calibration_version=self._calibration_version,
        )


class StaticSemanticAssessor:
    """Deterministic assessor for fixtures and scorer-conformance tests only."""

    assessor_id = "pelicanbench/static-fixture"
    assessor_revision = "1"

    def __init__(self, probabilities: Mapping[str, float] | None = None, *, default: float = 1.0):
        if not 0.0 <= default <= 1.0:
            raise ValueError("default probability must be within [0,1]")
        self._probabilities = dict(probabilities or {})
        self._default = default

    def assess(self, task: BenchmarkTask, rendered: RenderedSVG) -> SemanticAssessment:
        answers = [
            JudgeAnswer(
                question_id=question.question_id,
                probability_yes=self._probabilities.get(question.question_id, self._default),
                rationale="deterministic fixture assertion; not empirical model evidence",
                judge_id=self.assessor_id,
                judge_revision=self.assessor_revision,
            )
            for question in questions_for_task(task)
        ]
        return build_semantic_assessment(
            task,
            rendered,
            answers,
            method="fixture-assertion",
            source_independent=True,
            calibration_version="fixture-only",
        )


def validate_semantic_assessment(
    task: BenchmarkTask,
    rendered: RenderedSVG,
    assessment: SemanticAssessment,
) -> tuple[str, ...]:
    errors: list[str] = []
    if assessment.task_id != task.task_id:
        errors.append("semantic assessment task_id does not match")
    if assessment.render_hash != rendered.render_hash:
        errors.append("semantic assessment render_hash does not match canonical render")
    if not assessment.source_independent:
        errors.append("semantic assessment is not declared source-independent")
    required = {q.question_id for q in questions_for_task(task) if q.critical}
    supplied = {item.question_id for item in assessment.questions}
    missing = sorted(required - supplied)
    if missing:
        errors.append("semantic assessment is missing critical questions: " + ", ".join(missing))
    return tuple(errors)


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
