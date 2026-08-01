from __future__ import annotations

import random

import pytest

from pelicanbench.fuzzing import run_svg_fuzz_campaign


def test_bounded_svg_fuzz_campaign_has_no_unhandled_failures(valid_svg: str):
    report = run_svg_fuzz_campaign(valid_svg, cases=39, seed=17, budget_ms=1000)
    assert report.passed, report.as_dict()
    assert report.cases == report.accepted + report.rejected
    assert report.rendered + report.render_rejected == report.accepted
    assert report.maximum_elapsed_ms >= 0


def test_fuzz_campaign_reports_mutator_crashes_and_validates_inputs(valid_svg: str):
    def crash(_svg: str, _rng: random.Random) -> str:
        raise RuntimeError("controlled")

    report = run_svg_fuzz_campaign(
        valid_svg,
        cases=1,
        mutations=(("crash", crash),),
    )
    assert not report.passed
    assert report.failures[0].error_type == "RuntimeError"
    assert report.as_dict()["passed"] is False

    with pytest.raises(ValueError):
        run_svg_fuzz_campaign(valid_svg, cases=0)
    with pytest.raises(ValueError):
        run_svg_fuzz_campaign(valid_svg, budget_ms=0)
    with pytest.raises(ValueError):
        run_svg_fuzz_campaign(valid_svg, mutations=())
