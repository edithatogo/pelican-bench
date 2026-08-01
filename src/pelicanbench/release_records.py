"""Portable release-package record schemas without packaging side effects."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PackagedArtifact(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    role: str


class ReleasePackageReceipt(StrictModel):
    schema_version: str = "1.0.0"
    generated_at: str
    project: str = "PelicanBench"
    version: str
    profile: str
    tag: str
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    git_clean: bool
    tag_points_at_head: bool
    assurance_ready: bool
    ecosystem_audit_passed: bool
    verification_result: str
    clean_clone_result: str
    pilot_cells: int = Field(ge=0)
    pilot_ready_cells: int = Field(ge=0)
    pilot_qualification_required_cells: int = Field(ge=0)
    publication_bundle_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    external_writes_executed: bool = False
    artifacts: tuple[PackagedArtifact, ...]
    package_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    limitations: tuple[str, ...]
