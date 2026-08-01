#!/usr/bin/env python3
"""Validate repository contracts and evidence references."""
from __future__ import annotations

from pathlib import Path

from pelicanbench.validation import validate_repository, validation_exit_code

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = validate_repository(ROOT)
    for finding in findings:
        location = f" [{finding.path}]" if finding.path else ""
        print(f"{finding.severity.upper()} {finding.code}{location}: {finding.message}")
    if not findings:
        print("Repository contract valid.")
    return validation_exit_code(findings)


if __name__ == "__main__":
    raise SystemExit(main())
