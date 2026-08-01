"""Quantitative SVG and raster feature extraction for longitudinal analysis."""

from __future__ import annotations

import io
from statistics import mean
from typing import Any

from .render import SVGRenderError, render_svg
from .svg import inspect_svg


def analyse_svg(svg: str) -> dict[str, Any]:
    """Return source and canonical-render diagnostics without semantic inference."""

    inspection = inspect_svg(svg)
    features = dict(inspection.features)
    declared = set(features.get("declared_role_counts", {}))
    render_features: dict[str, Any] = {}
    if inspection.valid:
        try:
            render_features = render_svg(svg, inspection=inspection).diagnostics()
        except SVGRenderError as exc:
            render_features = {"render_error": str(exc), "nonblank": False}
    features.update(
        {
            "valid": inspection.valid,
            "canonical_hash": inspection.canonical_hash,
            "error_count": len(inspection.errors),
            "warning_count": len(inspection.warnings),
            # These are declared source labels, useful for longitudinal artifact
            # editability analysis but never evidence of visual correctness.
            "declared_anatomy_label_count": len(
                declared & {"animal", "bird", "pelican", "bill", "beak", "pouch", "wing", "foot"}
            ),
            "declared_mechanics_label_count": len(
                declared
                & {
                    "vehicle",
                    "bicycle",
                    "bike",
                    "frame",
                    "handlebar",
                    "pedal",
                    "saddle",
                    "wheel",
                }
            ),
            "declared_interaction_label_count": len(
                declared & {"contact", "rider", "riding", "grip", "driver", "passenger"}
            ),
            "render": render_features,
        }
    )
    return features


def analyse_raster(image_bytes: bytes) -> dict[str, Any]:
    """Return renderer-independent low-level raster descriptors using Pillow."""

    try:
        from PIL import Image, ImageStat
    except ImportError as exc:  # pragma: no cover - required by the image extra
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
