"""Model eligibility and benchmark execution registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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

    @property
    def eligible(self) -> bool:
        return (
            self.status not in {"blocked", "retired"}
            and not self.remote_code_required
            and self.license_status in {"eligible", "reviewed", "open"}
        )


def load_registry(path: str | Path) -> list[ModelRegistryEntry]:
    value = read_json(path)
    records = value.get("models", value) if isinstance(value, dict) else value
    if not isinstance(records, list):
        raise TypeError("model registry must contain a list")
    return [ModelRegistryEntry.model_validate(item) for item in records]


def eligible_models(entries: list[ModelRegistryEntry], *, track: str) -> list[ModelRegistryEntry]:
    return [entry for entry in entries if entry.eligible and track in entry.tracks]


def registry_summary(entries: list[ModelRegistryEntry]) -> dict[str, Any]:
    return {
        "models": len(entries),
        "eligible": sum(entry.eligible for entry in entries),
        "tracks": sorted({track for entry in entries for track in entry.tracks}),
        "access_types": sorted({entry.access_type for entry in entries}),
    }
