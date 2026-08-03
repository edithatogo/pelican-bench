"""Deterministic study-protocol lock verification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .io import file_hash, read_json, write_json


@dataclass(frozen=True, slots=True)
class ProtocolVerification:
    valid: bool
    checked_files: int
    missing_files: tuple[str, ...]
    mismatched_files: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["missing_files"] = list(self.missing_files)
        value["mismatched_files"] = list(self.mismatched_files)
        return value


def write_study_protocol_lock(root: str | Path, output: str | Path) -> Path:
    """Regenerate the authoritative lock from its repository source specification."""

    project = Path(root)
    spec = read_json(project / "benchmark/protocol/lock-spec.json")
    candidate = read_json(project / str(spec["candidate_commitment_path"]))
    files = []
    for relative in spec["files"]:
        source = project / str(relative)
        if not source.is_file():
            raise FileNotFoundError(f"locked protocol file is missing: {relative}")
        files.append(
            {
                "bytes": source.stat().st_size,
                "path": str(relative),
                "sha256": file_hash(source),
            }
        )
    value = {
        "amendment_ledger_hash": file_hash(project / str(spec["amendments_path"])),
        "candidate_release": spec["candidate_release"],
        "files": files,
        "generated_at": "2026-08-03T00:00:00Z",
        "protocol_id": "pelicanbench-v1-study-protocol",
        "protocol_revision": spec["protocol_revision"],
        "schema_version": spec["schema_version"],
        "task_identity_commitment": candidate["commitment"],
    }
    return write_json(output, value)


def verify_study_protocol(
    root: str | Path, lock: str | Path | Mapping[str, Any]
) -> ProtocolVerification:
    """Verify every locked file by size and prefixed SHA-256 digest."""

    project = Path(root)
    value = read_json(lock) if isinstance(lock, (str, Path)) else dict(lock)
    records = value.get("files")
    if not isinstance(records, list):
        raise ValueError("study protocol lock files must be an array")
    missing: list[str] = []
    mismatched: list[str] = []
    for record in records:
        relative = str(record["path"])
        source = project / relative
        if not source.is_file():
            missing.append(relative)
            continue
        if source.stat().st_size != int(record["bytes"]) or file_hash(source) != record["sha256"]:
            mismatched.append(relative)
    return ProtocolVerification(
        valid=not missing and not mismatched,
        checked_files=len(records),
        missing_files=tuple(missing),
        mismatched_files=tuple(mismatched),
    )


__all__ = ["ProtocolVerification", "verify_study_protocol", "write_study_protocol_lock"]
