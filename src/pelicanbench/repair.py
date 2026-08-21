"""Diagnosis, targeted SVG repair and edit-locality metrics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image as _PILImage

from .models import BenchmarkTask
from .render import SVGRenderError, render_svg
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


@dataclass(frozen=True, slots=True)
class RenderRepairScore:
    """Pixel-level, render-bound repair and preservation assessment.

    All fractions are measured on the canonical opaque-white RGBA canvas and are
    independent of source labels, identifiers or comments.  ``diff_pixel_fraction``
    and ``preserved_pixel_fraction`` sum to one.
    """

    method: str = "render-repair-v1"
    size: int = 128
    diff_pixel_fraction: float = 0.0
    preserved_pixel_fraction: float = 1.0
    foreground_retention_fraction: float = 1.0
    added_ink_fraction: float = 0.0
    edit_locality: float = 1.0
    introduced_components: int = 0
    renders_match: bool = True


def _decode_png(png: bytes) -> np.ndarray:
    image = _PILImage.open(BytesIO(png)).convert("RGBA")
    image.load()
    return np.asarray(image, dtype=np.uint8)


def _foreground_mask(rgba: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.int16)
    return np.max(np.abs(rgb - 255), axis=2) > 3


def _downsample_mask(mask: np.ndarray) -> np.ndarray:
    image = _PILImage.fromarray((mask * 255).astype(np.uint8), mode="L")
    image.thumbnail((64, 64), _PILImage.Resampling.NEAREST)
    return np.asarray(image, dtype=np.uint8) > 0


def _count_components(mask: np.ndarray, *, minimum_pixels: int = 4) -> int:
    small = _downsample_mask(mask)
    visited = np.zeros(small.shape, dtype=bool)
    height, width = small.shape
    components = 0
    for y in range(height):
        for x in range(width):
            if small[y, x] and not visited[y, x]:
                stack = [(y, x)]
                visited[y, x] = True
                area = 0
                while stack:
                    cy, cx = stack.pop()
                    area += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if (
                                0 <= ny < height
                                and 0 <= nx < width
                                and small[ny, nx]
                                and not visited[ny, nx]
                            ):
                                visited[ny, nx] = True
                                stack.append((ny, nx))
                if area >= minimum_pixels:
                    components += 1
    return components


def score_repair_render(
    before_svg: str,
    after_svg: str,
    *,
    size: int = 128,
) -> RenderRepairScore:
    """Score repair by pixel behaviour on the canonical opaque-white canvas.

    The assessment never inspects element identifiers or source labels; it compares
    the deterministic :func:`render_svg` outputs.  Unsafe or unrenderable inputs
    raise :class:`SVGRenderError` rather than silently scoring.
    """
    before = render_svg(before_svg, size=size)
    after = render_svg(after_svg, size=size)
    if (before.width, before.height) != (after.width, after.height):
        raise SVGRenderError("render roll exposed different canvas dimensions")

    before_mask = _foreground_mask(_decode_png(before.png))
    after_mask = _foreground_mask(_decode_png(after.png))
    if before_mask.shape != after_mask.shape:
        raise SVGRenderError("render roll exposed a mask shape mismatch")

    diff = before_mask ^ after_mask
    diff_pixels = int(diff.sum())
    total = max(1, int(diff.size))
    retained = before_mask & after_mask
    foreground_retention = int(retained.sum()) / max(1, int(before_mask.sum()))
    added_ink = int((after_mask & ~before_mask).sum()) / total
    diff_fraction = diff_pixels / total
    preserved_fraction = 1.0 - diff_fraction

    if diff_pixels:
        ys, xs = np.nonzero(diff)
        bbox_area = max(1, int((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)))
        edit_locality = min(1.0, diff_pixels / bbox_area)
    else:
        edit_locality = 1.0

    return RenderRepairScore(
        size=size,
        diff_pixel_fraction=diff_fraction,
        preserved_pixel_fraction=preserved_fraction,
        foreground_retention_fraction=foreground_retention,
        added_ink_fraction=added_ink,
        edit_locality=edit_locality,
        introduced_components=_count_components(after_mask & ~before_mask),
        renders_match=diff_pixels == 0,
    )
