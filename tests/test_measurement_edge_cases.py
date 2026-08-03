from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pelicanbench.assurance import evaluate_release_readiness
from pelicanbench.calibration import (
    CalibrationCandidate,
    build_pairwise_calibration_tasks,
    disagreement_band,
    score_band,
    select_calibration_sample,
)
from pelicanbench.metamorphic import (
    ChallengeCase,
    _insert_before_svg_close,
    run_scorer_challenges,
)
from pelicanbench.render import SVGRenderError, _connected_components, render_svg
from pelicanbench.render_bridge import render_with_inkscape
from pelicanbench.scoring import score_svg
from pelicanbench.semantic import (
    EnsembleSemanticAssessor,
    JudgeAnswer,
    build_semantic_assessment,
    questions_for_task,
)


def _write_assurance_fixture(tmp_path: Path, assurance: dict, blockers: dict) -> None:
    (tmp_path / "benchmark").mkdir()
    (tmp_path / "conductor").mkdir()
    (tmp_path / "benchmark/assurance-case.json").write_text(json.dumps(assurance))
    (tmp_path / "conductor/release-blockers.json").write_text(json.dumps(blockers))


def test_assurance_rejects_invalid_profiles_and_records(tmp_path: Path):
    assurance = {"claims": [], "release_profiles": {}}
    blockers = {"blockers": []}
    _write_assurance_fixture(tmp_path, assurance, blockers)
    with pytest.raises(KeyError):
        evaluate_release_readiness(tmp_path, profile="missing")

    (tmp_path / "benchmark/assurance-case.json").write_text("[]")
    with pytest.raises(TypeError):
        evaluate_release_readiness(tmp_path, profile="missing")


def test_assurance_reports_unknown_claim_level_and_missing_evidence(tmp_path: Path):
    assurance = {
        "claims": [
            {
                "id": "known",
                "title": "Known",
                "status": "implemented",
                "evidence_level": "E99",
                "evidence": ["missing.txt"],
            }
        ],
        "release_profiles": {
            "alpha": {
                "minimum_evidence_level": "E2",
                "required_claims": ["known", "unknown"],
            }
        },
    }
    blockers = {
        "blockers": [
            {
                "id": "blocker",
                "status": "partial",
                "blocks_profiles": ["alpha"],
                "evidence": ["also-missing.txt"],
            }
        ]
    }
    _write_assurance_fixture(tmp_path, assurance, blockers)
    report = evaluate_release_readiness(tmp_path, profile="alpha")
    assert not report.ready
    assert any("unknown claims" in item for item in report.errors)
    assert any("unknown evidence level" in item for item in report.errors)
    assert report.blocker_results[0].blocks_profile
    assert report.as_dict()["ready"] is False

    assurance["release_profiles"]["alpha"]["minimum_evidence_level"] = "E99"
    (tmp_path / "benchmark/assurance-case.json").write_text(json.dumps(assurance))
    with pytest.raises(ValueError):
        evaluate_release_readiness(tmp_path, profile="alpha")


def test_calibration_input_validation_and_empty_pair_design():
    with pytest.raises(ValueError):
        CalibrationCandidate("", "t", "s", "m", "x", 0.5, 0.1)
    with pytest.raises(ValueError):
        CalibrationCandidate("a", "t", "s", "m", "x", -0.1, 0.1)
    with pytest.raises(ValueError):
        CalibrationCandidate("a", "t", "s", "m", "x", 0.5, 1.1)
    with pytest.raises(ValueError):
        score_band(0.5, lower_boundary=0.8, upper_boundary=0.7)
    with pytest.raises(ValueError):
        disagreement_band(-0.1)
    with pytest.raises(ValueError):
        disagreement_band(0.1, high_threshold=1.0)
    with pytest.raises(ValueError):
        select_calibration_sample([], target=1)
    candidate = CalibrationCandidate("a", "t", "s", "m", "x", 0.5, 0.1)
    with pytest.raises(ValueError):
        select_calibration_sample([candidate], target=0)
    assert build_pairwise_calibration_tasks(select_calibration_sample([candidate], target=1)) == ()
    with pytest.raises(ValueError):
        build_pairwise_calibration_tasks((), maximum_pairs_per_task=0)
    with pytest.raises(ValueError):
        build_pairwise_calibration_tasks((), criteria=())


class _ChangingAssessor:
    assessor_id = "test/changing"
    assessor_revision = "1"

    def __init__(self) -> None:
        self.calls = 0

    def assess(self, task, rendered):
        self.calls += 1
        value = 0.5 if self.calls == 1 else 1.0
        answers = [
            JudgeAnswer(q.question_id, value, "controlled", "test", "1")
            for q in questions_for_task(task)
        ]
        return build_semantic_assessment(
            task,
            rendered,
            answers,
            method="controlled",
            calibration_version="edge-test",
        )


def test_metamorphic_failure_reporting_and_invalid_baseline(heritage, valid_svg: str):
    challenge = ChallengeCase(
        "FAIL",
        "Deliberately change visual and semantic evidence.",
        lambda value: value.replace('fill="orange"', 'fill="blue"'),
        require_full_score_equivalence=True,
    )
    report = run_scorer_challenges(
        heritage,
        valid_svg,
        assessor=_ChangingAssessor(),
        challenges=(challenge,),
    )
    assert not report.passed
    failures = report.outcomes[0].failures
    assert "canonical render changed" in failures
    assert "semantic dimensions changed" in failures
    assert "full score changed" in failures
    assert "aggregate score improved" in failures

    blank = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
    with pytest.raises(ValueError, match="baseline SVG"):
        run_scorer_challenges(heritage, blank)
    with pytest.raises(ValueError, match="closing tag"):
        _insert_before_svg_close("<svg>", "x")


def test_render_and_bridge_error_paths(monkeypatch, valid_svg: str):
    with pytest.raises(SVGRenderError):
        render_svg("<div/>")
    with pytest.raises(ValueError):
        render_svg(valid_svg, size=2)
    with pytest.raises(ValueError):
        _connected_components(np.zeros((2, 2, 2), dtype=bool), minimum_pixels=1)
    blank = render_svg('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    assert not blank.nonblank
    assert blank.bounding_box_fraction == 0

    monkeypatch.setattr("pelicanbench.render_bridge.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="not installed"):
        render_with_inkscape(valid_svg)
    with pytest.raises(ValueError):
        render_with_inkscape("<div/>")


def test_bridge_subprocess_failure(monkeypatch, valid_svg: str):
    monkeypatch.setattr("pelicanbench.render_bridge.shutil.which", lambda _: "/fake/inkscape")
    monkeypatch.setattr(
        "pelicanbench.render_bridge.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stderr=b"failed"),
    )
    with pytest.raises(RuntimeError, match="failed"):
        render_with_inkscape(valid_svg, size=64)


def test_semantic_builder_and_ensemble_reject_malformed_judges(heritage, valid_svg: str):
    rendered = render_svg(valid_svg)
    first = questions_for_task(heritage)[0]
    answer = JudgeAnswer(first.question_id, 0.5, "", "j", "1")
    with pytest.raises(ValueError, match="unique"):
        build_semantic_assessment(heritage, rendered, [answer, answer], method="x")
    with pytest.raises(ValueError, match="unknown"):
        build_semantic_assessment(
            heritage,
            rendered,
            [JudgeAnswer("unknown", 0.5, "", "j", "1")],
            method="x",
        )
    with pytest.raises(ValueError, match="at least one"):
        EnsembleSemanticAssessor(())

    class BadQuestionJudge:
        judge_id = "bad"
        judge_revision = "1"

        def answer(self, *, image, question):
            return JudgeAnswer("wrong", 0.5, "", self.judge_id, self.judge_revision)

    with pytest.raises(ValueError, match="answered"):
        EnsembleSemanticAssessor((BadQuestionJudge(),)).assess(heritage, rendered)

    class BadIdentityJudge:
        judge_id = "bad-id"
        judge_revision = "1"

        def answer(self, *, image, question):
            return JudgeAnswer(question.question_id, 0.5, "", "other", "1")

    with pytest.raises(ValueError, match="identity"):
        EnsembleSemanticAssessor((BadIdentityJudge(),)).assess(heritage, rendered)
    with pytest.raises(ValueError, match="unique"):
        EnsembleSemanticAssessor((BadIdentityJudge(), BadIdentityJudge()))


def test_mismatched_semantic_assessment_is_discarded(heritage, valid_svg: str):
    rendered = render_svg(valid_svg)
    answers = [
        JudgeAnswer(question.question_id, 1.0, "", "j", "1")
        for question in questions_for_task(heritage)
    ]
    assessment = build_semantic_assessment(heritage, rendered, answers, method="test")
    altered = assessment.model_copy(update={"task_id": "wrong-task"})
    score = score_svg(
        heritage,
        valid_svg,
        submission_id="mismatch",
        semantic_assessment=altered,
        rendered=rendered,
    )
    assert not score.valid
    assert any("task_id" in warning or "task" in warning for warning in score.warnings)
