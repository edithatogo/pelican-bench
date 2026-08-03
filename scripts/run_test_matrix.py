#!/usr/bin/env python3
"""Run every PelicanBench test taxonomy as an independently failing suite."""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CategoryResult:
    category: str
    returncode: int
    duration_seconds: float
    output_tail: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


CATEGORY_SELECTORS: dict[str, tuple[str, ...]] = {
    # Unit tests include the historical root-level tests, which are classified by
    # tests/conftest.py. The remaining categories use narrow paths to minimise
    # collection overhead while preserving marker-based classification in CI.
    "unit": ("-m", "unit", "tests"),
    "integration": ("tests/integration",),
    "e2e": ("tests/e2e",),
    "property": ("tests/property",),
    "mutation": ("tests/mutation",),
    "edge": ("tests/edge",),
    "dst": ("tests/dst",),
    "contract": ("tests/integration/test_consumer_contracts.py",),
    "metamorphic": ("tests/test_metamorphic.py",),
    "agent": ("tests/agent", "tests/autonomous"),
    "autonomous": ("tests/autonomous",),
}

DEFAULT_CATEGORY_TIMEOUT_SECONDS = 60
CATEGORY_TIMEOUT_SECONDS = {"unit": 120}

CATEGORIES = tuple(CATEGORY_SELECTORS)


def run_category(root: Path, category: str) -> CategoryResult:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    timeout_seconds = CATEGORY_TIMEOUT_SECONDS.get(category, DEFAULT_CATEGORY_TIMEOUT_SECONDS)
    started = time.monotonic()
    try:
        completed = subprocess.run(  # nosec B603
            [sys.executable, "-m", "pytest", "-q", *CATEGORY_SELECTORS[category]],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output = (stdout + "\n" + stderr).strip()
        return CategoryResult(
            category=category,
            returncode=124,
            duration_seconds=round(duration, 3),
            output_tail=(
                f"category timed out after {timeout_seconds}s\n"
                + "\n".join(output.splitlines()[-11:])
            ),
        )
    duration = time.monotonic() - started
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return CategoryResult(
        category=category,
        returncode=completed.returncode,
        duration_seconds=round(duration, 3),
        output_tail="\n".join(output.splitlines()[-12:]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/test-taxonomy.json")
    parser.add_argument("--category", action="append", choices=CATEGORIES)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    categories = tuple(args.category or CATEGORIES)
    results = tuple(run_category(root, category) for category in categories)
    payload = {
        "schema_version": "1.0.0",
        "categories": [asdict(result) | {"passed": result.passed} for result in results],
        "categories_total": len(results),
        "categories_passed": sum(result.passed for result in results),
        "passed": all(result.passed for result in results),
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
