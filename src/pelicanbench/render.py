"""Canonical, source-independent SVG rendering and raster diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cairosvg
import numpy as np
from PIL import Image

from .io import content_hash
from .svg import SVGInspection, inspect_svg


class SVGRenderError(ValueError):
    """Raised when a safe SVG cannot be rendered canonically."""


@dataclass(frozen=True, slots=True)
class RenderedSVG:
    png: bytes
    render_hash: str
    width: int
    height: int
    foreground_fraction: float
    bounding_box_fraction: float
    connected_components: int
    edge_density: float
    nonblank: bool

    def diagnostics(self) -> dict[str, Any]:
        return {
            "render_hash": self.render_hash,
            "width": self.width,
            "height": self.height,
            "foreground_fraction": self.foreground_fraction,
            "bounding_box_fraction": self.bounding_box_fraction,
            "connected_components": self.connected_components,
            "edge_density": self.edge_density,
            "nonblank": self.nonblank,
        }


def render_svg(
    svg: str,
    *,
    size: int = 512,
    inspection: SVGInspection | None = None,
) -> RenderedSVG:
    """Render an already bounded SVG to a deterministic square RGBA canvas.

    The hash is computed from dimensions plus decoded RGBA pixels rather than PNG
    container bytes, avoiding encoder metadata differences.  The renderer never uses
    source labels, comments or element identifiers. The canonical judge canvas is
    opaque white so visual meaning is independent of viewer background.
    """

    checked = inspection or inspect_svg(svg)
    if not checked.valid:
        raise SVGRenderError("cannot render unsafe SVG: " + "; ".join(checked.errors))
    if size < 32 or size > 4096:
        raise ValueError("render size must be within [32,4096]")
    try:
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=size,
            output_height=size,
            unsafe=False,
            background_color="#ffffff",
        )
        image = Image.open(BytesIO(png)).convert("RGBA")
        image.load()
    except Exception as exc:  # Cairo/Pillow expose several backend-specific exceptions
        raise SVGRenderError(f"canonical render failure: {type(exc).__name__}: {exc}") from exc

    pixels = np.asarray(image, dtype=np.uint8)
    # The normative judge canvas is opaque white.  A fixed background avoids a
    # black bicycle disappearing in dark-mode viewers and removes undefined RGB
    # values beneath fully transparent pixels from the content hash.
    rgb = pixels[:, :, :3].astype(np.int16)
    distance_from_white = np.max(np.abs(rgb - 255), axis=2)
    mask = distance_from_white > 3
    visible_count = int(mask.sum())
    pixel_count = int(mask.size)
    foreground_fraction = visible_count / max(1, pixel_count)

    if visible_count:
        ys, xs = np.nonzero(mask)
        box_width = int(xs.max() - xs.min() + 1)
        box_height = int(ys.max() - ys.min() + 1)
        bounding_box_fraction = (box_width * box_height) / max(1, pixel_count)
    else:
        bounding_box_fraction = 0.0

    # Downsample the binary alpha mask before component analysis to bound work and
    # make anti-aliasing noise less influential.
    small = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    small.thumbnail((128, 128), Image.Resampling.NEAREST)
    small_mask = np.asarray(small, dtype=np.uint8) > 0
    components = _connected_components(small_mask, minimum_pixels=2)

    # Edge density is diagnostic only. It is measured on luminance rather than
    # alpha because the normative canvas is intentionally opaque.
    luminance = (299 * rgb[:, :, 0] + 587 * rgb[:, :, 1] + 114 * rgb[:, :, 2]) // 1000
    horizontal = np.abs(np.diff(luminance, axis=1)) > 8
    vertical = np.abs(np.diff(luminance, axis=0)) > 8
    edge_pixels = int(horizontal.sum() + vertical.sum())
    edge_denominator = max(1, horizontal.size + vertical.size)
    edge_density = edge_pixels / edge_denominator

    width, height = image.size
    render_hash = content_hash(
        width.to_bytes(4, "big") + height.to_bytes(4, "big") + pixels.tobytes()
    )
    nonblank = visible_count >= max(16, int(pixel_count * 0.0001))
    return RenderedSVG(
        png=png,
        render_hash=render_hash,
        width=width,
        height=height,
        foreground_fraction=foreground_fraction,
        bounding_box_fraction=bounding_box_fraction,
        connected_components=components,
        edge_density=edge_density,
        nonblank=nonblank,
    )


def _connected_components(mask: np.ndarray, *, minimum_pixels: int) -> int:
    """Count 8-connected components in a small boolean mask without SciPy."""

    if mask.ndim != 2:
        raise ValueError("component mask must be two-dimensional")
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    count = 0
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(y, x)]
            visited[y, x] = True
            size = 0
            while stack:
                current_y, current_x = stack.pop()
                size += 1
                for next_y in range(max(0, current_y - 1), min(height, current_y + 2)):
                    for next_x in range(max(0, current_x - 1), min(width, current_x + 2)):
                        if mask[next_y, next_x] and not visited[next_y, next_x]:
                            visited[next_y, next_x] = True
                            stack.append((next_y, next_x))
            if size >= minimum_pixels:
                count += 1
    return count
