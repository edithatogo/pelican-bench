from pathlib import Path

from pelicanbench.adapters import CallableAdapter
from pelicanbench.runner import run_benchmark
from pelicanbench.taskgen import heritage_task

root = Path(__file__).resolve().parents[2]
svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text()
run_benchmark(
    [heritage_task()],
    CallableAdapter(lambda task, seed: svg),
    output_directory="artifacts/hf-fixture",
    seed=20260801,
    benchmark_commit="hf-job",
    environment_digest="hf-job",
)
