"""Content-addressed analysis and data freezes for controlled unblinding.

A study freeze commits to repository-relative files, the locked study protocol, the
candidate task identity, and, for a data freeze, the exact campaign-ledger head. The
human-readable generation timestamp is provenance only and is deliberately excluded
from the scientific identity so an identical freeze can be rebuilt deterministically.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import canonical_json, content_hash, file_hash, read_json, read_jsonl, write_json
from .timeutil import utc_now_iso

FreezeType = Literal["analysis-lock", "data-freeze"]
_FREEZE_TYPES = frozenset({"analysis-lock", "data-freeze"})
_RESTRICTED_PATH_MARKERS = (
    ".secrets",
    "private-blinding",
    "unblinding-map",
    "unblinded.jsonl",
)
_SCHEMA_VERSION = "1.0.0"


def _freeze_type(value: object) -> FreezeType:
    selected = str(value)
    if selected not in _FREEZE_TYPES:
        raise ValueError(f"unsupported study freeze type: {selected}")
    return cast(FreezeType, selected)


def _valid_sha256(value: str) -> bool:
    if not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return (
        len(digest) == 64
        and digest == digest.lower()
        and all(character in "0123456789abcdef" for character in digest)
    )


def _validate_timestamp(value: str, *, field: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    parsed.astimezone(UTC)


def _canonical_object(value: Mapping[str, object] | None, *, field: str) -> dict[str, object]:
    """Return an isolated JSON-compatible object with deterministic key ordering."""
    selected: object = {} if value is None else dict(value)
    try:
        copied = json.loads(canonical_json(selected))
    except (TypeError, ValueError) as error:
        raise TypeError(f"{field} must be JSON-compatible") from error
    if not isinstance(copied, dict):  # Defensive; the input type already requires a mapping.
        raise TypeError(f"{field} must be an object")
    return cast(dict[str, object], copied)


def _normalise_ledger_head(value: Mapping[str, object] | None) -> dict[str, object] | None:
    if value is None:
        return None
    selected: Mapping[str, object] = value
    if "valid" in value and value.get("valid") is not True:
        raise ValueError("campaign ledger verification must be valid")
    nested = value.get("head")
    if nested is not None:
        if not isinstance(nested, Mapping):
            raise TypeError("study freeze ledger verification head must be an object")
        selected = cast(Mapping[str, object], nested)
    head = _canonical_object(selected, field="study freeze ledger_head")
    required = {
        "schema_version",
        "event_count",
        "last_event_hash",
        "ledger_hash",
        "size_bytes",
    }
    missing = sorted(required.difference(head))
    if missing:
        raise ValueError("study freeze ledger_head is missing: " + ", ".join(missing))
    if str(head["schema_version"]) != "1.0.0":
        raise ValueError("unsupported campaign ledger head schema")
    event_count = head["event_count"]
    size_bytes = head["size_bytes"]
    if isinstance(event_count, bool) or not isinstance(event_count, int) or event_count < 1:
        raise ValueError("study freeze ledger_head event_count must be a positive integer")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 1:
        raise ValueError("study freeze ledger_head size_bytes must be a positive integer")
    ledger_hash = str(head["ledger_hash"])
    last_event_hash = head["last_event_hash"]
    if not _valid_sha256(ledger_hash):
        raise ValueError("study freeze ledger_hash must be a lowercase SHA-256 digest")
    if not isinstance(last_event_hash, str) or not _valid_sha256(last_event_hash):
        raise ValueError("study freeze last_event_hash must be a lowercase SHA-256 digest")
    return head


class StrictFreezeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenFileRecord(StrictFreezeModel):
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class CampaignLedgerHeadRecord(StrictFreezeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    event_count: int = Field(ge=1)
    last_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class StudyFreezeManifestRecord(StrictFreezeModel):
    """Public machine contract for analysis-lock and data-freeze manifests."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    study_id: str = Field(min_length=1)
    freeze_type: FreezeType
    generated_at: str = Field(min_length=1)
    task_identity_commitment: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    protocol_lock_path: str = Field(min_length=1)
    protocol_lock_commitment: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_head: CampaignLedgerHeadRecord | None = None
    files: tuple[FrozenFileRecord, ...] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    freeze_commitment: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def coherent_freeze_type(self) -> Self:
        _validate_timestamp(self.generated_at, field="study freeze generated_at")
        if self.freeze_type == "analysis-lock" and self.ledger_head is not None:
            raise ValueError("analysis locks cannot contain a campaign ledger head")
        if self.freeze_type == "data-freeze" and self.ledger_head is None:
            raise ValueError("data freezes require a committed campaign ledger head")
        paths = tuple(item.relative_path for item in self.files)
        if len(paths) != len(set(paths)):
            raise ValueError("study freeze contains duplicate file paths")
        return self


@dataclass(frozen=True, slots=True)
class FrozenFile:
    relative_path: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> FrozenFile:
        item = cls(
            relative_path=str(value["relative_path"]),
            sha256=str(value["sha256"]),
            size_bytes=int(value["size_bytes"]),
        )
        if not item.relative_path.strip():
            raise ValueError("study freeze file path cannot be blank")
        if not _valid_sha256(item.sha256):
            raise ValueError("study freeze file hash must be a lowercase SHA-256 digest")
        if item.size_bytes < 0:
            raise ValueError("study freeze file size cannot be negative")
        return item


def _ledger_file_matches_head(path: Path, head: Mapping[str, object]) -> bool:
    """Verify that one frozen JSONL ledger is exactly the committed ledger head."""
    if file_hash(path) != str(head["ledger_hash"]):
        return False
    if path.stat().st_size != int(str(head["size_bytes"])):
        return False
    try:
        records = read_jsonl(path)
    except (OSError, ValueError):
        return False
    if len(records) != int(str(head["event_count"])) or not records:
        return False
    final = records[-1]
    if not isinstance(final, Mapping):
        return False
    return final.get("event_hash") == head["last_event_hash"]


def _ledger_head_matches_files(
    project: Path,
    files: Iterable[FrozenFile],
    head: Mapping[str, object],
) -> bool:
    for item in files:
        if item.sha256 != head["ledger_hash"] or item.size_bytes != head["size_bytes"]:
            continue
        try:
            _, candidate = _safe_relative_file(project, item.relative_path)
        except (FileNotFoundError, ValueError):
            continue
        if _ledger_file_matches_head(candidate, head):
            return True
    return False


@dataclass(frozen=True, slots=True)
class StudyFreezeManifest:
    schema_version: str
    study_id: str
    freeze_type: FreezeType
    generated_at: str
    task_identity_commitment: str
    protocol_lock_path: str
    protocol_lock_commitment: str
    ledger_head: dict[str, object] | None
    files: tuple[FrozenFile, ...]
    metadata: dict[str, object]
    freeze_commitment: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "study_id": self.study_id,
            "freeze_type": self.freeze_type,
            "generated_at": self.generated_at,
            "task_identity_commitment": self.task_identity_commitment,
            "protocol_lock_path": self.protocol_lock_path,
            "protocol_lock_commitment": self.protocol_lock_commitment,
            "ledger_head": self.ledger_head,
            "files": [item.as_dict() for item in self.files],
            "metadata": self.metadata,
            "freeze_commitment": self.freeze_commitment,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> StudyFreezeManifest:
        files = value.get("files")
        if not isinstance(files, (list, tuple)):
            raise TypeError("study freeze files must be a list")
        parsed = StudyFreezeManifestRecord.model_validate(value)
        return cls(
            schema_version=parsed.schema_version,
            study_id=parsed.study_id,
            freeze_type=parsed.freeze_type,
            generated_at=parsed.generated_at,
            task_identity_commitment=parsed.task_identity_commitment,
            protocol_lock_path=parsed.protocol_lock_path,
            protocol_lock_commitment=parsed.protocol_lock_commitment,
            ledger_head=(
                None
                if parsed.ledger_head is None
                else cast(dict[str, object], parsed.ledger_head.model_dump(mode="json"))
            ),
            files=tuple(
                FrozenFile(
                    relative_path=item.relative_path,
                    sha256=item.sha256,
                    size_bytes=item.size_bytes,
                )
                for item in parsed.files
            ),
            metadata=_canonical_object(parsed.metadata, field="study freeze metadata"),
            freeze_commitment=parsed.freeze_commitment,
        )


@dataclass(frozen=True, slots=True)
class StudyFreezeVerification:
    schema_version: str
    study_id: str
    freeze_type: FreezeType
    file_count: int
    missing_files: tuple[str, ...]
    mismatched_files: tuple[str, ...]
    protocol_lock_matches: bool
    freeze_commitment_matches: bool
    generated_at_valid: bool
    ledger_head_valid: bool
    ledger_file_matches: bool
    canonical_file_order: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _freeze_payload(manifest: StudyFreezeManifest) -> dict[str, object]:
    return {
        "schema_version": manifest.schema_version,
        "study_id": manifest.study_id,
        "freeze_type": manifest.freeze_type,
        "task_identity_commitment": manifest.task_identity_commitment,
        "protocol_lock_path": manifest.protocol_lock_path,
        "protocol_lock_commitment": manifest.protocol_lock_commitment,
        "ledger_head": manifest.ledger_head,
        "files": [item.as_dict() for item in manifest.files],
        "metadata": manifest.metadata,
    }


def _safe_relative_file(project: Path, value: str | Path) -> tuple[str, Path]:
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError("study freeze inputs must be repository-relative")
    lowered = relative.as_posix().lower()
    if any(marker in lowered for marker in _RESTRICTED_PATH_MARKERS):
        raise ValueError(f"restricted file cannot enter a study freeze: {relative}")
    project_root = project.resolve()
    unresolved = project / relative
    if unresolved.is_symlink():
        raise ValueError(f"study freeze inputs cannot be symbolic links: {relative}")
    candidate = unresolved.resolve()
    try:
        normalised = candidate.relative_to(project_root)
    except ValueError as error:
        raise ValueError(f"study freeze input escapes repository root: {relative}") from error
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return normalised.as_posix(), candidate


def _validate_manifest_fields(value: StudyFreezeManifest) -> bool:
    # Check stable domain errors before Pydantic so callers receive the benchmark
    # contract's messages rather than version-specific validation wording.
    if value.schema_version != _SCHEMA_VERSION:
        raise ValueError(f"unsupported study freeze schema: {value.schema_version}")
    if not value.study_id.strip():
        raise ValueError("study freeze study_id is required")
    _validate_timestamp(value.generated_at, field="study freeze generated_at")
    if not _valid_sha256(value.task_identity_commitment):
        raise ValueError("study freeze task commitment is invalid")
    if not _valid_sha256(value.protocol_lock_commitment):
        raise ValueError("study freeze protocol commitment is invalid")
    if not _valid_sha256(value.freeze_commitment):
        raise ValueError("study freeze commitment is invalid")
    if value.freeze_type == "analysis-lock" and value.ledger_head is not None:
        raise ValueError("analysis locks cannot contain a campaign ledger head")
    if value.freeze_type == "data-freeze" and value.ledger_head is None:
        raise ValueError("data freezes require a committed campaign ledger head")
    if value.ledger_head is not None:
        _normalise_ledger_head(value.ledger_head)
    canonical_json(value.metadata)
    StudyFreezeManifestRecord.model_validate(value.as_dict())
    return True


def build_study_freeze(
    root: str | Path,
    inputs: Iterable[str | Path],
    *,
    study_id: str,
    freeze_type: FreezeType,
    task_identity_commitment: str,
    protocol_lock_path: str | Path = "benchmark/protocol/v1-study-lock.json",
    ledger_head: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
    generated_at: str | None = None,
) -> StudyFreezeManifest:
    """Build a deterministic commitment to the exact frozen study inputs."""
    project = Path(root)
    selected_type = _freeze_type(freeze_type)
    clean_study_id = study_id.strip()
    if not clean_study_id:
        raise ValueError("study_id is required")
    if not _valid_sha256(task_identity_commitment):
        raise ValueError("task identity commitment must be a lowercase SHA-256 digest")
    timestamp = generated_at or utc_now_iso()
    _validate_timestamp(timestamp, field="generated_at")
    selected_head = _normalise_ledger_head(ledger_head)
    if selected_type == "analysis-lock" and selected_head is not None:
        raise ValueError("analysis locks cannot contain a campaign ledger head")
    if selected_type == "data-freeze" and selected_head is None:
        raise ValueError("data freezes require a committed campaign ledger head")

    protocol_relative, protocol_path = _safe_relative_file(project, protocol_lock_path)
    selected_files: list[FrozenFile] = []
    seen: set[str] = set()
    for value in inputs:
        relative, candidate = _safe_relative_file(project, value)
        if relative == protocol_relative:
            continue
        if relative in seen:
            raise ValueError(f"duplicate study freeze input: {relative}")
        seen.add(relative)
        selected_files.append(
            FrozenFile(
                relative_path=relative,
                sha256=file_hash(candidate),
                size_bytes=candidate.stat().st_size,
            )
        )
    if not selected_files:
        raise ValueError("study freeze requires at least one input file")
    selected_files.sort(key=lambda item: item.relative_path)
    if (
        selected_type == "data-freeze"
        and selected_head is not None
        and not _ledger_head_matches_files(project, selected_files, selected_head)
    ):
        raise ValueError(
            "data freeze must include the exact campaign ledger JSONL committed by ledger_head"
        )
    selected_metadata = _canonical_object(metadata, field="study freeze metadata")
    provisional = StudyFreezeManifest(
        schema_version=_SCHEMA_VERSION,
        study_id=clean_study_id,
        freeze_type=selected_type,
        generated_at=timestamp,
        task_identity_commitment=task_identity_commitment,
        protocol_lock_path=protocol_relative,
        protocol_lock_commitment=file_hash(protocol_path),
        ledger_head=selected_head,
        files=tuple(selected_files),
        metadata=selected_metadata,
        freeze_commitment="sha256:" + "0" * 64,
    )
    return replace(provisional, freeze_commitment=content_hash(_freeze_payload(provisional)))


def verify_study_freeze(
    root: str | Path,
    manifest: StudyFreezeManifest | Mapping[str, Any],
) -> StudyFreezeVerification:
    """Verify all frozen bytes and the manifest commitment against a repository tree."""
    project = Path(root)
    value = (
        manifest
        if isinstance(manifest, StudyFreezeManifest)
        else StudyFreezeManifest.from_mapping(manifest)
    )
    _validate_manifest_fields(value)
    paths = tuple(item.relative_path for item in value.files)
    if len(set(paths)) != len(paths):
        raise ValueError("study freeze contains duplicate file paths")
    canonical_order = paths == tuple(sorted(paths))
    missing: list[str] = []
    mismatched: list[str] = []
    for item in value.files:
        try:
            _, candidate = _safe_relative_file(project, item.relative_path)
        except FileNotFoundError:
            missing.append(item.relative_path)
            continue
        if item.size_bytes != candidate.stat().st_size or item.sha256 != file_hash(candidate):
            mismatched.append(item.relative_path)
    try:
        _, protocol_path = _safe_relative_file(project, value.protocol_lock_path)
    except FileNotFoundError:
        protocol_matches = False
    else:
        protocol_matches = value.protocol_lock_commitment == file_hash(protocol_path)
    commitment_matches = value.freeze_commitment == content_hash(_freeze_payload(value))
    ledger_valid = (
        value.ledger_head is None or _normalise_ledger_head(value.ledger_head) is not None
    )
    ledger_file_matches = value.ledger_head is None or _ledger_head_matches_files(
        project, value.files, value.ledger_head
    )
    passed = (
        not missing
        and not mismatched
        and protocol_matches
        and commitment_matches
        and canonical_order
        and ledger_valid
        and ledger_file_matches
    )
    return StudyFreezeVerification(
        schema_version=_SCHEMA_VERSION,
        study_id=value.study_id,
        freeze_type=value.freeze_type,
        file_count=len(value.files),
        missing_files=tuple(sorted(missing)),
        mismatched_files=tuple(sorted(mismatched)),
        protocol_lock_matches=protocol_matches,
        freeze_commitment_matches=commitment_matches,
        generated_at_valid=True,
        ledger_head_valid=ledger_valid,
        ledger_file_matches=ledger_file_matches,
        canonical_file_order=canonical_order,
        passed=passed,
    )


def authorization_commitments(
    analysis_lock: StudyFreezeManifest,
    data_freeze: StudyFreezeManifest,
) -> tuple[str, str]:
    """Return compatible commitments for a controlled unblinding authorization."""
    _validate_manifest_fields(analysis_lock)
    _validate_manifest_fields(data_freeze)
    if analysis_lock.freeze_type != "analysis-lock":
        raise ValueError("analysis_lock manifest has the wrong freeze type")
    if data_freeze.freeze_type != "data-freeze":
        raise ValueError("data_freeze manifest has the wrong freeze type")
    fields = ("study_id", "task_identity_commitment", "protocol_lock_commitment")
    for field in fields:
        if getattr(analysis_lock, field) != getattr(data_freeze, field):
            raise ValueError(f"analysis and data freezes differ on {field}")
    return analysis_lock.freeze_commitment, data_freeze.freeze_commitment


def load_study_freeze(path: str | Path) -> StudyFreezeManifest:
    return StudyFreezeManifest.from_mapping(read_json(path))


def write_study_freeze(path: str | Path, manifest: StudyFreezeManifest) -> Path:
    _validate_manifest_fields(manifest)
    if manifest.freeze_commitment != content_hash(_freeze_payload(manifest)):
        raise ValueError("study freeze manifest has an invalid commitment")
    return write_json(path, manifest.as_dict())


__all__ = [
    "FreezeType",
    "FrozenFile",
    "StudyFreezeManifest",
    "StudyFreezeManifestRecord",
    "StudyFreezeVerification",
    "authorization_commitments",
    "build_study_freeze",
    "load_study_freeze",
    "verify_study_freeze",
    "write_study_freeze",
]
