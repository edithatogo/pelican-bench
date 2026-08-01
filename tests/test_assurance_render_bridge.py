from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pelicanbench.assurance import evaluate_release_readiness
from pelicanbench.cli import app
from pelicanbench.render_bridge import compare_renderers

runner = CliRunner()


def test_release_profiles(root: Path):
    alpha = evaluate_release_readiness(root, profile="v0.2-alpha")
    assert alpha.ready, alpha.as_dict()
    v1 = evaluate_release_readiness(root, profile="v1.0")
    assert not v1.ready
    assert any(item.blocks_profile for item in v1.blocker_results)


def test_release_readiness_cli(root: Path):
    alpha = runner.invoke(
        app,
        ["release-readiness", "--root", str(root), "--profile", "v0.2-alpha"],
    )
    assert alpha.exit_code == 0, alpha.output
    assert "READY" in alpha.output
    v1 = runner.invoke(
        app,
        ["release-readiness", "--root", str(root), "--profile", "v1.0"],
    )
    assert v1.exit_code == 1
    assert "NOT_READY" in v1.output


@pytest.mark.skipif(shutil.which("inkscape") is None, reason="Inkscape not installed")
def test_inkscape_bridge(valid_svg: str):
    result = compare_renderers(valid_svg, size=256)
    assert result.canonical_hash.startswith("sha256:")
    assert result.bridge_hash.startswith("sha256:")
    assert 0 <= result.mean_absolute_error <= 1
    assert 0 <= result.differing_pixel_fraction <= 1
    assert not result.materially_different
