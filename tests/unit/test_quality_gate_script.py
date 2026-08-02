from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_quality_gate():
    path = Path(__file__).parents[2] / "scripts/quality_gate.py"
    spec = importlib.util.spec_from_file_location("quality_gate_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_coverage_uses_weighted_line_and_branch_opportunities(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.xml"
    coverage.write_text(
        '<coverage lines-valid="100" lines-covered="95" '
        'branches-valid="20" branches-covered="15" '
        'line-rate="0.95" branch-rate="0.75"/>',
        encoding="utf-8",
    )

    result = _load_quality_gate()._coverage(coverage)

    assert result["line_percent"] == 95.0
    assert result["branch_percent"] == 75.0
    assert result["combined_percent"] == 91.67
    assert result["lines_valid"] == 100
    assert result["branches_covered"] == 15
