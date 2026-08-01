"""Model eligibility, runtime profiles, and benchmark execution registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import read_json


class ModelRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_id: str
    revision: str
    tracks: tuple[str, ...]
    access_type: str
    license_status: str
    remote_code_required: bool = False
    minimum_output_tokens: int = Field(default=0, ge=0)
    status: str = "candidate"
    notes: str = ""
    first_party: bool = False
    base_model: str | None = None
    runtime_profile: str | None = None
    inference_provider_status: str = "unknown"
    provenance_sources: tuple[str, ...] = ()
    evaluation_role: Literal["fixture", "candidate", "comparison", "excluded"] = "candidate"

    @property
    def eligibility_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.status not in {"eligible", "reviewed"}:
            blockers.append(f"status:{self.status}")
        if self.revision.startswith("unresolved"):
            blockers.append("revision-unresolved")
        if self.remote_code_required:
            blockers.append("remote-code-required")
        if self.license_status not in {"eligible", "reviewed", "open"}:
            blockers.append(f"license:{self.license_status}")
        return tuple(blockers)

    @property
    def eligible(self) -> bool:
        return not self.eligibility_blockers


class RuntimePromptProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    profile_id: str
    model_ids: tuple[str, ...]
    endpoint_kind: Literal["openai-compatible", "command", "directory", "fixture"]
    first_user_prefix: str = ""
    assistant_prefill: str = ""
    system_prompt: str = (
        "Return one complete, self-contained SVG document and no explanatory prose. "
        "Do not embed raster images, scripts, external resources, or hidden text."
    )
    max_tokens: int = Field(default=12000, ge=1)
    temperature: float = Field(default=0.0, ge=0.0)
    source: str
    status: Literal["active", "experimental", "blocked", "retired"] = "experimental"
    notes: str = ""


class RuntimeProfileRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str = "1.0.0"
    policy: dict[str, str]
    profiles: tuple[RuntimePromptProfile, ...]

    @model_validator(mode="after")
    def unique_profiles(self) -> "RuntimeProfileRegistry":
        identifiers = [item.profile_id for item in self.profiles]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("runtime profile identifiers must be unique")
        return self


def load_registry(path: str | Path) -> list[ModelRegistryEntry]:
    value = read_json(path)
    records = value.get("models", value) if isinstance(value, dict) else value
    if not isinstance(records, list):
        raise TypeError("model registry must contain a list")
    return [ModelRegistryEntry.model_validate(item) for item in records]


def load_runtime_profiles(path: str | Path) -> RuntimeProfileRegistry:
    return RuntimeProfileRegistry.model_validate(read_json(path))


def runtime_profile_for_model(
    registry: RuntimeProfileRegistry,
    model_id: str,
) -> RuntimePromptProfile | None:
    matches = [profile for profile in registry.profiles if model_id in profile.model_ids]
    if len(matches) > 1:
        raise ValueError(f"multiple runtime profiles match {model_id}")
    return matches[0] if matches else None


def eligible_models(entries: list[ModelRegistryEntry], *, track: str) -> list[ModelRegistryEntry]:
    return [entry for entry in entries if entry.eligible and track in entry.tracks]


def registry_summary(entries: list[ModelRegistryEntry]) -> dict[str, Any]:
    return {
        "models": len(entries),
        "eligible": sum(entry.eligible for entry in entries),
        "first_party": sum(entry.first_party for entry in entries),
        "tracks": sorted({track for entry in entries for track in entry.tracks}),
        "access_types": sorted({entry.access_type for entry in entries}),
        "inference_provider_statuses": sorted({entry.inference_provider_status for entry in entries}),
    }
