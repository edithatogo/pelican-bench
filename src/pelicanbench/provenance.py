"""Interoperable W3C PROV and RO-Crate exports for benchmark runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .models import EvaluationRecord, RunManifest, TrialRecord

PROV_CONTEXT = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "pb": "https://w3id.org/pelicanbench/",
    "id": "@id",
    "type": "@type",
}


def build_prov_jsonld(
    manifest: RunManifest,
    *,
    trials: Iterable[TrialRecord],
    evaluations: Iterable[EvaluationRecord],
) -> dict[str, Any]:
    """Represent the run as entities, activities and agents using PROV-O terms."""

    graph: list[dict[str, Any]] = [
        {
            "id": f"pb:{manifest.run_id}",
            "type": "prov:Activity",
            "prov:startedAtTime": {"@value": manifest.created_at, "@type": "xsd:dateTime"},
            "prov:wasAssociatedWith": [
                {"id": f"pb:model/{manifest.model_id}@{manifest.model_revision}"},
                {"id": "pb:software/pelicanbench"},
            ],
            "pb:benchmarkRelease": manifest.benchmark_release,
            "pb:benchmarkCommit": manifest.benchmark_commit,
            "pb:environmentDigest": manifest.environment_digest,
        },
        {
            "id": f"pb:model/{manifest.model_id}@{manifest.model_revision}",
            "type": "prov:Agent",
            "pb:modelId": manifest.model_id,
            "pb:modelRevision": manifest.model_revision,
        },
        {
            "id": "pb:software/pelicanbench",
            "type": "prov:SoftwareAgent",
            "pb:adapterId": manifest.adapter_id,
        },
    ]
    for trial in trials:
        activity = {
            "id": f"pb:{trial.trial_id}",
            "type": "prov:Activity",
            "prov:wasInformedBy": {"id": f"pb:{manifest.run_id}"},
            "prov:used": {"id": f"pb:task/{trial.task_id}"},
            "pb:seed": trial.seed,
            "pb:status": trial.status,
            "pb:attempts": trial.attempts,
        }
        if trial.error_type is not None:
            activity["pb:errorType"] = trial.error_type
        graph.extend(
            (
                activity,
                {
                    "id": f"pb:task/{trial.task_id}",
                    "type": "prov:Entity",
                    "pb:scenarioId": trial.scenario_id,
                    "pb:promptId": trial.prompt_id,
                    "pb:conditionId": trial.condition_id,
                },
            )
        )
        if trial.artifact_id is not None:
            graph.append(
                {
                    "id": f"pb:artifact/{trial.artifact_id.split(':', 1)[1]}",
                    "type": "prov:Entity",
                    "prov:wasGeneratedBy": {"id": f"pb:{trial.trial_id}"},
                    "pb:sha256": trial.artifact_id,
                }
            )
    for evaluation in evaluations:
        graph.append(
            {
                "id": f"pb:{evaluation.evaluation_id}",
                "type": "prov:Activity",
                "prov:used": [
                    {"id": f"pb:artifact/{evaluation.artifact_id.split(':', 1)[1]}"},
                    {"id": f"pb:scorer/{evaluation.scorer_version}"},
                ],
                "prov:wasInformedBy": {"id": f"pb:{evaluation.trial_id}"},
                "pb:renderHash": evaluation.render_hash,
                "pb:scorecardHash": evaluation.scorecard_hash,
            }
        )
    return {"@context": PROV_CONTEXT, "@graph": graph}


def build_ro_crate(manifest: RunManifest, *, root_name: str = "PelicanBench run") -> dict[str, Any]:
    """Create a minimal RO-Crate 1.1 metadata graph for the run bundle."""

    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": root_name,
            "datePublished": manifest.created_at,
            "identifier": manifest.run_id,
            "version": manifest.benchmark_release,
            "hasPart": [
                {"@id": "run-manifest.json"},
                *({"@id": artifact.path} for artifact in manifest.artifacts),
            ],
        },
        {
            "@id": "run-manifest.json",
            "@type": "File",
            "encodingFormat": "application/json",
            "about": {"@id": "./"},
        },
    ]
    for artifact in manifest.artifacts:
        graph.append(
            {
                "@id": artifact.path,
                "@type": "File",
                "encodingFormat": artifact.media_type,
                "contentSize": artifact.bytes,
                "sha256": artifact.sha256.split(":", 1)[1],
            }
        )
    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": graph,
    }


def reproduction_script(manifest: RunManifest) -> str:
    """Return a portable, non-secret reproduction entry point."""

    return "\n".join(
        (
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# This script verifies the packaged run. It does not invoke a paid provider.",
            'ROOT="$(cd "$(dirname "$0")" && pwd)"',
            'cd "$ROOT"',
            "python - <<'PY'",
            "import hashlib, json, pathlib",
            "root = pathlib.Path('.')",
            "manifest = json.loads((root / 'run-manifest.json').read_text())",
            "for artifact in manifest['artifacts']:",
            "    path = root / artifact['path']",
            "    digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()",
            "    if digest != artifact['sha256']:",
            "        raise SystemExit(f\"hash mismatch: {path}\")",
            f"print('verified {manifest.run_id}')",
            "PY",
            "",
        )
    )
