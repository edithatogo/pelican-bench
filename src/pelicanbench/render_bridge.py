"""Cross-renderer bridge diagnostics for canonical SVG interpretation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from .io import content_hash
from .render import render_svg
from .svg import inspect_svg


@dataclass(frozen=True, slots=True)
class RendererBridgeResult:
    canonical_renderer: str
    bridge_renderer: str
    canonical_hash: str
    bridge_hash: str
    mean_absolute_error: float
    differing_pixel_fraction: float
    maximum_channel_error: float
    width: int
    height: int

    @property
    def materially_different(self) -> bool:
        return self.differing_pixel_fraction > 0.02 or self.mean_absolute_error > 0.02


def _rgba_pixels(png: bytes, *, size: int) -> np.ndarray:
    with Image.open(BytesIO(png)) as image:
        rgba = image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        rgba.load()
    return np.asarray(rgba, dtype=np.uint8)


def render_with_inkscape(svg: str, *, size: int = 512, timeout: float = 30.0) -> bytes:
    """Render safe SVG source with the installed Inkscape CLI."""

    inspection = inspect_svg(svg)
    if not inspection.valid:
        raise ValueError("cannot bridge-render unsafe SVG: " + "; ".join(inspection.errors))
    executable = shutil.which("inkscape")
    if executable is None:
        raise RuntimeError("Inkscape is not installed")
    if size < 32 or size > 4096:
        raise ValueError("render size must be within [32,4096]")
    with tempfile.TemporaryDirectory(prefix="pelicanbench-render-") as directory:
        root = Path(directory)
        source = root / "input.svg"
        output = root / "output.png"
        source.write_text(svg, encoding="utf-8")
        completed = subprocess.run(
            [
                executable,
                str(source),
                "--export-type=png",
                f"--export-filename={output}",
                f"--export-width={size}",
                "--export-background=#ffffff",
                "--export-background-opacity=255",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        if completed.returncode != 0 or not output.exists():
            stderr = completed.stderr.decode("utf-8", errors="replace")[-2_000:]
            raise RuntimeError(f"Inkscape render failed ({completed.returncode}): {stderr}")
        with Image.open(output) as rendered:
            rgba = rendered.convert("RGBA")
            rgba.load()
        if rgba.width > size or rgba.height > size:
            rgba.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        offset = ((size - rgba.width) // 2, (size - rgba.height) // 2)
        canvas.alpha_composite(rgba, dest=offset)
        buffer = BytesIO()
        canvas.save(buffer, format="PNG", optimize=False)
        return buffer.getvalue()


def compare_renderers(svg: str, *, size: int = 512, timeout: float = 30.0) -> RendererBridgeResult:
    """Compare the normative CairoSVG render with an Inkscape bridge render."""

    canonical = render_svg(svg, size=size)
    bridge_png = render_with_inkscape(svg, size=size, timeout=timeout)
    left = _rgba_pixels(canonical.png, size=size).astype(np.int16)
    right = _rgba_pixels(bridge_png, size=size).astype(np.int16)
    absolute = np.abs(left - right)
    normalised = absolute / 255.0
    differing = np.any(absolute > 8, axis=2)
    bridge_hash = content_hash(
        size.to_bytes(4, "big") + size.to_bytes(4, "big") + right.astype(np.uint8).tobytes()
    )
    return RendererBridgeResult(
        canonical_renderer="CairoSVG 2.x",
        bridge_renderer="Inkscape CLI",
        canonical_hash=canonical.render_hash,
        bridge_hash=bridge_hash,
        mean_absolute_error=float(normalised.mean()),
        differing_pixel_fraction=float(differing.mean()),
        maximum_channel_error=float(normalised.max()),
        width=size,
        height=size,
    )
