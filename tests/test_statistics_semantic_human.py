from __future__ import annotations

import pytest

from pelicanbench.human_eval import PairwiseVote, fit_bradley_terry, probability_superior
from pelicanbench.semantic import JudgeAnswer, aggregate_judges, calibration_error, questions_for_task
from pelicanbench.statistics import Observation, estimate_interaction, rank_with_uncertainty


def test_atomic_questions(heritage):
    questions = questions_for_task(heritage)
    assert questions[0].critical
    assert any(question.question_id == "relation:rides_on" for question in questions)
    assert len(questions) == 2 + len(heritage.animal.required_features) + len(heritage.mobile_object.required_features) + 1


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
