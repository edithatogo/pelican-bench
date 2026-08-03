from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

import pelicanbench.render_bridge as bridge


def _png(size=64):
    buffer = BytesIO()
    Image.new("RGBA", (size, size), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_compare_renderers_with_deterministic_bridge(valid_svg, monkeypatch):
    canonical = bridge.render_svg(valid_svg, size=64)
    monkeypatch.setattr(bridge, "render_with_inkscape", lambda *args, **kwargs: canonical.png)
    result = bridge.compare_renderers(valid_svg, size=64)
    assert result.mean_absolute_error == 0
    assert result.differing_pixel_fraction == 0
    assert not result.materially_different


def test_inkscape_bridge_guards(valid_svg, monkeypatch):
    monkeypatch.setattr(bridge.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="not installed"):
        bridge.render_with_inkscape(valid_svg)
    with pytest.raises(ValueError, match="unsafe SVG"):
        bridge.render_with_inkscape("<svg><script/></svg>")
    monkeypatch.setattr(bridge.shutil, "which", lambda name: "/fixture/inkscape")
    with pytest.raises(ValueError, match="render size"):
        bridge.render_with_inkscape(valid_svg, size=8)


def test_inkscape_success_and_failure(valid_svg, monkeypatch):
    monkeypatch.setattr(bridge.shutil, "which", lambda name: "/fixture/inkscape")

    def successful(command, **kwargs):
        output = next(
            value.split("=", 1)[1] for value in command if value.startswith("--export-filename=")
        )
        Image.open(BytesIO(_png())).save(output)
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(bridge.subprocess, "run", successful)
    assert bridge.render_with_inkscape(valid_svg, size=64).startswith(b"\x89PNG")

    monkeypatch.setattr(
        bridge.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stderr=b"fixture failure"),
    )
    with pytest.raises(RuntimeError, match="fixture failure"):
        bridge.render_with_inkscape(valid_svg, size=64)
