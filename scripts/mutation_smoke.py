#!/usr/bin/env python3
"""Run a deterministic, dependency-free mutation-smoke campaign.

This is not a replacement for the scheduled full ``mutmut`` campaign. It provides a
mandatory local and CI gate that proves critical tests kill known realistic mutations even
when the optional mutation framework is unavailable. Infrastructure failures are reported
separately and never counted as killed mutants.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class Mutant:
    mutant_id: str
    relative_path: str
    before: str
    after: str
    test_name: str


@dataclass(frozen=True, slots=True)
class MutantResult:
    mutant_id: str
    status: Literal["killed", "survived", "infrastructure-error"]
    returncode: int
    output_tail: str

    @property
    def killed(self) -> bool:
        return self.status == "killed"


MUTANTS = (
    Mutant(
        "M-CANVAS-LIMIT",
        "canvas.py",
        "if len(self.elements) >= self.max_elements:",
        "if len(self.elements) > self.max_elements:",
        "test_kills_canvas_limit_boundary_mutant",
    ),
    Mutant(
        "M-PILOT-EMPTY-TASKS",
        "pilot.py",
        "if not tasks:",
        "if False and not tasks:",
        "test_kills_empty_task_acceptance_mutant",
    ),
    Mutant(
        "M-CONTRACT-ALWAYS-VALID",
        "contracts.py",
        "valid=not errors,",
        "valid=True,",
        "test_kills_contract_validity_mutant",
    ),
    Mutant(
        "M-SIMULATION-REJECT-ZERO-SEED",
        "simulation.py",
        "if seed < 0:",
        "if seed <= 0:",
        "test_kills_zero_seed_rejection_mutant",
    ),
    Mutant(
        "M-AUTONOMOUS-ALLOW-ZERO-BUDGET",
        "autonomous.py",
        "if max_steps < 1:",
        "if max_steps < 0:",
        "test_kills_zero_budget_acceptance_mutant",
    ),
    Mutant(
        "M-CAMPAIGN-BYPASS-HARD-BUDGET",
        "campaign.py",
        "if manifest.hard_budget is None:",
        "if False and manifest.hard_budget is None:",
        "test_kills_campaign_hard_budget_bypass_mutant",
    ),
    Mutant(
        "M-CAMPAIGN-BYPASS-BUDGET-GATE",
        "campaign.py",
        'if manifest.budget_gate.startswith("blocked-"):',
        'if False and manifest.budget_gate.startswith("blocked-"):',
        "test_kills_campaign_budget_gate_bypass_mutant",
    ),
    Mutant(
        "M-COERCION-FALSE-AS-TRUE",
        "coercion.py",
        "if normalised in _FALSE_VALUES:\n            return False",
        "if normalised in _FALSE_VALUES:\n            return True",
        "test_kills_false_string_truthiness_mutant",
    ),
    Mutant(
        "M-FIREWALL-ALWAYS-ELIGIBLE",
        "judge_firewall.py",
        'eligible=decision == "eligible",',
        "eligible=True,",
        "test_kills_judge_firewall_eligibility_mutant",
    ),
)


def _apply_mutant(source: Path, mutant: Mutant) -> None:
    text = source.read_text(encoding="utf-8")
    occurrences = text.count(mutant.before)
    if occurrences != 1:
        raise RuntimeError(
            f"{mutant.mutant_id}: expected one mutation site in {source}, found {occurrences}"
        )
    source.write_text(text.replace(mutant.before, mutant.after, 1), encoding="utf-8")


def _status(completed: subprocess.CompletedProcess[str], test_name: str) -> str:
    output = completed.stdout + "\n" + completed.stderr
    if completed.returncode == 0:
        return "survived"
    if completed.returncode == 1 and test_name in output and "FAILED" in output:
        return "killed"
    return "infrastructure-error"


def run_campaign(root: Path) -> tuple[MutantResult, ...]:
    package_source = root / "src/pelicanbench"
    test_path = root / "tests/mutation/test_mutation_sentinels.py"
    results: list[MutantResult] = []
    for mutant in MUTANTS:
        with tempfile.TemporaryDirectory(prefix="pelicanbench-mutant-") as temporary:
            temporary_root = Path(temporary)
            mutated_source = temporary_root / "src/pelicanbench"
            shutil.copytree(package_source, mutated_source)
            _apply_mutant(mutated_source / mutant.relative_path, mutant)
            temporary_tests = temporary_root / "tests/mutation"
            temporary_tests.mkdir(parents=True)
            temporary_test = temporary_tests / test_path.name
            shutil.copy2(test_path, temporary_test)
            shutil.copy2(root / "tests/conftest.py", temporary_root / "tests/conftest.py")
            shutil.copytree(root / "benchmark/contracts", temporary_root / "benchmark/contracts")
            shutil.copytree(root / "benchmark/tasks", temporary_root / "benchmark/tasks")
            shutil.copytree(root / "benchmark/fixtures", temporary_root / "benchmark/fixtures")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(temporary_root / "src")
            completed = subprocess.run(  # nosec B603
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    str(temporary_test),
                    "--rootdir",
                    str(temporary_root),
                    "-k",
                    mutant.test_name,
                    "-o",
                    "addopts=",
                    "--disable-warnings",
                ],
                cwd=temporary_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            output = (completed.stdout + "\n" + completed.stderr).strip()
            results.append(
                MutantResult(
                    mutant_id=mutant.mutant_id,
                    status=_status(completed, mutant.test_name),  # type: ignore[arg-type]
                    returncode=completed.returncode,
                    output_tail="\n".join(output.splitlines()[-12:]),
                )
            )
    return tuple(results)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/mutation-smoke.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    results = run_campaign(root)
    killed = sum(result.killed for result in results)
    infrastructure_errors = sum(result.status == "infrastructure-error" for result in results)
    payload = {
        "schema_version": "1.1.0",
        "mutants": [asdict(result) | {"killed": result.killed} for result in results],
        "mutants_total": len(results),
        "mutants_killed": killed,
        "mutants_survived": sum(result.status == "survived" for result in results),
        "infrastructure_errors": infrastructure_errors,
        "mutation_score": killed / len(results),
        "passed": killed == len(results) and infrastructure_errors == 0,
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
