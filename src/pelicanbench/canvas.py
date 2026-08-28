"""Deterministic state/action model for the canonical PelicanCanvas environment."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from html import escape
from itertools import starmap
from typing import Any

from .io import content_hash

ALLOWED_ACTIONS = {"add", "update", "delete", "group", "ungroup", "checkpoint", "undo"}
ALLOWED_TAGS = {"g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}
ALLOWED_ATTRIBUTES = {
    "x",
    "y",
    "x1",
    "x2",
    "y1",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "d",
    "points",
    "fill",
    "stroke",
    "stroke-width",
    "transform",
    "class",
    "data-role",
    "aria-label",
}


@dataclass(slots=True)
class CanvasEnvironment:
    max_elements: int = 2_000
    width: int = 640
    height: int = 480
    elements: dict[str, dict[str, Any]] = field(default_factory=dict)
    history: list[dict[str, dict[str, Any]]] = field(default_factory=list)
    checkpoints: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def reset(self) -> dict[str, Any]:
        self.elements.clear()
        self.history.clear()
        self.checkpoints.clear()
        self.events.clear()
        return self.state()

    def state(self) -> dict[str, Any]:
        ordered = {key: self.elements[key] for key in sorted(self.elements)}
        return {
            "elements": deepcopy(ordered),
            "state_hash": content_hash(ordered),
            "steps": len(self.events),
            "checkpoints": tuple(sorted(self.checkpoints)),
        }

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        kind = action.get("type")
        if kind not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported action: {kind}")
        before = deepcopy(self.elements)
        if kind == "add":
            element_id = str(action["id"])
            if element_id in self.elements:
                raise ValueError(f"element already exists: {element_id}")
            if len(self.elements) >= self.max_elements:
                raise ValueError("element limit exceeded")
            self.elements[element_id] = self._sanitize_element(action["element"])
        elif kind == "update":
            element_id = str(action["id"])
            if element_id not in self.elements:
                raise KeyError(element_id)
            changes = self._sanitize_element(action["changes"], partial=True)
            if "attributes" in changes:
                existing = dict(self.elements[element_id].get("attributes", {}))
                existing.update(changes.pop("attributes"))
                self.elements[element_id]["attributes"] = existing
            self.elements[element_id].update(changes)
        elif kind == "delete":
            element_id = str(action["id"])
            if element_id not in self.elements:
                raise KeyError(element_id)
            del self.elements[element_id]
        elif kind in {"group", "ungroup"}:
            for element_id in action.get("ids", []):
                if element_id not in self.elements:
                    raise KeyError(element_id)
                self.elements[element_id]["group"] = (
                    action.get("group") if kind == "group" else None
                )
        elif kind == "checkpoint":
            checkpoint_id = str(action.get("id") or f"checkpoint-{len(self.checkpoints) + 1}")
            self.checkpoints[checkpoint_id] = deepcopy(self.elements)
        elif kind == "undo":
            if not self.history:
                raise ValueError("nothing to undo")
            self.elements = self.history.pop()
            self.events.append(
                {"action": deepcopy(action), "state_hash": self.state()["state_hash"]}
            )
            return self.state()
        if kind != "checkpoint":
            self.history.append(before)
        self.events.append({"action": deepcopy(action), "state_hash": self.state()["state_hash"]})
        return self.state()

    def restore(self, checkpoint_id: str) -> dict[str, Any]:
        if checkpoint_id not in self.checkpoints:
            raise KeyError(checkpoint_id)
        self.history.append(deepcopy(self.elements))
        self.elements = deepcopy(self.checkpoints[checkpoint_id])
        self.events.append(
            {
                "action": {"type": "restore", "id": checkpoint_id},
                "state_hash": self.state()["state_hash"],
            }
        )
        return self.state()

    def to_svg(self) -> str:
        """Export the editable state as deterministic, labelled SVG."""
        group_names = sorted(
            {
                str(item.get("group"))
                for item in self.elements.values()
                if item.get("group") is not None
            }
        )
        grouped: dict[str | None, list[tuple[str, dict[str, Any]]]] = {None: []}
        for name in group_names:
            grouped[name] = []
        for element_id in sorted(self.elements):
            item = self.elements[element_id]
            group = str(item["group"]) if item.get("group") is not None else None
            grouped.setdefault(group, []).append((element_id, item))

        def render(element_id: str, item: dict[str, Any]) -> str:
            attributes = {"id": element_id, **dict(item.get("attributes", {}))}
            serialised = " ".join(
                f'{escape(str(key), quote=True)}="{escape(str(value), quote=True)}"'
                for key, value in sorted(attributes.items())
            )
            text = escape(str(item.get("text", "")))
            return f"<{item['tag']} {serialised}>{text}</{item['tag']}>"

        body: list[str] = list(starmap(render, grouped.get(None, [])))
        for group in group_names:
            members = "".join(starmap(render, grouped[group]))
            body.append(f'<g id="{escape(group, quote=True)}">{members}</g>')
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">{"".join(body)}</svg>'
        )

    @staticmethod
    def _sanitize_element(value: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("element must be an object")
        allowed = {"tag", "attributes", "text", "group"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown element fields: {sorted(unknown)}")
        tag = str(value.get("tag", ""))
        if (not partial or "tag" in value) and tag not in ALLOWED_TAGS:
            raise ValueError(f"unsupported SVG tag: {tag}")
        output = deepcopy(value)
        if "attributes" in output:
            if not isinstance(output["attributes"], dict):
                raise TypeError("attributes must be an object")
            unsafe = set(output["attributes"]) - ALLOWED_ATTRIBUTES
            if unsafe:
                raise ValueError(f"unsupported SVG attributes: {sorted(unsafe)}")
            for attribute_value in output["attributes"].values():
                candidate = str(attribute_value).lower()
                if "javascript:" in candidate or "url(" in candidate or "data:" in candidate:
                    raise ValueError("active or external attribute value is forbidden")
        return output
