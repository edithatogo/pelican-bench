"""Diagnosis, targeted SVG repair and edit-locality metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import BenchmarkTask
from .svg import inspect_svg


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
    method: str = "declared-artifact-repair-v2"


def _declared_roles(svg: str) -> set[str]:
    return set(inspect_svg(svg).features.get("declared_role_counts", {}))


def _objective_score(roles: set[str], requirements: list[RepairRequirement]) -> float:
    if not requirements:
        return 1.0
    values: list[float] = []
    for requirement in requirements:
        target = set(requirement.target_roles)
        target_score = len(target & roles) / max(1, len(target))
        preserve = set(requirement.preserve_roles)
        preserve_score = len(preserve & roles) / max(1, len(preserve)) if preserve else 1.0
        values.append(0.7 * target_score + 0.3 * preserve_score)
    return sum(values) / len(values)


def score_repair(
    task: BenchmarkTask,
    before_svg: str,
    after_svg: str,
    requirements: Iterable[RepairRequirement],
) -> RepairScore:
    """Score known artifact edits without pretending source labels prove visual quality.

    ``task`` is retained for API symmetry and future source-independent semantic repair
    assessments.  The current objective measures explicit declared edit targets and
    preservation only; it is reported separately from the visual benchmark score.
    """

    del task
    requirement_values = list(requirements)
    before_roles = _declared_roles(before_svg)
    after_roles = _declared_roles(after_svg)
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
    before = _objective_score(before_roles, requirement_values)
    after = _objective_score(after_roles, requirement_values)
    return RepairScore(
        before_score=before,
        after_score=after,
        improvement=after - before,
        repaired_fraction=repaired / max(1, len(requirement_values)),
        preservation_fraction=preserved / max(1, preserve_total),
        new_defects=tuple(sorted(set(new_defects))),
    )
