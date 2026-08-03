"""Fixture-safe sealed challenge commitments and reveals."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

from .io import content_hash


def commit_challenge(
    tasks: Iterable[Mapping[str, Any]], *, release: str, seed: int, created_at: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    values = tuple(dict(x) for x in tasks)
    key = hashlib.sha256(f"{release}:{seed}".encode()).hexdigest()
    reveals = []
    for i, item in enumerate(values):
        salt = hashlib.sha256(f"{key}:{i}".encode()).hexdigest()
        payload = {"task": item, "salt": salt}
        reveals.append(payload)
    commitments = [content_hash(x) for x in reveals]
    public = {
        "schema_version": "1.0.0",
        "release": release,
        "created_at": created_at,
        "task_count": len(values),
        "commitments": commitments,
    }
    return public, {"schema_version": "1.0.0", "reveals": reveals}


def reveal_challenge(
    commitment: Mapping[str, Any], tasks: Iterable[Mapping[str, Any]], secrets: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    values = tuple(dict(x) for x in tasks)
    reveals = tuple(dict(x) for x in secrets["reveals"])
    if [x["task"] for x in reveals] != list(values):
        raise ValueError("challenge tasks do not match committed secrets")
    return reveals


def verify_challenge(
    commitment: Mapping[str, Any],
    reveals: Iterable[Mapping[str, Any]],
    *,
    require_full: bool = False,
) -> dict[str, Any]:
    values = tuple(dict(x) for x in reveals)
    actual = [content_hash(x) for x in values]
    expected = list(commitment["commitments"])
    valid = all(x in expected for x in actual) and (not require_full or actual == expected)
    return {
        "schema_version": "1.0.0",
        "valid": valid,
        "revealed": len(values),
        "committed": len(expected),
        "full": actual == expected,
    }


__all__ = ["commit_challenge", "reveal_challenge", "verify_challenge"]
