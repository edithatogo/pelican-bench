"""Quantitative image and SVG feature extraction for longitudinal analysis."""

from __future__ import annotations

import io
from statistics import mean
from typing import Any

from .svg import inspect_svg


def analyse_svg(svg: str) -> dict[str, Any]:
    inspection = inspect_svg(svg)
    features = dict(inspection.features)
    role_groups = features.get("role_groups", {})
    features.update(
        {
            "valid": inspection.valid,
            "canonical_hash": inspection.canonical_hash,
            "error_count": len(inspection.errors),
            "warning_count": len(inspection.warnings),
            "anatomy_role_count": sum(
                bool(role_groups.get(item))
                for item in ("animal", "pelican_bill", "pelican_pouch", "wing", "foot")
            ),
            "mechanics_role_count": sum(
                bool(role_groups.get(item))
                for item in ("vehicle", "frame", "handlebar", "pedal", "saddle")
            ),
            "interaction_role_count": int(bool(role_groups.get("contact"))),
        }
    )
    return features


def analyse_raster(image_bytes: bytes) -> dict[str, Any]:
    """Return renderer-independent low-level raster descriptors using Pillow when installed."""
    try:
        from PIL import Image, ImageStat
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Pillow is required for raster analysis") from exc
    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        extrema = rgb.getextrema()
        return {
            "width": rgb.width,
            "height": rgb.height,
            "aspect_ratio": rgb.width / max(1, rgb.height),
            "channel_means": tuple(round(value / 255, 6) for value in stat.mean),
            "channel_standard_deviations": tuple(round(value / 255, 6) for value in stat.stddev),
            "dynamic_range": mean((high - low) / 255 for low, high in extrema),
        }
