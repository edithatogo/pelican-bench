"""Bounded SVG security inspection, canonicalisation, and structural features."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

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
FORBIDDEN_TAGS = {"script", "foreignObject", "image", "iframe", "audio", "video", "use"}
EVENT_ATTRIBUTE = re.compile(r"^on[a-z]+", re.IGNORECASE)
UNSAFE_CSS = re.compile(r"url\s*\(|expression\s*\(|@import", re.IGNORECASE)
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
ROLE_SPLIT = re.compile(r"[^a-z0-9]+")


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
        return SVGInspection(False, (f"XML parse failure: {type(exc).__name__}: {exc}",), (), {}, None)
    if _local_name(root.tag) != "svg":
        errors.append("root element must be svg")

    elements = list(root.iter())
    if len(elements) > max_elements:
        errors.append(f"element limit exceeded ({len(elements)} > {max_elements})")

    tag_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    path_characters = 0
    external_references = 0
    event_attributes = 0
    circles: list[dict[str, float]] = []
    text_content: list[str] = []
    attribute_count = 0
    labelled_elements = 0

    for element in elements:
        tag = _local_name(element.tag)
        tag_counts[tag] += 1
        if tag in FORBIDDEN_TAGS:
            errors.append(f"forbidden element: {tag}")
        elif tag not in ALLOWED_TAGS:
            errors.append(f"unsupported element: {tag}")
        roles = _role_tokens(element)
        if roles:
            labelled_elements += 1
            role_counts.update(roles)
        attribute_count += len(element.attrib)
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
            if local_attribute in {"fill", "stroke", "filter", "clip-path", "mask"}:
                if _is_external_reference(candidate) or (
                    "url(" in candidate.lower()
                    and not re.fullmatch(r"url\(\s*#[^)]+\s*\)", candidate, re.IGNORECASE)
                ):
                    errors.append(f"unsafe paint/filter reference: {candidate}")
        if tag == "path":
            path_characters += len(str(element.attrib.get("d", "")))
        if tag in {"circle", "ellipse"}:
            circles.append(
                {
                    "cx": _float(element.attrib.get("cx")),
                    "cy": _float(element.attrib.get("cy")),
                    "rx": _float(element.attrib.get("r") or element.attrib.get("rx")),
                    "ry": _float(element.attrib.get("r") or element.attrib.get("ry")),
                }
            )
        if tag in {"text", "title", "desc"} and element.text:
            text_content.append(element.text.strip())
    if path_characters > max_path_characters:
        errors.append(
            f"path data limit exceeded ({path_characters} > {max_path_characters})"
        )
    if tag_counts["text"]:
        warnings.append("visible text is present; text shortcuts are scored separately")

    wheel_candidates = [
        item
        for item in circles
        if item["rx"] >= 8
        and item["ry"] >= 8
        and abs(item["rx"] - item["ry"]) <= max(item["rx"], item["ry"]) * 0.25
    ]
    role_groups = {
        "animal": _has_any(role_counts, {"animal", "bird", "pelican", "body"}),
        "pelican_bill": _has_any(role_counts, {"bill", "beak"}),
        "pelican_pouch": _has_any(role_counts, {"pouch", "gular"}),
        "wing": _has_any(role_counts, {"wing", "wings"}),
        "foot": _has_any(role_counts, {"foot", "feet", "webbed"}),
        "vehicle": _has_any(role_counts, {"vehicle", "bicycle", "bike", "tuktuk", "scooter"}),
        "frame": _has_any(role_counts, {"frame", "chassis"}),
        "handlebar": _has_any(role_counts, {"handlebar", "handlebars", "steering"}),
        "pedal": _has_any(role_counts, {"pedal", "pedals", "crank"}),
        "saddle": _has_any(role_counts, {"saddle", "seat"}),
        "contact": _has_any(role_counts, {"contact", "riding", "rider", "grip"}),
    }
    features: dict[str, Any] = {
        "element_count": len(elements),
        "tag_counts": dict(sorted(tag_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "role_groups": role_groups,
        "labelled_element_fraction": labelled_elements / max(1, len(elements)),
        "attribute_count": attribute_count,
        "path_characters": path_characters,
        "circle_or_ellipse_count": len(circles),
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
        tuple(warnings),
        features,
        content_hash(canonical) if not unique_errors else None,
    )


def _has_any(counter: Counter[str], values: set[str]) -> bool:
    return any(counter[value] > 0 for value in values)


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
