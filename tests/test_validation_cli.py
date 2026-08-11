from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from pelicanbench.cli import app
from pelicanbench.validation import (
    _is_external_repository_path,
    validate_repository,
    validation_exit_code,
)

runner = CliRunner()


def test_external_repository_paths_are_excluded(tmp_path: Path):
    root = tmp_path / "repository"

    assert _is_external_repository_path(root, root / ".git/config")
    assert _is_external_repository_path(root, root / ".venv/lib/package.json")
    assert _is_external_repository_path(root, root / ".agents/plugins/conductor/package.json")
    assert not _is_external_repository_path(root, root / ".agents/plugins/local/plugin.json")
    assert not _is_external_repository_path(root, tmp_path / "other/package.json")


def test_repository_contract(root: Path):
    findings = validate_repository(root)
    # Later evidence files are created by the repository harness; keep the assertion diagnostic.
    errors = [item for item in findings if item.severity == "error"]
    assert not errors, errors
    assert validation_exit_code(findings) == 0


def test_cli_generate_and_fixture(tmp_path: Path, root: Path):
    result = runner.invoke(
        app,
        [
            "generate-tasks",
            "--output",
            str(tmp_path / "tasks.jsonl"),
            "--count",
            "3",
            "--grammar",
            str(root / "benchmark/tasks/grammar.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert len((tmp_path / "tasks.jsonl").read_text().splitlines()) == 3
    result = runner.invoke(app, ["run-fixture", "--output", str(tmp_path / "run")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "run/run-manifest.json").exists()


def test_cli_corpus(tmp_path: Path, root: Path):
    result = runner.invoke(
        app,
        [
            "analyse-corpus",
            "--source",
            str(root / "data/fixtures/corpus.jsonl"),
            "--output",
            str(tmp_path / "ann.jsonl"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "ann.summary.json").exists()
