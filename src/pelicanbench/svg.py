"""Bounded SVG security inspection, canonicalisation and visible geometry features.

Source-controlled labels are retained only as diagnostics for editability.  They are never
used as evidence that an animal, object, component or relationship is visually present.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from defusedxml import ElementTree as DefusedET

from .io import content_hash

ALLOWED_TAGS = {
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "line",
    "polyline",
    "polygon",
    "text",
    "title",
    "desc",
    "defs",
    "clipPath",
    "linearGradient",
    "radialGradient",
    "stop",
}
DRAWABLE_TAGS = {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "text"}
NON_RENDERED_CONTAINERS = {"defs", "clipPath", "linearGradient", "radialGradient"}
FORBIDDEN_TAGS = {"script", "foreignObject", "image", "iframe", "audio", "video", "use"}
EVENT_ATTRIBUTE = re.compile(r"^on[a-z]+", re.IGNORECASE)
UNSAFE_CSS = re.compile(r"url\s*\(|expression\s*\(|@import", re.IGNORECASE)
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
ROLE_SPLIT = re.compile(r"[^a-z0-9]+")
TRANSFORM = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")
POINT = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")

# SVG affine matrix represented as (a,b,c,d,e,f):
# x' = ax + cy + e; y' = bx + dy + f
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class SVGInspection:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    features: dict[str, Any]
    canonical_hash: str | None


class SVGSecurityError(ValueError):
    """Raised when an SVG does not pass the source-security gate."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = NUMBER.search(value)
    if not match:
        return default
    try:
        number = float(match.group())
    except ValueError:
        return default
    return number if math.isfinite(number) else default


def _role_tokens(element: Any) -> set[str]:
    tokens: set[str] = set()
    for attribute in ("id", "class", "data-role", "aria-label"):
        raw = str(element.attrib.get(attribute, "")).lower()
        tokens.update(token for token in ROLE_SPLIT.split(raw) if token)
    return tokens


def _is_external_reference(value: str) -> bool:
    stripped = value.strip().lower()
    if stripped.startswith("#"):
        return False
    return any(
        stripped.startswith(prefix)
        for prefix in ("http:", "https:", "file:", "ftp:", "data:", "javascript:", "//")
    )


def _preflight(svg: str, *, max_bytes: int) -> list[str]:
    errors: list[str] = []
    encoded = svg.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        errors.append(f"svg exceeds byte limit ({len(encoded)} > {max_bytes})")
    lowered = svg.lower()
    for marker, label in (
        ("<!doctype", "doctype is forbidden"),
        ("<!entity", "entity declarations are forbidden"),
        ("<?xml-stylesheet", "xml stylesheets are forbidden"),
    ):
        if marker in lowered:
            errors.append(label)
    if "\x00" in svg:
        errors.append("NUL bytes are forbidden")
    return errors


def _style(element: Any) -> dict[str, str]:
    output: dict[str, str] = {}
    for item in str(element.attrib.get("style", "")).split(";"):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        output[key.strip().lower()] = value.strip()
    return output


def _property(element: Any, style: dict[str, str], name: str, default: str) -> str:
    if name in style:
        return style[name]
    return str(element.attrib.get(name, default))


def _multiply(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    la, lb, lc, ld, le, lf = left
    ra, rb, rc, rd, re_, rf = right
    return (
        la * ra + lc * rb,
        lb * ra + ld * rb,
        la * rc + lc * rd,
        lb * rc + ld * rd,
        la * re_ + lc * rf + le,
        lb * re_ + ld * rf + lf,
    )


def _transform_matrix(raw: str | None) -> tuple[float, ...]:
    current: tuple[float, ...] = IDENTITY
    for name, args in TRANSFORM.findall(raw or ""):
        values = [_float(value) for value in POINT.findall(args)]
        operation: tuple[float, ...] = IDENTITY
        lowered = name.lower()
        if lowered == "matrix" and len(values) == 6:
            operation = tuple(values)
        elif lowered == "translate" and values:
            operation = (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) > 1 else 0.0)
        elif lowered == "scale" and values:
            sy = values[1] if len(values) > 1 else values[0]
            operation = (values[0], 0.0, 0.0, sy, 0.0, 0.0)
        elif lowered == "rotate" and values:
            angle = math.radians(values[0])
            cosine, sine = math.cos(angle), math.sin(angle)
            rotation = (cosine, sine, -sine, cosine, 0.0, 0.0)
            if len(values) >= 3:
                cx, cy = values[1], values[2]
                operation = _multiply(
                    _multiply((1.0, 0.0, 0.0, 1.0, cx, cy), rotation),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
            else:
                operation = rotation
        current = _multiply(current, operation)
    return current


def _point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _bounds_for(
    element: Any, tag: str, matrix: tuple[float, ...]
) -> tuple[float, float, float, float] | None:
    points: list[tuple[float, float]] = []
    if tag == "circle":
        cx, cy = _float(element.attrib.get("cx")), _float(element.attrib.get("cy"))
        radius = abs(_float(element.attrib.get("r")))
        points = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    elif tag == "ellipse":
        cx, cy = _float(element.attrib.get("cx")), _float(element.attrib.get("cy"))
        rx, ry = abs(_float(element.attrib.get("rx"))), abs(_float(element.attrib.get("ry")))
        points = [(cx - rx, cy - ry), (cx + rx, cy + ry)]
    elif tag == "rect":
        x, y = _float(element.attrib.get("x")), _float(element.attrib.get("y"))
        width, height = (
            abs(_float(element.attrib.get("width"))),
            abs(_float(element.attrib.get("height"))),
        )
        points = [(x, y), (x + width, y), (x, y + height), (x + width, y + height)]
    elif tag == "line":
        points = [
            (_float(element.attrib.get("x1")), _float(element.attrib.get("y1"))),
            (_float(element.attrib.get("x2")), _float(element.attrib.get("y2"))),
        ]
    elif tag in {"polyline", "polygon"}:
        values = [_float(item) for item in POINT.findall(str(element.attrib.get("points", "")))]
        points = list(zip(values[::2], values[1::2], strict=False))
    if not points:
        return None
    transformed = [_point(matrix, x, y) for x, y in points]
    xs = [item[0] for item in transformed]
    ys = [item[1] for item in transformed]
    return min(xs), min(ys), max(xs), max(ys)


def _view_box(root: Any) -> tuple[float, float, float, float] | None:
    values = [_float(item) for item in POINT.findall(str(root.attrib.get("viewBox", "")))]
    if len(values) == 4 and values[2] > 0 and values[3] > 0:
        return values[0], values[1], values[0] + values[2], values[1] + values[3]
    width = _float(root.attrib.get("width"))
    height = _float(root.attrib.get("height"))
    if width > 0 and height > 0:
        return 0.0, 0.0, width, height
    return None


def _intersects(
    bounds: tuple[float, float, float, float] | None, viewport: tuple[float, ...] | None
) -> bool:
    if bounds is None or viewport is None:
        return True
    left, top, right, bottom = bounds
    view_left, view_top, view_right, view_bottom = viewport
    return right >= view_left and left <= view_right and bottom >= view_top and top <= view_bottom


def _has_visible_paint(element: Any, tag: str, style: dict[str, str], opacity: float) -> bool:
    if tag not in DRAWABLE_TAGS or opacity <= 0:
        return False
    fill_default = "black" if tag not in {"line", "polyline"} else "none"
    fill = _property(element, style, "fill", fill_default).strip().lower()
    stroke = _property(element, style, "stroke", "none").strip().lower()
    fill_opacity = opacity * _float(_property(element, style, "fill-opacity", "1"), 1.0)
    stroke_opacity = opacity * _float(_property(element, style, "stroke-opacity", "1"), 1.0)
    stroke_width = _float(_property(element, style, "stroke-width", "1"), 1.0)
    fill_visible = fill not in {"none", "transparent"} and fill_opacity > 0
    stroke_visible = (
        stroke not in {"none", "transparent"} and stroke_opacity > 0 and stroke_width > 0
    )
    return fill_visible or stroke_visible


def inspect_svg(
    svg: str,
    *,
    max_bytes: int = 2_000_000,
    max_elements: int = 10_000,
    max_path_characters: int = 500_000,
) -> SVGInspection:
    """Inspect SVG source without executing active or external content."""

    errors = _preflight(svg, max_bytes=max_bytes)
    warnings: list[str] = []
    if errors:
        return SVGInspection(False, tuple(errors), (), {}, None)
    try:
        root = DefusedET.fromstring(svg)
    except Exception as exc:  # parser-specific security exceptions share no stable base class
        return SVGInspection(
            False, (f"XML parse failure: {type(exc).__name__}: {exc}",), (), {}, None
        )
    if _local_name(root.tag) != "svg":
        errors.append("root element must be svg")

    elements = list(root.iter())
    if len(elements) > max_elements:
        errors.append(f"element limit exceeded ({len(elements)} > {max_elements})")

    tag_counts: Counter[str] = Counter()
    declared_role_counts: Counter[str] = Counter()
    path_characters = 0
    external_references = 0
    event_attributes = 0
    visible_circles: list[dict[str, float]] = []
    text_content: list[str] = []
    attribute_count = 0
    declared_labelled_elements = 0
    visible_labelled_elements = 0
    visible_shape_count = 0
    hidden_shape_count = 0
    off_canvas_shape_count = 0
    group_count = 0
    transform_count = 0
    viewport = _view_box(root)

    def walk(
        element: Any,
        *,
        context_visible: bool,
        in_non_rendered_container: bool,
        inherited_opacity: float,
        inherited_transform: tuple[float, ...],
    ) -> None:
        nonlocal \
            path_characters, \
            external_references, \
            event_attributes, \
            attribute_count, \
            declared_labelled_elements, \
            visible_labelled_elements, \
            visible_shape_count, \
            hidden_shape_count, \
            off_canvas_shape_count, \
            group_count, \
            transform_count

        tag = _local_name(element.tag)
        tag_counts[tag] += 1
        if tag == "g":
            group_count += 1
        if tag in FORBIDDEN_TAGS:
            errors.append(f"forbidden element: {tag}")
        elif tag not in ALLOWED_TAGS:
            errors.append(f"unsupported element: {tag}")

        roles = _role_tokens(element)
        if roles:
            declared_labelled_elements += 1
            declared_role_counts.update(roles)
        attribute_count += len(element.attrib)
        style = _style(element)
        for name, value in element.attrib.items():
            local_attribute = _local_name(name)
            candidate = str(value)
            if EVENT_ATTRIBUTE.match(local_attribute):
                event_attributes += 1
                errors.append(f"event attribute is forbidden: {local_attribute}")
            if local_attribute in {"href", "src"} and _is_external_reference(candidate):
                external_references += 1
                errors.append(f"external reference is forbidden: {candidate}")
            if local_attribute == "style" and UNSAFE_CSS.search(candidate):
                errors.append("unsafe CSS reference or expression")
            if local_attribute in {"fill", "stroke", "filter", "clip-path", "mask"} and (
                _is_external_reference(candidate)
                or (
                    "url(" in candidate.lower()
                    and not re.fullmatch(r"url\(\s*#[^)]+\s*\)", candidate, re.IGNORECASE)
                )
            ):
                errors.append(f"unsafe paint/filter reference: {candidate}")

        display = _property(element, style, "display", "inline").strip().lower()
        visibility = _property(element, style, "visibility", "visible").strip().lower()
        opacity = inherited_opacity * max(
            0.0,
            min(1.0, _float(_property(element, style, "opacity", "1"), 1.0)),
        )
        visible_context = (
            context_visible
            and display != "none"
            and visibility not in {"hidden", "collapse"}
            and opacity > 0
        )
        non_rendered = in_non_rendered_container or tag in NON_RENDERED_CONTAINERS
        local_transform_raw = str(element.attrib.get("transform", ""))
        if local_transform_raw:
            transform_count += 1
        matrix = _multiply(inherited_transform, _transform_matrix(local_transform_raw))

        if tag == "path":
            path_characters += len(str(element.attrib.get("d", "")))

        if tag in DRAWABLE_TAGS:
            bounds = _bounds_for(element, tag, matrix)
            on_canvas = _intersects(bounds, viewport)
            visible_shape = (
                visible_context
                and not non_rendered
                and on_canvas
                and _has_visible_paint(element, tag, style, opacity)
            )
            if visible_shape:
                visible_shape_count += 1
                if roles:
                    visible_labelled_elements += 1
                if tag in {"circle", "ellipse"}:
                    cx, cy = _point(
                        matrix,
                        _float(element.attrib.get("cx")),
                        _float(element.attrib.get("cy")),
                    )
                    raw_rx = abs(_float(element.attrib.get("r") or element.attrib.get("rx")))
                    raw_ry = abs(_float(element.attrib.get("r") or element.attrib.get("ry")))
                    a, b, c, d, _, _ = matrix
                    scale_x = math.sqrt(a * a + b * b)
                    scale_y = math.sqrt(c * c + d * d)
                    visible_circles.append(
                        {
                            "cx": cx,
                            "cy": cy,
                            "rx": raw_rx * max(scale_x, 1e-12),
                            "ry": raw_ry * max(scale_y, 1e-12),
                        }
                    )
                if tag == "text" and element.text:
                    text_content.append(element.text.strip())
            else:
                hidden_shape_count += 1
                if visible_context and not non_rendered and not on_canvas:
                    off_canvas_shape_count += 1

        child_non_rendered = non_rendered
        for child in list(element):
            walk(
                child,
                context_visible=visible_context,
                in_non_rendered_container=child_non_rendered,
                inherited_opacity=opacity,
                inherited_transform=matrix,
            )

    walk(
        root,
        context_visible=True,
        in_non_rendered_container=False,
        inherited_opacity=1.0,
        inherited_transform=IDENTITY,
    )

    if path_characters > max_path_characters:
        errors.append(f"path data limit exceeded ({path_characters} > {max_path_characters})")
    if text_content:
        warnings.append("visible text is present; text shortcuts are not semantic evidence")

    wheel_candidates = [
        item
        for item in visible_circles
        if item["rx"] >= 8
        and item["ry"] >= 8
        and abs(item["rx"] - item["ry"]) <= max(item["rx"], item["ry"]) * 0.25
    ]
    features: dict[str, Any] = {
        "element_count": len(elements),
        "tag_counts": dict(sorted(tag_counts.items())),
        "declared_role_counts": dict(sorted(declared_role_counts.items())),
        # Backward-compatible diagnostic alias. Normative scorers must not use it.
        "role_counts": dict(sorted(declared_role_counts.items())),
        "declared_labelled_element_fraction": declared_labelled_elements / max(1, len(elements)),
        "visible_labelled_element_fraction": visible_labelled_elements
        / max(1, visible_shape_count),
        "attribute_count": attribute_count,
        "path_characters": path_characters,
        "visible_shape_count": visible_shape_count,
        "hidden_shape_count": hidden_shape_count,
        "off_canvas_shape_count": off_canvas_shape_count,
        "group_count": group_count,
        "transform_count": transform_count,
        "visible_circle_or_ellipse_count": len(visible_circles),
        "wheel_candidate_count": len(wheel_candidates),
        "wheel_pair_score": _wheel_pair_score(wheel_candidates),
        "external_reference_count": external_references,
        "event_attribute_count": event_attributes,
        "text_character_count": sum(len(item) for item in text_content),
        "view_box": root.attrib.get("viewBox"),
        "width": root.attrib.get("width"),
        "height": root.attrib.get("height"),
    }
    canonical = _canonical_tree(root)
    unique_errors = tuple(dict.fromkeys(errors))
    return SVGInspection(
        not unique_errors,
        unique_errors,
        tuple(dict.fromkeys(warnings)),
        features,
        content_hash(canonical) if not unique_errors else None,
    )


def _wheel_pair_score(candidates: Iterable[dict[str, float]]) -> float:
    values = list(candidates)
    best = 0.0
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            separation = abs(left["cx"] - right["cx"])
            vertical = abs(left["cy"] - right["cy"])
            mean_radius = max(1.0, (left["rx"] + right["rx"]) / 2)
            radius_similarity = 1 - min(1.0, abs(left["rx"] - right["rx"]) / mean_radius)
            alignment = 1 - min(1.0, vertical / mean_radius)
            separated = min(1.0, separation / (mean_radius * 2.5))
            best = max(best, max(0.0, radius_similarity * alignment * separated))
    return best


def _canonical_tree(root: Any) -> dict[str, Any]:
    def convert(element: Any) -> dict[str, Any]:
        return {
            "tag": _local_name(element.tag),
            "attributes": {
                str(key): str(value).strip() for key, value in sorted(element.attrib.items())
            },
            "text": (element.text or "").strip(),
            "children": [convert(child) for child in list(element)],
        }

    return convert(root)


def assert_safe_svg(svg: str, **kwargs: Any) -> SVGInspection:
    inspection = inspect_svg(svg, **kwargs)
    if not inspection.valid:
        raise SVGSecurityError("; ".join(inspection.errors))
    return inspection
