"""Validation and content commitments for the prospective V1 candidate benchmark.

The candidate is a checked research object, not merely a JSONL file. This module validates
its factorial panels, exact empirical bridge, canary subset, stable identities, and
content-addressed commitment using only PelicanBench's runtime dependencies.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .empirical_nlp import PromptRecord, annotate_prompt_corpus, task_design_coverage
from .io import file_hash, read_json, read_jsonl
from .models import BenchmarkTask
from .taskgen import task_set_commitment


@dataclass(frozen=True, slots=True)
class CandidateFinding:
    severity: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateValidationReport:
    schema_version: str
    release: str
    task_count: int
    scenario_count: int
    prompt_count: int
    canary_count: int
    panel_counts: dict[str, int]
    task_commitment: str
    design_sha256: str
    empirical_exact_prompt_coverage: float
    findings: tuple[CandidateFinding, ...]

    @property
    def passed(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["passed"] = self.passed
        return value


def _task_panel(task: BenchmarkTask) -> str:
    value = task.metadata.get("panel_id")
    return str(value) if value is not None else "unassigned"


def _matches_selector(task: BenchmarkTask, selector: Mapping[str, Any]) -> bool:
    if selector.get("task_id") is not None:
        return bool(task.task_id == selector["task_id"])
    expected: dict[str, Any] = {
        "panel_id": _task_panel(task),
        "animal": task.animal.id,
        "mobile_object": task.mobile_object.id,
        "prompt_variant": task.metadata.get("prompt_variant"),
    }
    return all(expected.get(key) == value for key, value in selector.items())


def resolve_canary_tasks(
    tasks: Iterable[BenchmarkTask], selectors: Iterable[Mapping[str, Any]]
) -> tuple[BenchmarkTask, ...]:
    values = tuple(tasks)
    resolved: list[BenchmarkTask] = []
    for selector in selectors:
        matches = [task for task in values if _matches_selector(task, selector)]
        if len(matches) != 1:
            raise ValueError(
                "each canary selector must resolve exactly one task; "
                f"selector={dict(selector)!r}, matches={len(matches)}"
            )
        resolved.append(matches[0])
    identifiers = [task.task_id for task in resolved]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("canary selectors must resolve unique tasks")
    return tuple(resolved)


def _validate_factorial_panel(
    tasks: list[BenchmarkTask],
    *,
    animals: set[str],
    objects: set[str],
    prompt_variants: int,
    panel_id: str,
) -> list[CandidateFinding]:
    findings: list[CandidateFinding] = []
    expected = {(animal, obj) for animal in animals for obj in objects}
    grouped: dict[tuple[str, str], list[BenchmarkTask]] = defaultdict(list)
    for task in tasks:
        grouped[(task.animal.id, task.mobile_object.id)].append(task)
    missing = sorted(expected - set(grouped))
    unexpected = sorted(set(grouped) - expected)
    wrong_replicates = sorted(
        (animal, obj, len(rows))
        for (animal, obj), rows in grouped.items()
        if len(rows) != prompt_variants
    )
    if missing:
        findings.append(
            CandidateFinding("error", "factorial-cells-missing", f"{panel_id}: {missing}")
        )
    if unexpected:
        findings.append(
            CandidateFinding("error", "factorial-cells-unexpected", f"{panel_id}: {unexpected}")
        )
    if wrong_replicates:
        findings.append(
            CandidateFinding(
                "error",
                "factorial-prompt-variant-count",
                f"{panel_id}: expected {prompt_variants} per cell; observed {wrong_replicates}",
            )
        )
    return findings


def validate_candidate(
    root: str | Path,
    *,
    task_path: str = "benchmark/tasks/v1-candidate.jsonl",
    design_path: str = "benchmark/tasks/v1-candidate-design.json",
    commitment_path: str = "benchmark/tasks/v1-candidate-commitment.json",
    canary_path: str = "benchmark/tasks/v1-candidate-canary.jsonl",
    empirical_source_path: str = "data/derived/castillo-2026-prompt-corpus.jsonl",
) -> CandidateValidationReport:
    project = Path(root)
    tasks = [BenchmarkTask.model_validate(item) for item in read_jsonl(project / task_path)]
    design = read_json(project / design_path)
    commitment = read_json(project / commitment_path)
    canary_rows = [BenchmarkTask.model_validate(item) for item in read_jsonl(project / canary_path)]
    findings: list[CandidateFinding] = []

    if not tasks:
        findings.append(CandidateFinding("error", "empty-candidate", "candidate task set is empty"))
    for attribute in ("task_id", "prompt_id"):
        values = [getattr(task, attribute) for task in tasks]
        if len(values) != len(set(values)):
            findings.append(
                CandidateFinding(
                    "error", f"duplicate-{attribute}", f"{attribute} values must be unique"
                )
            )

    release = str(design.get("release", ""))
    wrong_release = sorted(
        {task.benchmark_release for task in tasks if task.benchmark_release != release}
    )
    if wrong_release:
        findings.append(
            CandidateFinding(
                "error", "mixed-release", f"tasks use unexpected releases: {wrong_release}"
            )
        )

    panel_counts = dict(sorted(Counter(_task_panel(task) for task in tasks).items()))
    if commitment.get("panel_counts") != panel_counts:
        findings.append(
            CandidateFinding("error", "panel-count-mismatch", "commitment panel counts differ")
        )

    expected_counts = {
        "task_count": len(tasks),
        "prompt_count": len({task.prompt_id for task in tasks}),
        "scenario_count": len({task.scenario_id for task in tasks}),
    }
    for name, expected in expected_counts.items():
        if commitment.get(name) != expected:
            findings.append(
                CandidateFinding(
                    "error", f"{name}-mismatch", f"expected {expected}, got {commitment.get(name)}"
                )
            )

    candidate_commitment = task_set_commitment(tasks)
    if commitment.get("commitment") != candidate_commitment:
        findings.append(
            CandidateFinding(
                "error", "task-commitment-mismatch", "task identity commitment differs"
            )
        )
    design_digest = file_hash(project / design_path)
    if commitment.get("design_sha256") != design_digest:
        findings.append(
            CandidateFinding("error", "design-hash-mismatch", "design file hash differs")
        )

    panels: dict[str, list[BenchmarkTask]] = defaultdict(list)
    for task in tasks:
        panels[_task_panel(task)].append(task)
    heritage = panels.get("heritage-anchor", [])
    if len(heritage) != 1 or heritage[0].prompt != "Generate an SVG of a pelican riding a bicycle":
        findings.append(
            CandidateFinding("error", "heritage-anchor-invalid", "heritage anchor changed")
        )

    bridge_animals = {
        "pelican",
        "flamingo",
        "heron",
        "otter",
        "raccoon",
        "antelope",
        "whale",
        "cat",
    }
    bridge_objects = {"bicycle", "unicycle", "skateboard", "scooter", "plane", "boat"}
    findings.extend(
        _validate_factorial_panel(
            panels.get("castillo-2026-factorial-bridge", []),
            animals=bridge_animals,
            objects=bridge_objects,
            prompt_variants=1,
            panel_id="castillo-2026-factorial-bridge",
        )
    )

    confirmatory = design.get("confirmatory_panel", {})
    confirmatory_id = str(confirmatory.get("id", "pelicanbench-interface-confirmatory-v1"))
    findings.extend(
        _validate_factorial_panel(
            panels.get(confirmatory_id, []),
            animals={str(item) for item in confirmatory.get("animals", [])},
            objects={str(item["id"]) for item in confirmatory.get("mobile_objects", [])},
            prompt_variants=len(confirmatory.get("prompt_templates", [])),
            panel_id=confirmatory_id,
        )
    )

    try:
        resolved = resolve_canary_tasks(tasks, design.get("canary_selectors", []))
    except ValueError as exc:
        findings.append(CandidateFinding("error", "canary-selector-invalid", str(exc)))
        resolved = ()
    if [task.model_dump(mode="json") for task in resolved] != [
        task.model_dump(mode="json") for task in canary_rows
    ]:
        findings.append(CandidateFinding("error", "canary-file-mismatch", "canary JSONL is stale"))

    source_records = [
        PromptRecord.from_mapping(item) for item in read_jsonl(project / empirical_source_path)
    ]
    annotations = annotate_prompt_corpus(source_records)
    empirical = task_design_coverage(
        annotations,
        tasks,
        panel_id="castillo-2026-factorial-bridge",
        evidence_status="source-derived-exact-prompt-bridge-E2",
    )
    if empirical["exact_prompt_coverage"] != 1.0:
        findings.append(
            CandidateFinding(
                "error", "empirical-bridge-incomplete", "source prompts are not fully represented"
            )
        )

    return CandidateValidationReport(
        schema_version="1.0.0",
        release=release,
        task_count=len(tasks),
        scenario_count=len({task.scenario_id for task in tasks}),
        prompt_count=len({task.prompt_id for task in tasks}),
        canary_count=len(canary_rows),
        panel_counts=panel_counts,
        task_commitment=candidate_commitment,
        design_sha256=design_digest,
        empirical_exact_prompt_coverage=float(empirical["exact_prompt_coverage"]),
        findings=tuple(findings),
    )


def candidate_commitment_payload(root: str | Path) -> dict[str, Any]:
    project = Path(root)
    tasks = [
        BenchmarkTask.model_validate(item)
        for item in read_jsonl(project / "benchmark/tasks/v1-candidate.jsonl")
    ]
    design = read_json(project / "benchmark/tasks/v1-candidate-design.json")
    panel_counts = dict(sorted(Counter(_task_panel(task) for task in tasks).items()))
    return {
        "schema_version": "2.0.0",
        "release": design["release"],
        "task_count": len(tasks),
        "scenario_count": len({task.scenario_id for task in tasks}),
        "prompt_count": len({task.prompt_id for task in tasks}),
        "panel_counts": panel_counts,
        "commitment": task_set_commitment(tasks),
        "design_sha256": file_hash(project / "benchmark/tasks/v1-candidate-design.json"),
    }


__all__ = [
    "CandidateFinding",
    "CandidateValidationReport",
    "candidate_commitment_payload",
    "resolve_canary_tasks",
    "validate_candidate",
]
