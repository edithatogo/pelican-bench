"""Diagnosis, targeted SVG repair, and edit-locality metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .scoring import score_svg
from .svg import inspect_svg
from .models import BenchmarkTask


@dataclass(frozen=True, slots=True)
class RepairRequirement:
    defect_id: str
    description: str
    target_roles: tuple[str, ...]
    preserve_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RepairScore:
    before_score: float
    after_score: float
    improvement: float
    repaired_fraction: float
    preservation_fraction: float
    new_defects: tuple[str, ...]


def _roles(svg: str) -> set[str]:
    return set(inspect_svg(svg).features.get("role_counts", {}))


def score_repair(
    task: BenchmarkTask,
    before_svg: str,
    after_svg: str,
    requirements: Iterable[RepairRequirement],
) -> RepairScore:
    requirement_values = list(requirements)
    before_roles = _roles(before_svg)
    after_roles = _roles(after_svg)
    repaired = 0
    preserved = 0
    preserve_total = 0
    new_defects: list[str] = []
    for requirement in requirement_values:
        target = set(requirement.target_roles)
        if target and not target.issubset(before_roles) and target.issubset(after_roles):
            repaired += 1
        for role in requirement.preserve_roles:
            preserve_total += 1
            if role in before_roles and role in after_roles:
                preserved += 1
            elif role in before_roles and role not in after_roles:
                new_defects.append(f"lost:{role}")
    before = score_svg(task, before_svg, submission_id="repair-before").aggregate
    after = score_svg(task, after_svg, submission_id="repair-after").aggregate
    return RepairScore(
        before_score=before,
        after_score=after,
        improvement=after - before,
        repaired_fraction=repaired / max(1, len(requirement_values)),
        preservation_fraction=preserved / max(1, preserve_total),
        new_defects=tuple(sorted(set(new_defects))),
    )
