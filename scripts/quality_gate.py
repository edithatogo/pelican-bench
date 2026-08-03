#!/usr/bin/env python3
"""Aggregate executable local quality evidence into one fail-closed receipt."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object in {path}")
    return value


def _coverage(path: Path) -> dict[str, Any]:
    """Read Cobertura totals using coverage.py's branch-aware weighting.

    Averaging the line and branch rates gives each rate equal weight and does not
    reproduce coverage.py's reported total. The authoritative branch-aware total
    weights every executable line and branch arc once.
    """

    root = ET.parse(path).getroot()
    lines_valid = int(root.attrib.get("lines-valid", "0"))
    lines_covered = int(root.attrib.get("lines-covered", "0"))
    branches_valid = int(root.attrib.get("branches-valid", "0"))
    branches_covered = int(root.attrib.get("branches-covered", "0"))
    denominator = lines_valid + branches_valid
    combined_rate = (lines_covered + branches_covered) / denominator if denominator else 0.0
    line_rate = lines_covered / lines_valid if lines_valid else 0.0
    branch_rate = branches_covered / branches_valid if branches_valid else 0.0
    return {
        "lines_valid": lines_valid,
        "lines_covered": lines_covered,
        "branches_valid": branches_valid,
        "branches_covered": branches_covered,
        "line_percent": round(line_rate * 100, 2),
        "branch_percent": round(branch_rate * 100, 2),
        "combined_percent": round(combined_rate * 100, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/quality-gate.json")
    parser.add_argument("--coverage", default="coverage.xml")
    parser.add_argument("--threshold", type=float, default=90.0)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    evidence_paths = {
        "static_audit": root / "artifacts/static-audit.json",
        "prose_audit": root / "artifacts/prose-audit.json",
        "test_taxonomy": root / "artifacts/test-taxonomy.json",
        "mutation_smoke": root / "artifacts/mutation-smoke.json",
        "toolchain_preflight": root / "artifacts/toolchain-preflight.json",
    }
    missing = [name for name, path in evidence_paths.items() if not path.exists()]
    evidence = {name: _load(path) for name, path in evidence_paths.items() if path.exists()}
    coverage_path = root / args.coverage
    coverage = _coverage(coverage_path) if coverage_path.exists() else None
    gates = {
        "evidence_complete": not missing,
        "static_audit": bool(evidence.get("static_audit", {}).get("passed")),
        "prose_audit": bool(evidence.get("prose_audit", {}).get("passed")),
        "test_taxonomy": bool(evidence.get("test_taxonomy", {}).get("passed")),
        "mutation_smoke": bool(evidence.get("mutation_smoke", {}).get("passed")),
        "coverage_line": coverage is not None and coverage["line_percent"] >= args.threshold,
        "coverage_combined": coverage is not None
        and coverage["combined_percent"] >= args.threshold,
    }
    payload = {
        "schema_version": "1.0.0",
        "threshold_percent": args.threshold,
        "coverage": coverage,
        "missing_evidence": missing,
        "gates": gates,
        "passed": all(gates.values()),
        "external_tool_state": evidence.get("toolchain_preflight", {}),
        "claim": (
            "This receipt covers repository-native evidence. CI remains "
            "authoritative for Ruff, mypy, Pyright, Vale, Hypothesis, and "
            "full mutmut execution."
        ),
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
