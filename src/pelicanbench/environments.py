"""Agentic drawing environment and application-adapter boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .canvas import CanvasEnvironment


class DrawingEnvironment(Protocol):
    def reset(self) -> dict[str, Any]: ...
    def step(self, action: dict[str, Any]) -> dict[str, Any]: ...
    def state(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class PelicanCanvasOpenEnv:
    """Minimal reset/step/state envelope compatible with OpenEnv-style clients."""

    canvas: CanvasEnvironment

    def reset(self) -> dict[str, Any]:
        return {"observation": self.canvas.reset(), "done": False, "reward": 0.0}

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        try:
            state = self.canvas.step(action)
            reward = 0.01
            error = None
        except (KeyError, TypeError, ValueError) as exc:
            state = self.canvas.state()
            reward = -0.05
            error = f"{type(exc).__name__}: {exc}"
        return {"observation": state, "done": False, "reward": reward, "error": error}

    def state(self) -> dict[str, Any]:
        return self.canvas.state()


@dataclass(frozen=True, slots=True)
class ApplicationAdapterSpec:
    adapter_id: str
    application: str
    artifact_type: str
    status: str
    capabilities: tuple[str, ...]
    isolation: str
    notes: str = ""


REFERENCE_ADAPTERS = (
    ApplicationAdapterSpec(
        "pelican-canvas",
        "PelicanCanvas",
        "SVG",
        "reference",
        ("create", "edit", "group", "undo", "checkpoint", "export"),
        "in-process deterministic state machine",
    ),
    ApplicationAdapterSpec(
        "krita-cli-legacy",
        "Krita",
        "raster/vector document",
        "legacy-compatibility",
        ("create", "edit", "render", "version"),
        "external process or MCP boundary",
    ),
    ApplicationAdapterSpec(
        "penpot-future",
        "Penpot",
        "SVG/design document",
        "recommended-future",
        ("create", "edit", "components", "collaboration"),
        "containerised browser/API adapter",
    ),
    ApplicationAdapterSpec(
        "figma-optional",
        "Figma",
        "design document",
        "optional-commercial",
        ("create", "edit", "components", "export"),
        "remote API/tool adapter",
    ),
)
