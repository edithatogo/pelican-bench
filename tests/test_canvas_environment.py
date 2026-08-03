from __future__ import annotations

import pytest

from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.environments import REFERENCE_ADAPTERS, PelicanCanvasOpenEnv
from pelicanbench.svg import inspect_svg


def circle(role: str = "wheel"):
    return {"tag": "circle", "attributes": {"cx": 20, "cy": 20, "r": 10, "data-role": role}}


def test_canvas_crud_group_undo_and_export():
    canvas = CanvasEnvironment()
    initial = canvas.reset()
    canvas.step({"type": "add", "id": "wheel", "element": circle()})
    canvas.step({"type": "update", "id": "wheel", "changes": {"attributes": {"cx": 30}}})
    assert canvas.elements["wheel"]["attributes"]["cx"] == 30
    canvas.step({"type": "group", "ids": ["wheel"], "group": "bike"})
    svg = canvas.to_svg()
    assert inspect_svg(svg).valid
    assert 'id="bike"' in svg
    canvas.step({"type": "ungroup", "ids": ["wheel"]})
    canvas.step({"type": "undo"})
    assert canvas.elements["wheel"]["group"] == "bike"
    assert initial["steps"] == 0


def test_checkpoint_and_restore():
    canvas = CanvasEnvironment()
    canvas.step({"type": "add", "id": "a", "element": circle()})
    canvas.step({"type": "checkpoint", "id": "one"})
    canvas.step({"type": "delete", "id": "a"})
    assert not canvas.elements
    canvas.restore("one")
    assert "a" in canvas.elements
    with pytest.raises(KeyError):
        canvas.restore("missing")


def test_canvas_validation():
    canvas = CanvasEnvironment(max_elements=1)
    with pytest.raises(ValueError):
        canvas.step({"type": "nope"})
    with pytest.raises(ValueError):
        canvas.step({"type": "add", "id": "x", "element": {"tag": "script"}})
    canvas.step({"type": "add", "id": "x", "element": circle()})
    with pytest.raises(ValueError):
        canvas.step({"type": "add", "id": "y", "element": circle()})
    with pytest.raises(ValueError):
        canvas.step({"type": "update", "id": "x", "changes": {"attributes": {"href": "x"}}})
    with pytest.raises(ValueError):
        canvas.step(
            {"type": "update", "id": "x", "changes": {"attributes": {"fill": "url(http://x)"}}}
        )


def test_openenv_error_is_observation():
    env = PelicanCanvasOpenEnv(CanvasEnvironment())
    assert env.reset()["reward"] == 0
    success = env.step({"type": "add", "id": "x", "element": circle()})
    assert success["reward"] > 0
    failure = env.step({"type": "delete", "id": "missing"})
    assert failure["reward"] < 0
    assert failure["error"].startswith("KeyError")


def test_adapter_registry():
    assert {item.adapter_id for item in REFERENCE_ADAPTERS} >= {
        "pelican-canvas",
        "krita-cli-legacy",
        "penpot-future",
    }
