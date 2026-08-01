from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.adapters import CallableAdapter, CommandAdapter, DirectoryAdapter, GenerationResult, ModelAdapter
from pelicanbench.io import read_json
from pelicanbench.manifest import artifact_record, build_run_manifest
from pelicanbench.runner import run_benchmark
from pelicanbench.semantic import StaticSemanticAssessor
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
        semantic_assessor=StaticSemanticAssessor(),
    )
    assert result.scorecards[0].valid
    assert result.manifest.created_at == "1970-01-01T00:00:00Z"
    assert (tmp_path / "run/run-manifest.json").exists()
    assert read_json(tmp_path / "run/run-manifest.json")["run_id"] == result.manifest.run_id
    assert (tmp_path / "run/trials.jsonl").exists()
    assert (tmp_path / "run/evaluations.jsonl").exists()
    assert (tmp_path / "run/prov.jsonld").exists()
    assert (tmp_path / "run/ro-crate-metadata.json").exists()
    assert (tmp_path / "run/reproduce.sh").exists()
    assert any((tmp_path / "run/renders").glob("*.png"))


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


def test_run_without_semantic_assessor_is_explicitly_unvalidated(
    tmp_path: Path, heritage, valid_svg: str
):
    result = run_benchmark(
        [heritage],
        CallableAdapter(lambda _task, _seed: valid_svg),
        output_directory=tmp_path / "unassessed",
        seed=4,
        benchmark_commit="abc",
        environment_digest="env",
    )
    score = result.scorecards[0]
    assert not score.valid
    assert score.semantic_assessment_id is None
    assert not score.critical_gates["source_independent_semantics"]
    assert result.trials[0].scenario_id == heritage.scenario_id
    assert result.evaluations[0].trial_id == result.trials[0].trial_id


def test_command_adapter_does_not_inherit_unlisted_secrets(heritage, monkeypatch):
    monkeypatch.setenv("PELICANBENCH_TEST_SECRET", "should-not-leak")
    adapter = CommandAdapter(
        [
            "python",
            "-c",
            (
                "import os; "
                "print('<svg xmlns=\"http://www.w3.org/2000/svg\">' "
                "+ str('PELICANBENCH_TEST_SECRET' in os.environ) + '</svg>')"
            ),
        ],
        adapter_id="cmd",
        model_id="m",
        model_revision="r",
    )
    result = adapter.generate(heritage, seed=1)
    assert "False" in result.output
    with pytest.raises(ValueError):
        CommandAdapter(
            ["python"],
            adapter_id="cmd",
            model_id="m",
            model_revision="r",
            timeout_seconds=0,
        )


def test_retrying_and_checkpointing_adapters(tmp_path: Path, heritage, valid_svg: str):
    from pelicanbench.adapters import CheckpointingAdapter, RetryingAdapter

    calls = {"count": 0}

    def flaky(_task, _seed):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient")
        return valid_svg

    retrying = RetryingAdapter(CallableAdapter(flaky), max_attempts=2)
    checkpointed = CheckpointingAdapter(retrying, tmp_path / "checkpoints")
    first = checkpointed.generate(heritage, seed=9)
    second = checkpointed.generate(heritage, seed=9)
    assert first.metadata["checkpoint_status"] == "miss"
    assert first.metadata["attempts"] == 2
    assert second.metadata["checkpoint_status"] == "hit"
    assert calls["count"] == 2

    exhausted = RetryingAdapter(
        CallableAdapter(lambda _task, _seed: (_ for _ in ()).throw(RuntimeError("no"))),
        max_attempts=2,
    )
    with pytest.raises(RuntimeError, match="after 2 attempts") as captured:
        exhausted.generate(heritage, seed=1)
    assert getattr(captured.value, "attempts") == 2


def test_runner_retains_generation_failures(tmp_path: Path, heritage):
    adapter = CallableAdapter(
        lambda _task, _seed: (_ for _ in ()).throw(RuntimeError("provider unavailable"))
    )
    result = run_benchmark(
        [heritage],
        adapter,
        output_directory=tmp_path / "failed-run",
        seed=11,
        benchmark_commit="abc",
        environment_digest="env",
        continue_on_error=True,
    )
    assert result.scorecards == ()
    assert len(result.trials) == 1
    assert len(result.failures) == 1
    assert result.trials[0].status == "generation-failed"
    assert result.trials[0].artifact_id is None
    assert result.manifest.configuration["failure_count"] == 1
    assert (tmp_path / "failed-run/failures.jsonl").read_text(encoding="utf-8").strip()
    provenance = read_json(tmp_path / "failed-run/prov.jsonld")
    assert any(item.get("pb:status") == "generation-failed" for item in provenance["@graph"])
