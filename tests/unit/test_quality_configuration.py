from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_quality_configuration_is_fail_closed(root: Path) -> None:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["coverage"]["report"]["fail_under"] >= 90
    assert pyproject["tool"]["mypy"]["strict"] is True
    assert pyproject["tool"]["pyright"]["typeCheckingMode"] == "strict"

    codecov = (root / "codecov.yml").read_text(encoding="utf-8")
    assert "target: 90%" in codecov
    assert "informational: false" in codecov

    renovate = json.loads((root / "renovate.json").read_text(encoding="utf-8"))
    assert "helpers:pinGitHubActionDigests" in renovate["extends"]
    assert renovate["rollbackPrs"] is True


def test_vale_policy_is_repository_local(root: Path) -> None:
    config = (root / ".vale.ini").read_text(encoding="utf-8")
    assert "StylesPath = .github/styles" in config
    styles = {path.name for path in (root / ".github/styles/PelicanBench").glob("*.yml")}
    assert styles >= {"Terminology.yml", "Maturity.yml", "Editorial.yml"}
