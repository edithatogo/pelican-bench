from __future__ import annotations

import re
from pathlib import Path

import pytest

from pelicanbench.io import content_hash
from pelicanbench.render import render_svg
from pelicanbench.scoring import DEFAULT_WEIGHTS, score_svg
from pelicanbench.semantic import StaticSemanticAssessor
from pelicanbench.svg import SVGSecurityError, assert_safe_svg, inspect_svg


def _perfect_assessment(task, svg: str):
    rendered = render_svg(svg)
    return rendered, StaticSemanticAssessor().assess(task, rendered)


def test_valid_svg_features(valid_svg: str):
    inspection = inspect_svg(valid_svg)
    assert inspection.valid
    assert inspection.canonical_hash
    assert inspection.features["wheel_candidate_count"] >= 2
    assert inspection.features["visible_shape_count"] >= 8
    assert "pouch" in inspection.features["declared_role_counts"]


def test_valid_svg_requires_source_independent_semantics(heritage, valid_svg: str):
    unassessed = score_svg(heritage, valid_svg, submission_id=content_hash(valid_svg))
    assert not unassessed.valid
    assert not unassessed.critical_gates["semantic_assessment_complete"]
    assert unassessed.dimensions[1].value == 0

    rendered, assessment = _perfect_assessment(heritage, valid_svg)
    score = score_svg(
        heritage,
        valid_svg,
        submission_id=content_hash(valid_svg),
        semantic_assessment=assessment,
        rendered=rendered,
    )
    assert score.valid
    assert score.aggregate >= 0.85
    assert all(score.critical_gates.values())
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1)


def test_broken_svg_score(heritage, broken_svg: str):
    score = score_svg(heritage, broken_svg, submission_id="broken")
    assert score.aggregate < 0.75
    assert not score.valid
    assert score.critical_gates["interaction_minimum"] is False


@pytest.mark.parametrize("filename", ["script.svg", "external-image.svg", "event-handler.svg", "entity.svg"])
def test_malicious_fixtures_rejected(root: Path, filename: str):
    svg = (root / "benchmark/fixtures/malicious" / filename).read_text()
    inspection = inspect_svg(svg)
    assert not inspection.valid
    assert inspection.errors
    with pytest.raises(SVGSecurityError):
        assert_safe_svg(svg)


def test_wrong_root_and_unknown_tag():
    assert not inspect_svg("<div/>").valid
    assert not inspect_svg('<svg xmlns="http://www.w3.org/2000/svg"><animate/></svg>').valid


def test_size_and_path_limits():
    assert not inspect_svg("<svg>" + "x" * 100 + "</svg>", max_bytes=10).valid
    huge_path = '<svg xmlns="http://www.w3.org/2000/svg"><path d="' + "M0 0 " * 100 + '"/></svg>'
    assert not inspect_svg(huge_path, max_path_characters=10).valid


def test_visible_text_warns(heritage):
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>pelican riding bicycle</text></svg>'
    inspection = inspect_svg(svg)
    assert inspection.valid
    assert inspection.warnings
    score = score_svg(heritage, svg, submission_id="text")
    assert "visible text may create a visual semantic shortcut" in score.warnings


def test_canonical_hash_ignores_attribute_order():
    a = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="1" cy="2" r="3"/></svg>'
    b = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="3" cy="2" cx="1"/></svg>'
    assert inspect_svg(a).canonical_hash == inspect_svg(b).canonical_hash


def test_bad_xml():
    result = inspect_svg("<svg><path></svg>")
    assert not result.valid
    assert "XML parse failure" in result.errors[0]


def test_source_label_injection_cannot_create_semantic_credit(root: Path, heritage):
    svg = (root / "benchmark/fixtures/adversarial/semantic-label-injection.svg").read_text()
    inspection = inspect_svg(svg)
    assert inspection.features["hidden_shape_count"] >= 1
    assert "pelican" in inspection.features["declared_role_counts"]
    score = score_svg(heritage, svg, submission_id="injection")
    by_name = {item.name: item.value for item in score.dimensions}
    assert by_name["animal_anatomy"] == 0
    assert by_name["vehicle_mechanics"] == 0
    assert by_name["interaction"] == 0
    assert not score.valid


def test_semantic_scores_are_invariant_to_ids_and_classes(heritage, valid_svg: str):
    stripped = re.sub(r'\s(?:id|class|data-role|aria-label)="[^"]*"', "", valid_svg)
    original_render = render_svg(valid_svg)
    stripped_render = render_svg(stripped)
    assert original_render.render_hash == stripped_render.render_hash
    assessment = StaticSemanticAssessor().assess(heritage, original_render)
    original = score_svg(
        heritage,
        valid_svg,
        submission_id="original",
        semantic_assessment=assessment,
        rendered=original_render,
    )
    relabelled = score_svg(
        heritage,
        stripped,
        submission_id="stripped",
        semantic_assessment=assessment,
        rendered=stripped_render,
    )
    assert original.aggregate == relabelled.aggregate
    assert original.dimensions == relabelled.dimensions


def test_invisible_labelled_elements_cannot_improve_score(heritage, valid_svg: str):
    injected = valid_svg.replace(
        "</svg>",
        '<rect opacity="0" id="pelican-pouch-pedal-rider-contact" x="0" y="0" width="2" height="2"/></svg>',
    )
    original_render = render_svg(valid_svg)
    injected_render = render_svg(injected)
    assert original_render.render_hash == injected_render.render_hash
    assessment = StaticSemanticAssessor().assess(heritage, original_render)
    original = score_svg(
        heritage,
        valid_svg,
        submission_id="original",
        semantic_assessment=assessment,
        rendered=original_render,
    )
    manipulated = score_svg(
        heritage,
        injected,
        submission_id="injected",
        semantic_assessment=assessment,
        rendered=injected_render,
    )
    assert manipulated.aggregate <= original.aggregate
    assert "hidden or non-rendered shapes are excluded from visual evidence" in manipulated.warnings
