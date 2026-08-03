"""Auditable integration boundaries for the edithatogo repository ecosystem.

PelicanBench deliberately reuses first-party capabilities through thin, versioned
contracts rather than copying implementations or coupling every repository into the
runtime.  The machine-readable registry records what is integrated, why it is relevant,
what evidence exists, and which apparently adjacent repositories are intentionally not
runtime dependencies.
"""

from __future__ import annotations

import shutil
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import content_hash, read_json
from .timeutil import utc_now_iso

AssetKind = Literal[
    "github-repository",
    "huggingface-model",
    "huggingface-dataset",
    "huggingface-space",
]
IntegrationClass = Literal[
    "governance",
    "provenance",
    "source-rights",
    "corpus-nlp",
    "ontology",
    "human-evaluation",
    "model-runtime",
    "agentic-drawing",
    "publication",
    "platform-publication",
    "research-methods",
]
Relevance = Literal["direct", "pattern-source", "candidate", "watch", "excluded"]
IntegrationStatus = Literal[
    "implemented",
    "contracted",
    "pattern-adopted",
    "planned",
    "blocked",
    "not-required",
]
Direction = Literal[
    "import",
    "export",
    "bidirectional",
    "adapter",
    "pattern-only",
    "publication-target",
    "none",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EcosystemAsset(StrictModel):
    asset_id: str = Field(
        pattern=r"^(github|hf-model|hf-dataset|hf-space):[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    name: str
    asset_kind: AssetKind
    integration_class: IntegrationClass
    relevance: Relevance
    status: IntegrationStatus
    direction: Direction
    required: bool = False
    capability: str
    contract: str
    interfaces: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    local_names: tuple[str, ...] = ()
    command_names: tuple[str, ...] = ()
    source_revision: str | None = None
    rationale: str
    notes: str = ""

    @model_validator(mode="after")
    def coherent_status(self) -> EcosystemAsset:
        if self.required and self.status in {"planned", "blocked", "not-required"}:
            raise ValueError("required assets must have an implemented or contracted boundary")
        if self.status in {"implemented", "contracted", "pattern-adopted"} and not self.evidence:
            raise ValueError("implemented, contracted, and pattern-adopted assets require evidence")
        if self.relevance == "excluded" and self.status != "not-required":
            raise ValueError("excluded assets must use not-required status")
        return self


class ExcludedFamily(StrictModel):
    family: str
    examples: tuple[str, ...]
    rationale: str


class EcosystemRegistry(StrictModel):
    schema_version: str = "1.0.0"
    owner: str
    policy: dict[str, str]
    assets: tuple[EcosystemAsset, ...]
    excluded_families: tuple[ExcludedFamily, ...] = ()

    @model_validator(mode="after")
    def unique_assets(self) -> EcosystemRegistry:
        identifiers = [item.asset_id for item in self.assets]
        names = [item.name for item in self.assets]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("ecosystem asset identifiers must be unique")
        if len(names) != len(set(names)):
            raise ValueError("ecosystem asset names must be unique")
        return self


class EcosystemAuditFinding(StrictModel):
    severity: Literal["info", "warning", "error"]
    code: str
    asset_id: str | None = None
    message: str
    path: str | None = None


class EcosystemAuditReport(StrictModel):
    schema_version: str = "1.0.0"
    generated_at: str
    registry_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    asset_count: int = Field(ge=0)
    status_counts: dict[str, int]
    relevance_counts: dict[str, int]
    class_counts: dict[str, int]
    evidence_files_checked: int = Field(ge=0)
    local_repositories: dict[str, str | None]
    command_availability: dict[str, bool]
    findings: tuple[EcosystemAuditFinding, ...]
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


@dataclass(frozen=True, slots=True)
class Integration:
    """Backward-compatible thin integration view used by existing callers."""

    repository: str
    capability: str
    direction: str
    required: bool
    contract: str


INTEGRATIONS = (
    Integration(
        "edithatogo/repository-standards",
        "estate governance and verification receipts",
        "import",
        True,
        "verification-receipt and repository-profile contracts",
    ),
    Integration(
        "edithatogo/krita-cli",
        "legacy agentic drawing adapter",
        "import",
        False,
        "MCP/CLI adapter",
    ),
    Integration(
        "edithatogo/sourceright",
        "source rights and citation evidence",
        "bidirectional",
        False,
        "CSL and evidence-sidecar exchange",
    ),
    Integration(
        "edithatogo/authentext",
        "publication-language review",
        "export",
        False,
        "Agent Skill review boundary",
    ),
    Integration(
        "edithatogo/nlp-policy-nz",
        "NER, relation extraction, and ontology patterns",
        "import",
        False,
        "versioned corpus-record contract",
    ),
    Integration(
        "edithatogo/open_social_data",
        "human preference and public annotation data",
        "import",
        False,
        "Arrow/Parquet dataset contract",
    ),
    Integration(
        "edithatogo/osf-cli-go",
        "preregistration and archival publication",
        "export",
        False,
        "release bundle and validation contract",
    ),
    Integration(
        "edithatogo/substack-cli-ts",
        "Substack drafting and publication",
        "export",
        False,
        "Markdown preflight and dry-run contract",
    ),
    Integration(
        "edithatogo/voiage",
        "evaluation and value-of-information methods",
        "bidirectional",
        False,
        "versioned analysis contract",
    ),
    Integration(
        "edithatogo/UOGTO",
        "formal ontology-engineering patterns",
        "import",
        False,
        "JSON-LD, SHACL, and competency-question pattern contract",
    ),
    Integration(
        "edithatogo/fyi-cli",
        "faithful source-capture patterns",
        "import",
        False,
        "WARC/WACZ and content-addressed capture pattern contract",
    ),
    Integration(
        "edithatogo/fyi-archive",
        "verified multi-mirror publication patterns",
        "import",
        False,
        "manifest and mirror-verification pattern contract",
    ),
    Integration(
        "edithatogo/postiz-agent",
        "manual social distribution",
        "export",
        False,
        "approval-gated template contract",
    ),
    Integration(
        "edithatogo/entireio-cli",
        "agent development provenance",
        "import",
        False,
        "Git checkpoint/session contract",
    ),
)


def default_registry_path(root: str | Path = ".") -> Path:
    return Path(root).resolve() / "benchmark/integrations/ecosystem-registry.json"


def load_ecosystem_registry(path: str | Path) -> EcosystemRegistry:
    return EcosystemRegistry.model_validate(read_json(path))


def locate_sibling_repositories(
    root: str | Path,
    integrations: Iterable[Integration] = INTEGRATIONS,
) -> dict[str, str | None]:
    parent = Path(root).resolve().parent
    output: dict[str, str | None] = {}
    for integration in integrations:
        name = integration.repository.rsplit("/", 1)[-1]
        candidate = parent / name
        output[integration.repository] = candidate.as_posix() if candidate.is_dir() else None
    return output


def locate_registry_repositories(
    root: str | Path,
    registry: EcosystemRegistry,
) -> dict[str, str | None]:
    parent = Path(root).resolve().parent
    output: dict[str, str | None] = {}
    for asset in registry.assets:
        if asset.asset_kind != "github-repository":
            continue
        candidates = asset.local_names or (asset.name.rsplit("/", 1)[-1],)
        found: str | None = None
        for name in candidates:
            candidate = parent / name
            if candidate.is_dir():
                found = candidate.as_posix()
                break
        output[asset.name] = found
    return output


def audit_ecosystem(
    root: str | Path,
    registry: EcosystemRegistry,
) -> EcosystemAuditReport:
    project = Path(root).resolve()
    findings: list[EcosystemAuditFinding] = []
    checked = 0
    for asset in registry.assets:
        for relative in asset.evidence:
            checked += 1
            path = project / relative
            if not path.exists():
                findings.append(
                    EcosystemAuditFinding(
                        severity="error",
                        code="missing-integration-evidence",
                        asset_id=asset.asset_id,
                        message=f"declared integration evidence is missing: {relative}",
                        path=relative,
                    )
                )
        if asset.status == "blocked":
            findings.append(
                EcosystemAuditFinding(
                    severity="warning",
                    code="blocked-external-surface",
                    asset_id=asset.asset_id,
                    message=asset.notes or "external integration is blocked",
                )
            )
        elif asset.status == "planned":
            findings.append(
                EcosystemAuditFinding(
                    severity="info",
                    code="planned-integration",
                    asset_id=asset.asset_id,
                    message=asset.rationale,
                )
            )

    local_repositories = locate_registry_repositories(project, registry)
    for asset in registry.assets:
        if asset.asset_kind != "github-repository" or not asset.local_names:
            continue
        if local_repositories.get(asset.name) is None:
            findings.append(
                EcosystemAuditFinding(
                    severity="info",
                    code="sibling-repository-not-present",
                    asset_id=asset.asset_id,
                    message="the thin integration contract is present; no sibling clone was found",
                )
            )

    command_names = sorted({name for asset in registry.assets for name in asset.command_names})
    command_availability = {name: shutil.which(name) is not None for name in command_names}
    for name, available in command_availability.items():
        if not available:
            findings.append(
                EcosystemAuditFinding(
                    severity="info",
                    code="optional-command-unavailable",
                    message=f"optional integration command is not installed: {name}",
                )
            )

    payload = registry.model_dump(mode="json")
    errors = [item for item in findings if item.severity == "error"]
    return EcosystemAuditReport(
        generated_at=utc_now_iso(),
        registry_hash=content_hash(payload),
        asset_count=len(registry.assets),
        status_counts=dict(sorted(Counter(item.status for item in registry.assets).items())),
        relevance_counts=dict(sorted(Counter(item.relevance for item in registry.assets).items())),
        class_counts=dict(
            sorted(Counter(item.integration_class for item in registry.assets).items())
        ),
        evidence_files_checked=checked,
        local_repositories=local_repositories,
        command_availability=command_availability,
        findings=tuple(findings),
        passed=not errors,
    )
