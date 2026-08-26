from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_quality_configuration_is_fail_closed(root: Path) -> None:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["coverage"]["report"]["fail_under"] >= 90
    assert pyproject["tool"]["pyright"]["typeCheckingMode"] == "strict"
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(item.startswith("basedpyright") for item in dev)
    assert any(item.startswith("ty") for item in dev)
    assert not any(item.startswith("mypy") for item in dev)

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


def test_harness_uses_ty_and_basedpyright_not_mypy(root: Path) -> None:
    harness = (root / "scripts/harness.sh").read_text(encoding="utf-8")
    assert "ty check src/pelicanbench" in harness
    assert "basedpyright src/pelicanbench/adapters.py" in harness
    assert "--verifytypes pelicanbench" in harness
    # mypy was retired from the routine gate; its lane must not return silently.
    assert "mypy src/pelicanbench" not in harness
    assert "== Mypy ==" not in harness


def test_harness_optional_conformance_lanes_are_conditional(root: Path) -> None:
    harness = (root / "scripts/harness.sh").read_text(encoding="utf-8")
    # Optional lanes must skip cleanly when the optional toolchain is absent.
    assert "Nightly Rust lane skipped" in harness
    assert "Free-threaded lane skipped" in harness
    assert "command -v python3.14t" in harness
    assert "\"$FT_PYTHON\" -c 'import pytest'" in harness
    assert "interpreter found but pytest is unavailable" in harness
    assert "CI=1 entire status --json" in harness
    assert "\n  entire status\n" not in harness


def test_test_taxonomy_allows_concurrent_unit_execution(root: Path) -> None:
    runner = (root / "scripts/run_test_matrix.py").read_text(encoding="utf-8")
    assert 'CATEGORY_TIMEOUT_SECONDS = {"unit": 600}' in runner
