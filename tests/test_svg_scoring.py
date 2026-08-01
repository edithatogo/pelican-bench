from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.io import content_hash
from pelicanbench.scoring import DEFAULT_WEIGHTS, score_svg
from pelicanbench.svg import SVGSecurityError, assert_safe_svg, inspect_svg


def test_valid_svg_features(valid_svg: str):
    inspection = inspect_svg(valid_svg)
    assert inspection.valid
    assert inspection.canonical_hash
    assert inspection.features["wheel_candidate_count"] >= 2
    assert inspection.features["role_groups"]["pelican_pouch"]
    assert inspection.features["role_groups"]["contact"]


def test_valid_svg_score(heritage, valid_svg: str):
    score = score_svg(heritage, valid_svg, submission_id=content_hash(valid_svg))
    assert score.valid
    assert score.aggregate >= 0.95
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
    assert "visible text may create a semantic shortcut" in score.warnings


def test_canonical_hash_ignores_attribute_order():
    a = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="1" cy="2" r="3"/></svg>'
    b = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="3" cy="2" cx="1"/></svg>'
    assert inspect_svg(a).canonical_hash == inspect_svg(b).canonical_hash


def test_bad_xml():
    result = inspect_svg("<svg><path></svg>")
    assert not result.valid
    assert "XML parse failure" in result.errors[0]
