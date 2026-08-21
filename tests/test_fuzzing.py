from __future__ import annotations

import random

import pytest

from pelicanbench.fuzzing import (
    run_coverage_guided_svg_fuzz_campaign,
    run_svg_fuzz_campaign,
)


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


def test_coverage_guided_fuzz_campaign_has_no_unhandled_failures(valid_svg: str):
    report = run_coverage_guided_svg_fuzz_campaign(
        valid_svg,
        cases=14,
        seed=23,
        budget_ms=2000,
    )
    assert report.passed, report.as_dict()
    assert report.cases == report.accepted + report.rejected
    assert report.rendered + report.render_rejected == report.accepted
    # Coverage telemetry is optional; the loop remains deterministic either way.
    assert isinstance(report.coverage_guided, bool)
    assert report.coverage_lines >= 0
    payload = report.as_dict()
    assert "coverage_guided" in payload
    assert "coverage_lines" in payload

    with pytest.raises(ValueError):
        run_coverage_guided_svg_fuzz_campaign(valid_svg, cases=0)
    with pytest.raises(ValueError):
        run_coverage_guided_svg_fuzz_campaign(valid_svg, budget_ms=0)
    with pytest.raises(ValueError):
        run_coverage_guided_svg_fuzz_campaign(valid_svg, mutations=())


def test_coverage_guided_fuzz_campaign_updates_guidance_deterministically(
    valid_svg: str,
):
    # The loop always runs a stdlib ``trace``-guided campaign; the first cases must
    # accumulate parser/renderer coverage and stay within the per-case budget.
    reports = [
        run_coverage_guided_svg_fuzz_campaign(
            valid_svg,
            cases=6,
            seed=seed,
            budget_ms=5000,
        )
        for seed in (7, 7)
    ]
    assert reports[0].passed, reports[0].as_dict()
    assert reports[0].coverage_guided is True
    # Counts and coverage telemetry are deterministic across a repeated seed;
    # only the wall-clock maximum_elapsed_ms differs.
    a = {k: v for k, v in reports[0].as_dict().items() if k != "maximum_elapsed_ms"}
    b = {k: v for k, v in reports[1].as_dict().items() if k != "maximum_elapsed_ms"}
    assert a == b
