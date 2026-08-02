"""Reproducible, rights-aware publication bundle generation.

This module exports stable hand-off contracts for Dylan's existing SourceRight,
Authentext, Substack, OSF, and arXiv tooling.  It never performs an authenticated
publication action itself.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .io import content_hash, read_json, write_json
from .timeutil import utc_now_iso


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicationAction(StrictModel):
    action_id: str
    tool: str
    mode: Literal["local-check", "agent-review", "dry-run", "manual-write"]
    description: str
    command: tuple[str, ...] = ()
    input_paths: tuple[str, ...] = ()
    requires_configuration: tuple[str, ...] = ()
    writes_external: bool = False
    approval_required: bool = False


class PublicationPlan(StrictModel):
    schema_version: str = "1.0.0"
    generated_at: str
    project: str
    policy: dict[str, str]
    actions: tuple[PublicationAction, ...]


class PublicationBundleFile(StrictModel):
    path: str
    sha256: str
    size_bytes: int


class PublicationBundleManifest(StrictModel):
    schema_version: str = "1.0.0"
    generated_at: str
    project: str
    bundle_hash: str
    files: tuple[PublicationBundleFile, ...]
    external_writes_executed: bool = False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def source_registry_to_csl(source_registry: dict[str, object]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    records = source_registry.get("sources", [])
    if not isinstance(records, list):
        raise TypeError("source registry sources must be a list")
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("source records must be objects")
        source_type = str(record.get("source_type", "web-post"))
        csl_type = "software" if source_type == "software" else "webpage"
        item: dict[str, object] = {
            "id": str(record["source_id"]),
            "type": csl_type,
            "title": str(record["title"]),
            "URL": str(record["url"]),
            "note": str(record.get("notes", "")),
        }
        creator = record.get("creator")
        if creator:
            item["author"] = [{"literal": str(creator)}]
        published = record.get("published_at")
        if isinstance(published, str) and len(published) >= 4 and published[:4].isdigit():
            item["issued"] = {"date-parts": [[int(published[:4])]]}
        output.append(item)
    return sorted(output, key=lambda item: str(item["id"]))


def default_publication_plan() -> PublicationPlan:
    return PublicationPlan(
        generated_at=utc_now_iso(),
        project="PelicanBench",
        policy={
            "source_of_truth": "Repository Markdown, LaTeX, CSL, manifests, and evidence artifacts remain canonical.",
            "writes": "No authenticated external write is performed by bundle generation.",
            "review": "Authentext and scholarly agents review frozen drafts; they do not invent empirical results.",
            "rights": "Only source metadata and repository-authored material are copied into the bundle.",
        },
        actions=(
            PublicationAction(
                action_id="sourceright-validate",
                tool="sourceright",
                mode="local-check",
                description="Validate canonical CSL records and generate an evidence/review report.",
                command=(
                    "sourceright",
                    "validate-csl",
                    "--json",
                    ".sourceright/references.csl.json",
                ),
                input_paths=(".sourceright/references.csl.json",),
            ),
            PublicationAction(
                action_id="sourceright-report",
                tool="sourceright",
                mode="local-check",
                description=(
                    "Inspect citation verification coverage from the CSL-only SourceRight "
                    "workspace. A degraded-coverage diagnostic is expected until provider "
                    "verification sidecars are added."
                ),
                command=("sourceright", "report", "--json", ".sourceright"),
                input_paths=(".sourceright",),
            ),
            PublicationAction(
                action_id="authentext-review",
                tool="authentext",
                mode="agent-review",
                description="Review Substack and manuscript drafts using the portable Authentext Agent Skill.",
                input_paths=("substack", "arxiv", "review/authentext-brief.md"),
                requires_configuration=("Authentext SKILL.md and references available to the reviewing agent",),
            ),
            PublicationAction(
                action_id="scholarly-integrity-review",
                tool="scholarly-publishing-agents",
                mode="agent-review",
                description=(
                    "Review methods, limitations, research-integrity disclosures, and "
                    "release-to-manuscript traceability without adding unobserved results."
                ),
                input_paths=("arxiv", "review/scholarly-review-brief.md", "evidence"),
                requires_configuration=(
                    "local clone or installed skill/rule surface for edithatogo/scholarly-publishing-agents",
                ),
            ),
            PublicationAction(
                action_id="substack-preflight",
                tool="substack-cli",
                mode="local-check",
                description="Run strict publication preflight without creating a draft.",
                command=("substack-cli", "preflight", "substack/post-01-draft.md", "--strict"),
                input_paths=("substack/post-01-draft.md",),
            ),
            PublicationAction(
                action_id="substack-draft-dry-run",
                tool="substack-cli",
                mode="dry-run",
                description="Render and inspect the draft payload without writing to Substack.",
                command=("substack-cli", "draft", "substack/post-01-draft.md", "--dry-run"),
                input_paths=("substack/post-01-draft.md",),
                requires_configuration=("SUBSTACK_PUBLICATION_URL",),
            ),
            PublicationAction(
                action_id="postiz-social-draft",
                tool="postiz-agent",
                mode="manual-write",
                description=(
                    "Create or schedule reviewed social-distribution drafts from the "
                    "template only after replacing every placeholder and approving each "
                    "target account, time, text, link, and uploaded media URL."
                ),
                command=(
                    "postiz",
                    "posts:create",
                    "--json",
                    "distribution/postiz-post-template.json",
                ),
                input_paths=(
                    "distribution/postiz-post-template.json",
                    "substack/post-01-draft.md",
                ),
                requires_configuration=(
                    "POSTIZ authentication",
                    "reviewed integration IDs",
                    "future publication time",
                    "published article URL",
                    "uploaded media URLs where used",
                ),
                writes_external=True,
                approval_required=True,
            ),
            PublicationAction(
                action_id="osf-validate",
                tool="osf-cli-go",
                mode="local-check",
                description="Validate an existing OSF node against the research-output profile.",
                command=("osf", "validate", "<OSF_NODE_ID>", "--profile", "research-output", "--json"),
                input_paths=("osf/project-metadata.json", "manifest.json", "evidence"),
                requires_configuration=("OSF_NODE_ID",),
            ),
            PublicationAction(
                action_id="osf-upload",
                tool="osf-cli-go",
                mode="manual-write",
                description="Upload the frozen bundle only after rights, metadata, and release review.",
                command=("osf", "files", "upload", "--node", "<OSF_NODE_ID>", "<BUNDLE_ARCHIVE>"),
                input_paths=("manifest.json", "SHA256SUMS"),
                requires_configuration=("OSF_TOKEN", "OSF_NODE_ID", "BUNDLE_ARCHIVE"),
                writes_external=True,
                approval_required=True,
            ),
            PublicationAction(
                action_id="arxiv-template-quality",
                tool="arxiv-paper-template",
                mode="local-check",
                description=(
                    "Copy the prepared paper directory into the dedicated template and run "
                    "its reproducible quality target."
                ),
                command=("make", "quality"),
                input_paths=(
                    "arxiv/paper/main.tex",
                    "arxiv/paper/metadata.json",
                    "arxiv/paper/references.bib",
                    ".sourceright/references.csl.json",
                ),
                requires_configuration=("local clone of edithatogo/arxiv-paper-template",),
            ),
        ),
    )


def build_publication_bundle(
    root: str | Path,
    output_directory: str | Path,
    *,
    include_artifacts: tuple[str | Path, ...] = (),
    overwrite: bool = False,
) -> PublicationBundleManifest:
    project = Path(root).resolve()
    output = Path(output_directory).resolve()
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise FileExistsError(f"publication bundle destination is not empty: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    required_paths = (
        "publications/substack",
        "publications/arxiv",
        "CITATION.cff",
        "data/sources/source-registry.json",
        "data/sources/rights-ledger.json",
        "docs/benchmark-card.md",
        "docs/data-card.md",
        "docs/scorer-card.md",
        "docs/empirical-basis.md",
        "docs/human-evaluation-protocol.md",
        "docs/v1-pilot-amendment-001.md",
        "docs/v1-pilot-analysis-plan.md",
        "benchmark/tasks/v1-candidate-design.json",
        "benchmark/tasks/v1-candidate-commitment.json",
        "benchmark/tasks/v1-candidate.jsonl",
        "benchmark/tasks/v1-candidate-canary.jsonl",
        "benchmark/models/prospective-panel.json",
        "benchmark/judges/prospective-panel.json",
        "benchmark/judges/canary-manifest.json",
        "benchmark/human-calibration/study-spec.json",
        "benchmark/evidence/snapshots/castillo-2026-empirical-nlp-report.json",
        "benchmark/evidence/snapshots/castillo-2026-design-coverage.json",
        "benchmark/evidence/snapshots/model-qualification-plan.json",
        "benchmark/evidence/snapshots/judge-qualification-plan.json",
        "benchmark/evidence/snapshots/prospective-pilot-plan.json",
        "benchmark/tasks/v1-pilot-commitment.json",
        "benchmark/assurance-case.json",
        "benchmark/integrations/ecosystem-registry.json",
        "benchmark/ontologies/interoperability-profile.json",
    )
    destination_map = {
        "publications/substack": "substack",
        "publications/arxiv": "arxiv/paper",
        "CITATION.cff": "metadata/CITATION.cff",
        "data/sources/source-registry.json": "sources/source-registry.json",
        "data/sources/rights-ledger.json": "sources/rights-ledger.json",
        "docs/benchmark-card.md": "documentation/benchmark-card.md",
        "docs/data-card.md": "documentation/data-card.md",
        "docs/scorer-card.md": "documentation/scorer-card.md",
        "docs/empirical-basis.md": "documentation/empirical-basis.md",
        "docs/human-evaluation-protocol.md": "documentation/human-evaluation-protocol.md",
        "docs/v1-pilot-amendment-001.md": "documentation/v1-pilot-amendment-001.md",
        "docs/v1-pilot-analysis-plan.md": "documentation/v1-pilot-analysis-plan.md",
        "benchmark/tasks/v1-candidate-design.json": "candidate/v1-candidate-design.json",
        "benchmark/tasks/v1-candidate-commitment.json": "candidate/v1-candidate-commitment.json",
        "benchmark/tasks/v1-candidate.jsonl": "candidate/v1-candidate.jsonl",
        "benchmark/tasks/v1-candidate-canary.jsonl": "candidate/v1-candidate-canary.jsonl",
        "benchmark/models/prospective-panel.json": "candidate/prospective-model-panel.json",
        "benchmark/judges/prospective-panel.json": "candidate/prospective-judge-panel.json",
        "benchmark/judges/canary-manifest.json": "candidate/judge-canary-manifest.json",
        "benchmark/human-calibration/study-spec.json": "candidate/human-calibration-study-spec.json",
        "benchmark/evidence/snapshots/castillo-2026-empirical-nlp-report.json": (
            "evidence/castillo-2026-empirical-nlp-report.json"
        ),
        "benchmark/evidence/snapshots/castillo-2026-design-coverage.json": (
            "evidence/castillo-2026-design-coverage.json"
        ),
        "benchmark/evidence/snapshots/model-qualification-plan.json": (
            "evidence/model-qualification-plan.json"
        ),
        "benchmark/evidence/snapshots/judge-qualification-plan.json": (
            "evidence/judge-qualification-plan.json"
        ),
        "benchmark/evidence/snapshots/prospective-pilot-plan.json": (
            "evidence/prospective-pilot-plan.json"
        ),
        "benchmark/tasks/v1-pilot-commitment.json": (
            "evidence/historical/v1-pilot-commitment.json"
        ),
        "benchmark/assurance-case.json": "evidence/assurance-case.json",
        "benchmark/integrations/ecosystem-registry.json": "evidence/ecosystem-registry.json",
        "benchmark/ontologies/interoperability-profile.json": "evidence/ontology-interoperability-profile.json",
    }
    for relative in required_paths:
        source = project / relative
        if not source.exists():
            raise FileNotFoundError(source)
        _copy_path(source, output / destination_map[relative])

    source_registry = read_json(project / "data/sources/source-registry.json")
    csl_records = source_registry_to_csl(source_registry)
    # Keep a generic references surface and the exact workspace shape expected by
    # SourceRight. The two files are intentionally identical and are checked below.
    write_json(output / "references/references.csl.json", csl_records)
    write_json(output / ".sourceright/references.csl.json", csl_records)
    plan = default_publication_plan()
    write_json(output / "publication-plan.json", plan.model_dump(mode="json"))

    review_directory = output / "review"
    review_directory.mkdir(parents=True, exist_ok=True)
    (review_directory / "authentext-brief.md").write_text(
        """# Authentext review brief

Review the frozen Substack and arXiv drafts for Dylan Mordaunt's established voice,
clarity, cadence, unnecessary abstraction, and unsupported rhetorical certainty.
Do not disguise AI involvement, add empirical claims, or change prespecified methods.
Return proposed edits as a review artifact rather than modifying the evidence bundle.
""",
        encoding="utf-8",
    )
    (review_directory / "scholarly-review-brief.md").write_text(
        """# Scholarly integrity review brief

Check that the manuscript distinguishes implemented software, fixture verification,
prospective plans, and completed empirical evidence. Confirm that limitations, rights
constraints, human-participant governance, scorer validity, and model-qualification
gates are explicit. Never infer results from plans or fixtures. Record every proposed
claim change with its supporting bundle path.
""",
        encoding="utf-8",
    )

    osf_directory = output / "osf"
    osf_directory.mkdir(parents=True, exist_ok=True)
    write_json(
        osf_directory / "project-metadata.json",
        {
            "schema_version": "1.0.0",
            "title": "PelicanBench: measurement-valid visual generation evaluation",
            "category": "project",
            "description": (
                "Research materials, prespecified pilot design, software release evidence, "
                "and future preregistration artifacts for PelicanBench."
            ),
            "publication_policy": "draft-first; no registration or upload without explicit approval",
            "required_components": [
                "protocol-and-analysis-plan",
                "benchmark-and-scorer-releases",
                "human-calibration-governance",
                "results-and-reproducibility",
            ],
        },
    )

    distribution_directory = output / "distribution"
    distribution_directory.mkdir(parents=True, exist_ok=True)
    write_json(
        distribution_directory / "postiz-post-template.json",
        {
            "schema_version": "pelicanbench.postiz-template.v1",
            "status": "template-only-not-approved-for-write",
            "review_required": True,
            "scheduled_at": "<FUTURE_ISO_8601_TIME>",
            "integrations": ["<POSTIZ_INTEGRATION_ID>"],
            "posts": [
                {
                    "provider": "<PROVIDER_IDENTIFIER>",
                    "post": [
                        {
                            "content": (
                                "PelicanBench turns the pelican-on-a-bicycle prompt into "
                                "a measurement-valid visual benchmark. <PUBLISHED_ARTICLE_URL>"
                            ),
                            "image": ["<OPTIONAL_POSTIZ_UPLOADED_MEDIA_URL>"],
                        }
                    ],
                }
            ],
            "safety": {
                "replace_all_placeholders": True,
                "confirm_target_accounts": True,
                "confirm_future_schedule": True,
                "confirm_public_article_url": True,
                "confirm_media_rights_and_upload": True,
                "automatic_execution_permitted": False,
            },
        },
    )

    copied_artifacts: list[str] = []
    for value in include_artifacts:
        source = Path(value)
        if not source.is_absolute():
            source = project / source
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = output / "evidence" / source.name
        _copy_path(source, destination)
        copied_artifacts.append(destination.relative_to(output).as_posix())

    readme = """# PelicanBench publication bundle

This directory is a rights-aware, content-addressed hand-off to the author's existing
SourceRight, Authentext, scholarly-publishing, Substack, Postiz, OSF, and arXiv tooling.
Bundle generation did not perform any authenticated external write.

Use `publication-plan.json` as the machine-readable action contract. Actions marked
`manual-write` require explicit approval and credentials. External source bodies and
third-party images are not copied into this bundle; only permitted metadata and
repository-authored material are included. `.sourceright/` is a CSL-only workspace,
so SourceRight may correctly report degraded verification coverage until provider
evidence is added.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    pre_manifest_files = sorted(
        path for path in output.rglob("*") if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS"}
    )
    records = tuple(
        PublicationBundleFile(
            path=path.relative_to(output).as_posix(),
            sha256=_sha256(path),
            size_bytes=path.stat().st_size,
        )
        for path in pre_manifest_files
    )
    bundle_hash = content_hash([item.model_dump(mode="json") for item in records])
    manifest = PublicationBundleManifest(
        generated_at=utc_now_iso(),
        project="PelicanBench",
        bundle_hash=bundle_hash,
        files=records,
        external_writes_executed=False,
    )
    write_json(output / "manifest.json", manifest.model_dump(mode="json"))

    checksum_files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    lines = [f"{_sha256(path)}  {path.relative_to(output).as_posix()}" for path in checksum_files]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest
