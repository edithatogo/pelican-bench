"""Strict coercion helpers for external configuration and exchange payloads."""

from __future__ import annotations

from typing import Any

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def parse_bool(value: Any, *, field: str) -> bool:
    """Parse an explicit boolean without Python's truthy-string ambiguity.

    JSON booleans are preferred. Integer and string forms are accepted for command-line and
    tabular exchange surfaces, but only from a small, documented vocabulary.
    """

    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in _TRUE_VALUES:
            return True
        if normalised in _FALSE_VALUES:
            return False
    raise ValueError(f"{field} must be an explicit boolean")


__all__ = ["parse_bool"]
