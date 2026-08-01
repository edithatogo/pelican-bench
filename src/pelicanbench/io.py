"""Canonical serialization, hashing, and atomic file operations."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    """Serialize a JSON-compatible value deterministically."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any, *, prefix: str = "sha256") -> str:
    """Return a prefixed SHA-256 hash of bytes or canonical JSON."""
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()}"


def file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[Any]:
    output: list[Any] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            output.append(json.loads(line))
    return output


def atomic_write_text(path: str | Path, text: str) -> None:
    """Atomically replace a UTF-8 text file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def write_json(path: str | Path, value: Any, *, pretty: bool = True) -> Path:
    target = Path(path)
    text = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        if pretty
        else canonical_json(value)
    )
    atomic_write_text(target, text + "\n")
    return target


def write_jsonl(path: str | Path, values: Iterable[Any]) -> Path:
    target = Path(path)
    atomic_write_text(
        target,
        "".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values),
    )
    return target
