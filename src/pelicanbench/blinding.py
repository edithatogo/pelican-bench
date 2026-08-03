"""Model-identity blinding and controlled unblinding for prospective studies.

The public package contains stable study-specific aliases and opaque commitments but no
raw model identifiers. The restricted mapping never contains the blinding key. A public
mapping commitment is keyed so it cannot be used to enumerate a small, already-known
model panel and recover the alias assignment.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .io import canonical_json, content_hash, read_json, read_jsonl, write_json, write_jsonl
from .timeutil import utc_now_iso

_SHA256_PREFIX = "sha256:"
_SCHEMA_VERSION = "1.1.0"
_RESTRICTED_SENSITIVITY = "restricted-unblinding-map"


@dataclass(frozen=True, slots=True)
class PublicBlindingManifest:
    schema_version: str
    study_id: str
    generated_at: str
    task_identity_commitment: str
    key_commitment: str
    mapping_commitment: str
    aliases: tuple[str, ...]
    model_count: int
    blinded: bool = True
    contains_model_identifiers: bool = False
    commitment_scheme: str = "hmac-sha256-v1"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PublicBlindingManifest:
        aliases = value.get("aliases")
        if not isinstance(aliases, list | tuple):
            raise TypeError("public blinding aliases must be a list")
        return cls(
            schema_version=str(value["schema_version"]),
            study_id=str(value["study_id"]),
            generated_at=str(value["generated_at"]),
            task_identity_commitment=str(value["task_identity_commitment"]),
            key_commitment=str(value["key_commitment"]),
            mapping_commitment=str(value["mapping_commitment"]),
            aliases=tuple(str(alias) for alias in aliases),
            model_count=int(value["model_count"]),
            blinded=bool(value.get("blinded", True)),
            contains_model_identifiers=bool(value.get("contains_model_identifiers", False)),
            commitment_scheme=str(value.get("commitment_scheme", "hmac-sha256-v1")),
        )


@dataclass(frozen=True, slots=True)
class PrivateBlindingEntry:
    model_id: str
    alias: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PrivateBlindingMap:
    schema_version: str
    study_id: str
    generated_at: str
    task_identity_commitment: str
    key_commitment: str
    mapping_commitment: str
    entries: tuple[PrivateBlindingEntry, ...]
    sensitivity: str = _RESTRICTED_SENSITIVITY
    commitment_scheme: str = "hmac-sha256-v1"

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["entries"] = [entry.as_dict() for entry in self.entries]
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PrivateBlindingMap:
        raw_entries = value.get("entries")
        if not isinstance(raw_entries, list):
            raise TypeError("private blinding entries must be a list")
        entries: list[PrivateBlindingEntry] = []
        for item in raw_entries:
            if not isinstance(item, Mapping):
                raise TypeError("private blinding entries must be objects")
            entries.append(
                PrivateBlindingEntry(model_id=str(item["model_id"]), alias=str(item["alias"]))
            )
        return cls(
            schema_version=str(value["schema_version"]),
            study_id=str(value["study_id"]),
            generated_at=str(value["generated_at"]),
            task_identity_commitment=str(value["task_identity_commitment"]),
            key_commitment=str(value["key_commitment"]),
            mapping_commitment=str(value["mapping_commitment"]),
            entries=tuple(entries),
            sensitivity=str(value.get("sensitivity", _RESTRICTED_SENSITIVITY)),
            commitment_scheme=str(value.get("commitment_scheme", "hmac-sha256-v1")),
        )


@dataclass(frozen=True, slots=True)
class BlindingVerification:
    schema_version: str
    study_id: str
    model_count: int
    public_contains_model_identifiers: bool
    mapping_commitment_matches: bool
    aliases_unique: bool
    aliases_match_private_map: bool
    key_commitment_verified: bool | None
    cryptographic_mapping_verified: bool | None
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class UnblindingAuthorization:
    """Content-addressed and keyed authorization for a controlled unblinding step."""

    schema_version: str
    study_id: str
    issued_at: str
    mapping_commitment: str
    analysis_lock_commitment: str
    data_freeze_commitment: str
    authorized_by: str
    reason: str
    authorization_mac: str
    status: str = "approved"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> UnblindingAuthorization:
        return cls(
            schema_version=str(value["schema_version"]),
            study_id=str(value["study_id"]),
            issued_at=str(value["issued_at"]),
            mapping_commitment=str(value["mapping_commitment"]),
            analysis_lock_commitment=str(value["analysis_lock_commitment"]),
            data_freeze_commitment=str(value["data_freeze_commitment"]),
            authorized_by=str(value["authorized_by"]),
            reason=str(value["reason"]),
            authorization_mac=str(value["authorization_mac"]),
            status=str(value.get("status", "approved")),
        )


def _key_bytes(key: bytes | str) -> bytes:
    value = key.encode("utf-8") if isinstance(key, str) else key
    if len(value) < 32:
        raise ValueError("blinding key must contain at least 32 bytes")
    return value


def _valid_sha256(value: str) -> bool:
    if not value.startswith(_SHA256_PREFIX):
        return False
    digest = value.removeprefix(_SHA256_PREFIX)
    return len(digest) == 64 and digest == digest.lower() and all(
        character in "0123456789abcdef" for character in digest
    )


def _key_commitment(key: bytes) -> str:
    return _SHA256_PREFIX + hashlib.sha256(key).hexdigest()


def _hmac_commitment(key: bytes, *, purpose: str, payload: object) -> str:
    message = f"pelicanbench:{purpose}:".encode("utf-8") + canonical_json(payload).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _alias_digest(key: bytes, model_id: str, *, purpose: str, study_id: str) -> str:
    message = f"pelicanbench:{study_id}:{purpose}:{model_id}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _mapping_payload(entries: Sequence[PrivateBlindingEntry]) -> list[dict[str, str]]:
    return [entry.as_dict() for entry in sorted(entries, key=lambda item: item.model_id)]


def _mapping_commitment(entries: Sequence[PrivateBlindingEntry], key: bytes) -> str:
    return _hmac_commitment(key, purpose="model-alias-map", payload=_mapping_payload(entries))


def _authorization_payload(
    *,
    study_id: str,
    issued_at: str,
    mapping_commitment: str,
    analysis_lock_commitment: str,
    data_freeze_commitment: str,
    authorized_by: str,
    reason: str,
    status: str,
) -> dict[str, str]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "study_id": study_id,
        "issued_at": issued_at,
        "mapping_commitment": mapping_commitment,
        "analysis_lock_commitment": analysis_lock_commitment,
        "data_freeze_commitment": data_freeze_commitment,
        "authorized_by": authorized_by,
        "reason": reason,
        "status": status,
    }


def build_blinding_manifests(
    model_ids: Iterable[str],
    *,
    key: bytes | str,
    study_id: str,
    task_identity_commitment: str,
    generated_at: str | None = None,
) -> tuple[PublicBlindingManifest, PrivateBlindingMap]:
    """Create deterministic public aliases and a restricted model-to-alias mapping."""
    selected_key = _key_bytes(key)
    clean_study_id = study_id.strip()
    if not clean_study_id:
        raise ValueError("study_id is required")
    if not _valid_sha256(task_identity_commitment):
        raise ValueError("task identity commitment must be a prefixed lowercase SHA-256 digest")
    values = tuple(sorted(str(model_id).strip() for model_id in model_ids))
    if not values or any(not value for value in values):
        raise ValueError("at least one nonblank model identifier is required")
    if len(set(values)) != len(values):
        raise ValueError("model identifiers must be unique")

    aliases: dict[str, str] = {}
    occupied: set[str] = set()
    for model_id in values:
        digest = _alias_digest(selected_key, model_id, purpose="alias", study_id=clean_study_id)
        length = 12
        alias = "SYS-" + digest[:length].upper()
        while alias in occupied:
            length += 2
            if length > len(digest):
                raise ValueError("unable to resolve model alias collision")
            alias = "SYS-" + digest[:length].upper()
        aliases[model_id] = alias
        occupied.add(alias)

    entries = tuple(
        PrivateBlindingEntry(model_id=model_id, alias=aliases[model_id]) for model_id in values
    )
    mapping_commitment = _mapping_commitment(entries, selected_key)
    order = tuple(
        aliases[model_id]
        for model_id in sorted(
            values,
            key=lambda item: _alias_digest(
                selected_key,
                item,
                purpose="display-order",
                study_id=clean_study_id,
            ),
        )
    )
    timestamp = generated_at or utc_now_iso()
    commitment = _key_commitment(selected_key)
    public = PublicBlindingManifest(
        schema_version=_SCHEMA_VERSION,
        study_id=clean_study_id,
        generated_at=timestamp,
        task_identity_commitment=task_identity_commitment,
        key_commitment=commitment,
        mapping_commitment=mapping_commitment,
        aliases=order,
        model_count=len(entries),
    )
    private = PrivateBlindingMap(
        schema_version=_SCHEMA_VERSION,
        study_id=clean_study_id,
        generated_at=timestamp,
        task_identity_commitment=task_identity_commitment,
        key_commitment=commitment,
        mapping_commitment=mapping_commitment,
        entries=entries,
    )
    verify_blinding_manifests(public, private, raw_model_ids=values, key=selected_key)
    return public, private


def verify_blinding_manifests(
    public: PublicBlindingManifest | Mapping[str, Any],
    private: PrivateBlindingMap | Mapping[str, Any],
    *,
    raw_model_ids: Iterable[str] | None = None,
    key: bytes | str | None = None,
    require_key: bool = False,
) -> BlindingVerification:
    """Verify public/private consistency, optionally including keyed commitments."""
    public_value = (
        public if isinstance(public, PublicBlindingManifest) else PublicBlindingManifest.from_mapping(public)
    )
    private_value = (
        private if isinstance(private, PrivateBlindingMap) else PrivateBlindingMap.from_mapping(private)
    )
    model_ids = tuple(
        str(value)
        for value in (
            raw_model_ids
            if raw_model_ids is not None
            else (entry.model_id for entry in private_value.entries)
        )
    )
    public_text = canonical_json(public_value.as_dict())
    contains_raw = any(model_id and model_id in public_text for model_id in model_ids)
    aliases = public_value.aliases
    private_aliases = tuple(entry.alias for entry in private_value.entries)
    unique = len(aliases) == len(set(aliases)) == len(private_value.entries)
    aliases_match = set(aliases) == set(private_aliases)
    commitment_matches = hmac.compare_digest(
        public_value.mapping_commitment,
        private_value.mapping_commitment,
    )
    same_study = public_value.study_id == private_value.study_id
    same_task = public_value.task_identity_commitment == private_value.task_identity_commitment
    same_key_commitment = hmac.compare_digest(
        public_value.key_commitment,
        private_value.key_commitment,
    )
    selected_key = _key_bytes(key) if key is not None else None
    key_verified: bool | None = None
    mapping_verified: bool | None = None
    if selected_key is not None:
        key_verified = hmac.compare_digest(_key_commitment(selected_key), public_value.key_commitment)
        mapping_verified = hmac.compare_digest(
            _mapping_commitment(private_value.entries, selected_key),
            public_value.mapping_commitment,
        )
    elif require_key:
        raise ValueError("a blinding key is required for cryptographic verification")

    structural = (
        not contains_raw
        and unique
        and aliases_match
        and commitment_matches
        and same_study
        and same_task
        and same_key_commitment
        and public_value.model_count == len(private_value.entries)
        and public_value.blinded
        and not public_value.contains_model_identifiers
        and public_value.commitment_scheme == "hmac-sha256-v1"
        and private_value.commitment_scheme == "hmac-sha256-v1"
        and private_value.sensitivity == _RESTRICTED_SENSITIVITY
        and _valid_sha256(public_value.task_identity_commitment)
        and _valid_sha256(public_value.key_commitment)
        and public_value.mapping_commitment.startswith("hmac-sha256:")
    )
    passed = structural and key_verified is not False and mapping_verified is not False
    result = BlindingVerification(
        schema_version=_SCHEMA_VERSION,
        study_id=private_value.study_id,
        model_count=len(private_value.entries),
        public_contains_model_identifiers=contains_raw,
        mapping_commitment_matches=commitment_matches,
        aliases_unique=unique,
        aliases_match_private_map=aliases_match,
        key_commitment_verified=key_verified,
        cryptographic_mapping_verified=mapping_verified,
        passed=passed,
    )
    if not result.passed:
        raise ValueError("model blinding manifests failed verification")
    return result


def build_unblinding_authorization(
    *,
    key: bytes | str,
    private: PrivateBlindingMap,
    analysis_lock_commitment: str,
    data_freeze_commitment: str,
    authorized_by: str,
    reason: str,
    issued_at: str | None = None,
) -> UnblindingAuthorization:
    """Create a keyed authorization after analysis and data-freeze commitments exist."""
    selected_key = _key_bytes(key)
    if not _valid_sha256(analysis_lock_commitment):
        raise ValueError("analysis lock commitment must be a prefixed lowercase SHA-256 digest")
    if not _valid_sha256(data_freeze_commitment):
        raise ValueError("data freeze commitment must be a prefixed lowercase SHA-256 digest")
    clean_author = authorized_by.strip()
    clean_reason = reason.strip()
    if not clean_author or not clean_reason:
        raise ValueError("authorized_by and reason are required")
    if not hmac.compare_digest(_key_commitment(selected_key), private.key_commitment):
        raise ValueError("blinding key does not match the private map")
    timestamp = issued_at or utc_now_iso()
    payload = _authorization_payload(
        study_id=private.study_id,
        issued_at=timestamp,
        mapping_commitment=private.mapping_commitment,
        analysis_lock_commitment=analysis_lock_commitment,
        data_freeze_commitment=data_freeze_commitment,
        authorized_by=clean_author,
        reason=clean_reason,
        status="approved",
    )
    authorization_mac = _hmac_commitment(
        selected_key,
        purpose="unblinding-authorization",
        payload=payload,
    )
    return UnblindingAuthorization(**payload, authorization_mac=authorization_mac)


def verify_unblinding_authorization(
    authorization: UnblindingAuthorization | Mapping[str, Any],
    *,
    key: bytes | str,
    private: PrivateBlindingMap,
) -> bool:
    selected_key = _key_bytes(key)
    value = (
        authorization
        if isinstance(authorization, UnblindingAuthorization)
        else UnblindingAuthorization.from_mapping(authorization)
    )
    if value.status != "approved":
        raise ValueError("unblinding authorization is not approved")
    if value.study_id != private.study_id or value.mapping_commitment != private.mapping_commitment:
        raise ValueError("unblinding authorization does not match the private map")
    if not _valid_sha256(value.analysis_lock_commitment) or not _valid_sha256(
        value.data_freeze_commitment
    ):
        raise ValueError("unblinding authorization commitments are invalid")
    payload = _authorization_payload(
        study_id=value.study_id,
        issued_at=value.issued_at,
        mapping_commitment=value.mapping_commitment,
        analysis_lock_commitment=value.analysis_lock_commitment,
        data_freeze_commitment=value.data_freeze_commitment,
        authorized_by=value.authorized_by,
        reason=value.reason,
        status=value.status,
    )
    expected = _hmac_commitment(
        selected_key,
        purpose="unblinding-authorization",
        payload=payload,
    )
    if not hmac.compare_digest(expected, value.authorization_mac):
        raise ValueError("unblinding authorization MAC is invalid")
    return True


def _alias_mapping(private: PrivateBlindingMap) -> dict[str, str]:
    mapping = {entry.model_id: entry.alias for entry in private.entries}
    if len(mapping) != len(private.entries):
        raise ValueError("private blinding map contains duplicate model identifiers")
    return mapping


def blind_records(
    records: Iterable[Mapping[str, Any]],
    private: PrivateBlindingMap,
    *,
    fields: Sequence[str] = ("model_id", "generator_model_id", "judge_model_id"),
) -> tuple[dict[str, Any], ...]:
    """Replace known top-level model identifiers with their blinded aliases."""
    mapping = _alias_mapping(private)
    output: list[dict[str, Any]] = []
    for source in records:
        record = dict(source)
        for field in fields:
            value = record.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field} must be a string when present")
            if value not in mapping:
                raise ValueError(f"unmapped model identifier in {field}: {value}")
            record[field] = mapping[value]
        output.append(record)
    return tuple(output)


def unblind_records(
    records: Iterable[Mapping[str, Any]],
    private: PrivateBlindingMap,
    *,
    fields: Sequence[str] = ("model_id", "generator_model_id", "judge_model_id"),
    authorization: UnblindingAuthorization | Mapping[str, Any] | None = None,
    key: bytes | str | None = None,
    require_authorization: bool = True,
) -> tuple[dict[str, Any], ...]:
    """Restore raw model IDs, requiring a keyed authorization by default."""
    if require_authorization:
        if authorization is None or key is None:
            raise ValueError("controlled unblinding requires an authorization and blinding key")
        verify_unblinding_authorization(authorization, key=key, private=private)
    reverse = {entry.alias: entry.model_id for entry in private.entries}
    if len(reverse) != len(private.entries):
        raise ValueError("private blinding map contains duplicate aliases")
    output: list[dict[str, Any]] = []
    for source in records:
        record = dict(source)
        for field in fields:
            value = record.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field} must be a string when present")
            if value not in reverse:
                raise ValueError(f"unknown blinded alias in {field}: {value}")
            record[field] = reverse[value]
        output.append(record)
    return tuple(output)


def write_blinding_manifests(
    public_path: str | Path,
    private_path: str | Path,
    public: PublicBlindingManifest,
    private: PrivateBlindingMap,
    *,
    key: bytes | str | None = None,
) -> None:
    verify_blinding_manifests(public, private, key=key, require_key=key is not None)
    if Path(public_path).resolve() == Path(private_path).resolve():
        raise ValueError("public and private blinding manifests require different paths")
    write_json(public_path, public.as_dict())
    write_json(private_path, private.as_dict())
    try:
        os.chmod(private_path, 0o600)
    except OSError:
        pass


def load_public_blinding_manifest(path: str | Path) -> PublicBlindingManifest:
    return PublicBlindingManifest.from_mapping(read_json(path))


def load_private_blinding_map(path: str | Path) -> PrivateBlindingMap:
    return PrivateBlindingMap.from_mapping(read_json(path))


def blind_jsonl(
    source: str | Path,
    destination: str | Path,
    private_path: str | Path,
) -> int:
    private = load_private_blinding_map(private_path)
    output = blind_records(read_jsonl(source), private)
    write_jsonl(destination, output)
    return len(output)


def unblind_jsonl(
    source: str | Path,
    destination: str | Path,
    private_path: str | Path,
    authorization_path: str | Path,
    *,
    key: bytes | str,
) -> int:
    private = load_private_blinding_map(private_path)
    authorization = UnblindingAuthorization.from_mapping(read_json(authorization_path))
    output = unblind_records(
        read_jsonl(source),
        private,
        authorization=authorization,
        key=key,
    )
    write_jsonl(destination, output)
    return len(output)


def blinding_manifest_content_hash(
    public: PublicBlindingManifest,
    private: PrivateBlindingMap,
) -> str:
    """Return a non-secret content identity for the manifest pair."""
    return content_hash(
        {
            "public": public.as_dict(),
            "private_file_commitment": content_hash(private.as_dict()),
        }
    )


__all__ = [
    "BlindingVerification",
    "PrivateBlindingEntry",
    "PrivateBlindingMap",
    "PublicBlindingManifest",
    "UnblindingAuthorization",
    "blind_jsonl",
    "blind_records",
    "blinding_manifest_content_hash",
    "build_blinding_manifests",
    "build_unblinding_authorization",
    "load_private_blinding_map",
    "load_public_blinding_manifest",
    "unblind_jsonl",
    "unblind_records",
    "verify_blinding_manifests",
    "verify_unblinding_authorization",
    "write_blinding_manifests",
]
