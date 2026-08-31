"""Explorer callback is testable without importing or launching Gradio."""

import json

import pytest

from pelicanbench.explorer import evaluate
from pelicanbench.scoring import score_svg
from pelicanbench.taskgen import heritage_task


def test_callback_preserves_existing_scorecard(valid_svg):
    summary, details = evaluate(valid_svg)
    expected = score_svg(heritage_task(), valid_svg, submission_id="interactive")
    assert summary == f"Aggregate: {expected.aggregate:.3f} | Critical success: {expected.valid}"
    assert json.loads(details) == expected.model_dump(mode="json")
    assert expected.valid is False  # No human/model semantic assessment supplied.


@pytest.mark.parametrize(
    "source",
    [
        "",
        "<svg>",
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///sentinel">]><svg>&x;</svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://invalid.invalid/x"/></svg>',
        "x" * 2_000_001,
    ],
)
def test_malformed_unsafe_and_oversized_input_never_renders(source, monkeypatch):
    def unexpected_render(*args, **kwargs):
        raise AssertionError("invalid input reached renderer")

    monkeypatch.setattr("pelicanbench.scoring.render_svg", unexpected_render)
    summary, details = evaluate(source)
    assert "Critical success: False" in summary
    assert json.loads(details)["valid"] is False


@pytest.mark.parametrize("source", [None, 1, {}, b"svg"])
def test_non_text_rejected_without_echo(source):
    with pytest.raises(TypeError, match="SVG source must be text"):
        evaluate(source)
