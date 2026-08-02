from __future__ import annotations

import pytest

from pelicanbench.human_eval import PairwiseVote, fit_bradley_terry, probability_superior
from pelicanbench.render import render_svg
from pelicanbench.semantic import (
    EnsembleSemanticAssessor,
    JudgeAnswer,
    aggregate_judges,
    calibration_error,
    questions_for_task,
    validate_semantic_assessment,
)
from pelicanbench.statistics import (
    Observation,
    estimate_interaction,
    hierarchical_shrink_interactions,
    rank_with_uncertainty,
    replicate_reliability,
    superiority_probabilities,
)


def test_atomic_questions(heritage):
    questions = questions_for_task(heritage)
    assert questions[0].critical
    assert any(question.question_id == "relation:rides_on" for question in questions)
    expected = (
        2
        + len(heritage.animal.required_features)
        + len(heritage.mobile_object.required_features)
        + len(heritage.relations)
        + 1
    )
    assert len(questions) == expected


def test_judge_aggregation_and_calibration():
    answers = [
        JudgeAnswer("q", 0.8, "yes", "a", "1"),
        JudgeAnswer("q", 0.2, "no", "b", "1"),
    ]
    assert aggregate_judges(answers)["q"] == pytest.approx(0.5)
    assert aggregate_judges(answers, family_weights={"a": 3, "b": 1})["q"] == pytest.approx(0.65)
    assert calibration_error([0.9, 0.1], [1, 0], bins=2) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        JudgeAnswer("q", 2, "", "a", "1")
    with pytest.raises(ValueError):
        aggregate_judges(answers, family_weights={"a": 0, "b": 0})
    with pytest.raises(ValueError):
        calibration_error([], [])


def test_bradley_terry():
    votes = [
        PairwiseVote("t", "a", "b", "a", "r1"),
        PairwiseVote("t", "a", "b", "a", "r2"),
        PairwiseVote("t", "a", "b", "tie", "r3"),
    ]
    scores = fit_bradley_terry(votes, iterations=200)
    assert scores["a"] > scores["b"]
    assert probability_superior(scores["a"], scores["b"]) > 0.5
    with pytest.raises(ValueError):
        PairwiseVote("t", "a", "a", "a", "r")
    with pytest.raises(ValueError):
        fit_bradley_terry([])


def fixture_observations():
    rows=[]
    for model,boost in [("m1",0.15),("m2",0.0)]:
        for animal,a_effect in [("pelican",0.1),("cat",0.0),("dog",0.02)]:
            for obj,o_effect in [("bicycle",0.05),("tuk-tuk",0.0),("skateboard",-0.02)]:
                score=0.5+a_effect+o_effect+(boost if animal=="pelican" and obj=="bicycle" else 0)
                rows.append(Observation(model,animal,obj,score))
    return rows


def test_pelicanmaxxing_interaction():
    estimates = estimate_interaction(fixture_observations(), bootstrap_samples=100, seed=1)
    by_model = {item.model_id:item for item in estimates}
    assert by_model["m1"].interaction > by_model["m2"].interaction
    assert rank_with_uncertainty(estimates)[0].model_id == "m1"
    assert by_model["m1"].ci_low <= by_model["m1"].ci_high


def test_observation_validation():
    with pytest.raises(ValueError):
        Observation("m", "a", "o", 2)


class _Judge:
    def __init__(self, judge_id: str, value: float):
        self.judge_id = judge_id
        self.judge_revision = "1"
        self.value = value

    def answer(self, *, image: bytes, question):
        assert image.startswith(b"\x89PNG")
        return JudgeAnswer(
            question.question_id,
            self.value,
            "blind render assessment",
            self.judge_id,
            self.judge_revision,
        )


def test_source_independent_ensemble(heritage, valid_svg: str):
    rendered = render_svg(valid_svg)
    assessor = EnsembleSemanticAssessor(
        (_Judge("family-a", 0.8), _Judge("family-b", 0.4)),
        family_weights={"family-a": 3, "family-b": 1},
        calibration_version="cal-v0",
    )
    assessment = assessor.assess(heritage, rendered)
    assert not validate_semantic_assessment(heritage, rendered, assessment)
    assert all(value == pytest.approx(0.7) for value in assessment.probabilities().values())
    assert assessment.calibration_version == "cal-v0"


def test_interaction_shrinkage_reliability_and_superiority():
    rows = []
    for replicate in range(1, 4):
        for row in fixture_observations():
            rows.append(
                Observation(
                    row.model_id,
                    row.animal,
                    row.mobile_object,
                    min(1.0, max(0.0, row.score + (replicate - 2) * 0.01)),
                    relation=row.relation,
                    replicate=replicate,
                )
            )
    estimates = estimate_interaction(rows, bootstrap_samples=100, seed=2)
    shrunk = hierarchical_shrink_interactions(estimates)
    assert {item.model_id for item in shrunk} == {"m1", "m2"}
    assert all(0 <= item.shrinkage_weight <= 1 for item in shrunk)
    reliability = replicate_reliability(rows)
    assert reliability.mean_replicates == pytest.approx(3)
    assert 0 <= reliability.reliability <= 1
    probabilities = superiority_probabilities(estimates)
    assert probabilities[("m1", "m2")] > 0.5
    assert probabilities[("m2", "m1")] < 0.5
