"""Versioned benchmark data models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TrackName = Literal[
    "heritage-svg",
    "compositional-svg",
    "direct-image",
    "reference-grounded",
    "repair",
    "agentic-drawing",
    "human-in-the-loop",
]
RightsStatus = Literal[
    "unknown",
    "link-only",
    "metadata-only",
    "licensed",
    "public-domain",
    "permission-granted",
    "restricted",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntitySpec(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    label: str
    ontology_ref: str
    required_features: tuple[str, ...] = ()


class RelationSpec(StrictModel):
    predicate: str
    subject: str
    object: str
    required: bool = True


class BenchmarkTask(StrictModel):
    schema_version: str = "1.0.0"
    task_id: str
    benchmark_release: str
    track: TrackName
    prompt: str
    animal: EntitySpec
    mobile_object: EntitySpec
    relations: tuple[RelationSpec, ...]
    viewpoint: str = "side"
    style: str = "simple vector illustration"
    difficulty: int = Field(default=1, ge=1, le=5)
    seed: int = Field(ge=0)
    public: bool = True
    references: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def relation_entities_exist(self) -> "BenchmarkTask":
        identifiers = {self.animal.id, self.mobile_object.id}
        for relation in self.relations:
            if relation.subject not in identifiers or relation.object not in identifiers:
                raise ValueError("relations must reference task entities")
        return self


class DimensionScore(StrictModel):
    name: str
    value: float = Field(ge=0.0, le=1.0)
    method: str
    evidence: tuple[str, ...] = ()
    uncertainty: float | None = Field(default=None, ge=0.0)


class ScoreCard(StrictModel):
    schema_version: str = "1.0.0"
    task_id: str
    submission_id: str
    dimensions: tuple[DimensionScore, ...]
    critical_gates: dict[str, bool]
    valid: bool
    aggregate: float = Field(ge=0.0, le=1.0)
    scorer_version: str
    warnings: tuple[str, ...] = ()


class ArtifactRecord(StrictModel):
    path: str
    media_type: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bytes: int = Field(ge=0)


class RunManifest(StrictModel):
    schema_version: str = "1.0.0"
    run_id: str
    created_at: str
    benchmark_release: str
    benchmark_commit: str
    model_id: str
    model_revision: str
    adapter_id: str
    environment_digest: str
    seed: int
    task_ids: tuple[str, ...]
    prompt_hashes: dict[str, str]
    configuration: dict[str, Any]
    costs: dict[str, float] = Field(default_factory=dict)
    artifacts: tuple[ArtifactRecord, ...]
    result_hash: str


class TrajectoryEvent(StrictModel):
    index: int = Field(ge=0)
    timestamp: str
    action: dict[str, Any]
    state_hash: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    error: str | None = None


class LearningProposal(StrictModel):
    learning_id: str
    track: str
    phase: str
    observation: str
    evidence: tuple[str, ...]
    attempted_strategy: str = ""
    result: str = ""
    proposed_heuristic: str
    confidence: float = Field(ge=0.0, le=1.0)
    scope: str
    contamination_risk: Literal["none", "low", "medium", "high"]
    rollback_trigger: str
    status: Literal["proposed", "validated", "promoted", "rejected", "expired"]


class SourceRecord(StrictModel):
    source_id: str
    title: str
    url: str
    creator: str | None = None
    published_at: str | None = None
    source_type: str
    rights_status: RightsStatus
    permitted_uses: tuple[str, ...] = ()
    content_hash: str | None = None
    notes: str = ""


class HistoricalObservation(StrictModel):
    observation_id: str
    source_id: str
    observed_at: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    prompt: str | None = None
    artifact_url: str | None = None
    artifact_hash: str | None = None
    rights_status: RightsStatus = "unknown"
    commentary: str | None = None
    annotations: dict[str, Any] = Field(default_factory=dict)
