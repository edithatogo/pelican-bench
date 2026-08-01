"""Formal ontology interoperability and namespace-governance contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import read_json


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OntologyPatternSource(StrictModel):
    asset_id: str
    role: Literal["design-pattern", "semantic-import", "namespace-host", "validation-reference"]
    semantic_import: bool = False
    adopted_patterns: tuple[str, ...] = ()
    rationale: str

    @model_validator(mode="after")
    def coherent_import(self) -> "OntologyPatternSource":
        if self.role == "semantic-import" and not self.semantic_import:
            raise ValueError("semantic-import sources must explicitly enable semantic_import")
        if self.semantic_import and self.role != "semantic-import":
            raise ValueError("semantic_import may only be enabled for semantic-import sources")
        return self


class OntologyInteroperabilityProfile(StrictModel):
    schema_version: str = "1.0.0"
    namespace: str = Field(pattern=r"^https://")
    namespace_status: Literal["local-reservation", "registration-planned", "published"]
    registration_target: str | None = None
    registration_evidence: str | None = None
    representations: tuple[Literal["json", "json-ld", "rdf", "owl", "shacl"], ...]
    validation_surfaces: tuple[str, ...]
    competency_question_surface: str
    semantic_import_policy: str
    sources: tuple[OntologyPatternSource, ...]

    @model_validator(mode="after")
    def coherent_namespace(self) -> "OntologyInteroperabilityProfile":
        if self.namespace_status in {"registration-planned", "published"} and not self.registration_target:
            raise ValueError("planned or published namespaces require a registration target")
        if self.namespace_status == "published" and not self.registration_evidence:
            raise ValueError("published namespaces require registration evidence")
        if len(set(self.representations)) != len(self.representations):
            raise ValueError("representations must be unique")
        identifiers = [item.asset_id for item in self.sources]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("ontology pattern-source identifiers must be unique")
        return self


def load_ontology_interoperability_profile(
    path: str | Path,
) -> OntologyInteroperabilityProfile:
    return OntologyInteroperabilityProfile.model_validate(read_json(path))
