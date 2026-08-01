from __future__ import annotations

from pelicanbench.metamorphic import (
    add_offcanvas_labelled_shape,
    add_source_comment,
    add_transparent_labelled_shape,
    rename_source_labels,
    run_scorer_challenges,
    strip_source_labels,
)
from pelicanbench.render import render_svg


def test_all_normative_scorer_challenges_pass(heritage, valid_svg: str):
    report = run_scorer_challenges(heritage, valid_svg)
    assert report.passed
    assert len(report.outcomes) == 5
    assert all(item.semantic_dimensions_equal for item in report.outcomes)
    assert all(item.aggregate_not_improved for item in report.outcomes)


def test_metadata_transformations_are_render_invariant(valid_svg: str):
    baseline = render_svg(valid_svg).render_hash
    transformed = (
        strip_source_labels(valid_svg),
        rename_source_labels(valid_svg),
        add_source_comment(valid_svg),
        add_transparent_labelled_shape(valid_svg),
        add_offcanvas_labelled_shape(valid_svg),
    )
    assert all(render_svg(item).render_hash == baseline for item in transformed)
