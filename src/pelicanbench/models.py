"""Versioned benchmark data models.

The models deliberately separate semantic scenarios, prompt formulations, experimental
conditions, stochastic trials, generated artifacts and scorer evaluations.  This avoids
mistaking repeated samples of one task for independent benchmark items.
"""

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
EvidenceLevel = Literal["E0", "E1", "E2", "E3", "E4", "E5"]


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
    """A stable experimental task, independent of model sampling randomness.

    ``scenario_id`` identifies the semantic scene. ``prompt_id`` identifies the exact
    verbalisation. ``condition_id`` identifies the intervention/track. ``task_id`` is the
    release-scoped combination of those three identifiers. ``seed`` is retained as the
    deterministic design seed and MUST NOT participate in any of those identities.
    """

    schema_version: str = "2.0.0"
    task_id: str
    scenario_id: str
    prompt_id: str
    condition_id: str
    benchmark_release: str
    track: TrackName
    prompt: str
    animal: EntitySpec
    mobile_object: EntitySpec
    relations: tuple[RelationSpec, ...]
    viewpoint: str = "side"
    style: str = "simple vector illustration"
    difficulty: int = Field(default=1, ge=1, le=5)
    seed: int = Field(ge=0, description="Design seed; trial sampling seeds are recorded separately.")
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


class QuestionAssessment(StrictModel):
    """Source-independent answer to one atomic visual question."""

    question_id: str
    dimension: str
    probability_yes: float = Field(ge=0.0, le=1.0)
    method: str
    evidence: tuple[str, ...] = ()
    judge_id: str
    judge_revision: str
    uncertainty: float | None = Field(default=None, ge=0.0, le=1.0)


class SemanticAssessment(StrictModel):
    """Frozen semantic assessment of a canonical render.

    A normative assessment must be derived only from the render (and task question), not
    from SVG IDs, classes, comments, metadata or source labels.
    """

    schema_version: str = "1.0.0"
    assessment_id: str
    task_id: str
    render_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_independent: bool
    questions: tuple[QuestionAssessment, ...]
    calibration_version: str | None = None

    @model_validator(mode="after")
    def unique_questions(self) -> "SemanticAssessment":
        question_ids = [item.question_id for item in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("semantic assessment question identifiers must be unique")
        return self

    def probabilities(self) -> dict[str, float]:
        return {item.question_id: item.probability_yes for item in self.questions}


class DimensionScore(StrictModel):
    name: str
    value: float = Field(ge=0.0, le=1.0)
    method: str
    evidence: tuple[str, ...] = ()
    uncertainty: float | None = Field(default=None, ge=0.0)


class ScoreCard(StrictModel):
    schema_version: str = "2.0.0"
    task_id: str
    submission_id: str
    render_hash: str | None = None
    semantic_assessment_id: str | None = None
    dimensions: tuple[DimensionScore, ...]
    critical_gates: dict[str, bool]
    valid: bool
    aggregate: float = Field(ge=0.0, le=1.0)
    scorer_version: str
    evidence_level: EvidenceLevel = "E2"
    warnings: tuple[str, ...] = ()


class ArtifactRecord(StrictModel):
    path: str
    media_type: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bytes: int = Field(ge=0)


class TrialRecord(StrictModel):
    """One stochastic model invocation for one stable benchmark task.

    Failed invocations remain first-class trials so benchmark denominators and provider
    reliability are not biased by silently dropping errors.
    """

    schema_version: str = "1.1.0"
    trial_id: str
    task_id: str
    scenario_id: str
    prompt_id: str
    condition_id: str
    model_id: str
    model_revision: str
    adapter_id: str
    seed: int = Field(ge=0)
    status: Literal["success", "generation-failed"] = "success"
    attempts: int = Field(default=1, ge=1)
    artifact_id: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    raw_response_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def outcome_is_coherent(self) -> "TrialRecord":
        if self.status == "success":
            if self.artifact_id is None or self.raw_response_hash is None:
                raise ValueError("successful trials require artifact and raw-response hashes")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("successful trials cannot carry failure details")
        elif not self.error_type:
            raise ValueError("failed trials require an error type")
        return self


class EvaluationRecord(StrictModel):
    """One scorer application to one trial artifact."""

    schema_version: str = "1.0.0"
    evaluation_id: str
    trial_id: str
    task_id: str
    artifact_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    render_hash: str | None = None
    scorer_version: str
    semantic_assessment_id: str | None = None
    scorecard_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class RunManifest(StrictModel):
    schema_version: str = "2.0.0"
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
    scenario_ids: tuple[str, ...] = ()
    prompt_ids: tuple[str, ...] = ()
    condition_ids: tuple[str, ...] = ()
    trial_ids: tuple[str, ...] = ()
    evaluation_ids: tuple[str, ...] = ()
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
