from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.adapters import CallableAdapter, CommandAdapter, DirectoryAdapter, GenerationResult, ModelAdapter
from pelicanbench.io import read_json
from pelicanbench.manifest import artifact_record, build_run_manifest
from pelicanbench.runner import run_benchmark
from pelicanbench.taskgen import heritage_task


def test_artifact_and_manifest(tmp_path: Path, heritage):
    path = tmp_path / "x.txt"
    path.write_text("x")
    record = artifact_record(path, media_type="text/plain", relative_to=tmp_path)
    assert record.path == "x.txt"
    manifest = build_run_manifest(
        tasks=[heritage],
        artifacts=[record],
        benchmark_release=heritage.benchmark_release,
        benchmark_commit="abc",
        model_id="m",
        model_revision="r",
        adapter_id="a",
        environment_digest="env",
        seed=1,
        configuration={"x": 1},
        costs={"usd": 0.1},
    )
    assert manifest.run_id.startswith("run:")
    assert manifest.costs["usd"] == 0.1


def test_run_benchmark(tmp_path: Path, heritage, valid_svg: str, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    adapter = CallableAdapter(lambda _task, _seed: valid_svg)
    result = run_benchmark(
        [heritage],
        adapter,
        output_directory=tmp_path / "run",
        seed=2,
        benchmark_commit="abc",
        environment_digest="env",
    )
    assert result.scorecards[0].valid
    assert result.manifest.created_at == "1970-01-01T00:00:00Z"
    assert (tmp_path / "run/run-manifest.json").exists()
    assert read_json(tmp_path / "run/run-manifest.json")["run_id"] == result.manifest.run_id


def test_directory_adapter(tmp_path: Path, heritage, valid_svg: str):
    path = tmp_path / "pb_heritage-pelican-bike-v1.svg"
    path.write_text(valid_svg)
    adapter = DirectoryAdapter(tmp_path)
    result = adapter.generate(heritage, seed=1)
    assert result.output.startswith("<svg")


def test_command_adapter_success(heritage):
    adapter = CommandAdapter(
        ["python", "-c", "import sys; print('<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>')"],
        adapter_id="cmd",
        model_id="m",
        model_revision="r",
    )
    result = adapter.generate(heritage, seed=7)
    assert result.media_type == "image/svg+xml"


def test_command_adapter_failure(heritage):
    adapter = CommandAdapter(["python", "-c", "raise SystemExit(3)"], adapter_id="cmd", model_id="m", model_revision="r")
    with pytest.raises(RuntimeError):
        adapter.generate(heritage, seed=1)
    with pytest.raises(ValueError):
        CommandAdapter([], adapter_id="x", model_id="m", model_revision="r")


def test_empty_and_mixed_release_rejected(tmp_path: Path, valid_svg: str):
    adapter = CallableAdapter(lambda _task, _seed: valid_svg)
    with pytest.raises(ValueError):
        run_benchmark([], adapter, output_directory=tmp_path, seed=1, benchmark_commit="x", environment_digest="x")
    first = heritage_task(release="A")
    second = heritage_task(release="B")
    with pytest.raises(ValueError):
        run_benchmark([first, second], adapter, output_directory=tmp_path, seed=1, benchmark_commit="x", environment_digest="x")


def test_runner_rejects_task_mismatch(tmp_path: Path, heritage):
    class Bad(ModelAdapter):
        adapter_id = "bad"
        model_id = "bad"
        model_revision = "bad"
        def generate(self, task, *, seed):
            return GenerationResult("other", "<svg/>", "image/svg+xml", None, {})
    with pytest.raises(ValueError):
        run_benchmark([heritage], Bad(), output_directory=tmp_path, seed=1, benchmark_commit="x", environment_digest="x")
