#!/usr/bin/env python3
"""Network-independent prose checks mirroring the repository's Vale policy."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProseFinding:
    code: str
    severity: str
    path: str
    line: int
    match: str
    message: str


SUBSTITUTIONS = {
    "Github": "GitHub",
    "Git Hub": "GitHub",
    "HuggingFace": "Hugging Face",
    "Huggingface": "Hugging Face",
    "Openenv": "OpenEnv",
    "Pelican Bench": "PelicanBench",
}
UNSUPPORTED_CLAIMS = (
    "fully validated",
    "proved unbiased",
    "proven unbiased",
    "guaranteed reproducible",
    "completely secure",
    "production ready",
)
PLACEHOLDERS = ("TODO" + ": placeholder", "FIXME" + ":", "lorem ipsum")
EXCLUDED = {
    "conductor/status.md",
    "conductor/tracks.md",
}


def _markdown_files(root: Path, inputs: Iterable[str]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for value in inputs:
        candidate = root / value
        if candidate.is_file() and candidate.suffix == ".md":
            paths.append(candidate)
        elif candidate.is_dir():
            paths.extend(sorted(candidate.rglob("*.md")))
    return tuple(
        dict.fromkeys(path for path in paths if path.relative_to(root).as_posix() not in EXCLUDED)
    )


def audit_prose(root: Path, inputs: Iterable[str]) -> tuple[ProseFinding, ...]:
    findings: list[ProseFinding] = []
    for path in _markdown_files(root, inputs):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("docs/generated/"):
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for observed, preferred in SUBSTITUTIONS.items():
                if observed in line:
                    findings.append(
                        ProseFinding(
                            "PROSE001",
                            "warning",
                            relative,
                            line_number,
                            observed,
                            f"use {preferred!r} rather than {observed!r}",
                        )
                    )
            lowered = line.lower()
            for phrase in UNSUPPORTED_CLAIMS:
                if phrase in lowered:
                    findings.append(
                        ProseFinding(
                            "PROSE002",
                            "warning",
                            relative,
                            line_number,
                            phrase,
                            "state the evidence level and limitation instead of an unsupported maturity claim",
                        )
                    )
            for phrase in PLACEHOLDERS:
                if phrase.lower() in lowered:
                    findings.append(
                        ProseFinding(
                            "PROSE003",
                            "warning",
                            relative,
                            line_number,
                            phrase,
                            "remove placeholder language from reviewed prose",
                        )
                    )
            if re.search(r"\b(?:very|extremely|clearly) unique\b", lowered):
                findings.append(
                    ProseFinding(
                        "PROSE004",
                        "warning",
                        relative,
                        line_number,
                        line.strip(),
                        "avoid intensifying an absolute adjective",
                    )
                )
    return tuple(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/prose-audit.json")
    parser.add_argument("--fail-level", choices=("error", "warning", "none"), default="warning")
    parser.add_argument("paths", nargs="*", default=["README.md", "docs", "conductor"])
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = audit_prose(root, args.paths)
    payload = {
        "schema_version": "1.0.0",
        "files": len(_markdown_files(root, args.paths)),
        "findings": [asdict(item) for item in findings],
        "warnings": sum(item.severity == "warning" for item in findings),
        "errors": sum(item.severity == "error" for item in findings),
        "passed": not findings if args.fail_level == "warning" else True,
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for finding in findings:
        print(
            f"{finding.severity.upper()} {finding.code} {finding.path}:{finding.line} {finding.message}"
        )
    if args.fail_level == "none":
        return 0
    if args.fail_level == "error":
        return int(any(item.severity == "error" for item in findings))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
