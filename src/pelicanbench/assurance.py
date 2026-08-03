"""Evidence-level and release-blocker evaluation for benchmark assurance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

EvidenceLevel = Literal["E0", "E1", "E2", "E3", "E4", "E5"]
EVIDENCE_ORDER: dict[str, int] = {f"E{level}": level for level in range(6)}
OPEN_BLOCKER_STATES = {"planned", "partial", "blocked", "reopened"}


@dataclass(frozen=True, slots=True)
class ClaimResult:
    claim_id: str
    title: str
    evidence_level: str
    required_level: str
    satisfied: bool
    missing_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BlockerResult:
    blocker_id: str
    title: str
    status: str
    blocks_profile: bool
    open_criteria: tuple[str, ...]
    missing_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    profile: str
    ready: bool
    claim_results: tuple[ClaimResult, ...]
    blocker_results: tuple[BlockerResult, ...]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "ready": self.ready,
            "claims": [
                {
                    "claim_id": item.claim_id,
                    "title": item.title,
                    "evidence_level": item.evidence_level,
                    "required_level": item.required_level,
                    "satisfied": item.satisfied,
                    "missing_evidence": list(item.missing_evidence),
                }
                for item in self.claim_results
            ],
            "blockers": [
                {
                    "blocker_id": item.blocker_id,
                    "title": item.title,
                    "status": item.status,
                    "blocks_profile": item.blocks_profile,
                    "open_criteria": list(item.open_criteria),
                    "missing_evidence": list(item.missing_evidence),
                }
                for item in self.blocker_results
            ],
            "errors": list(self.errors),
        }


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _missing_paths(root: Path, values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(value for value in values if not (root / value).exists()))


def evaluate_release_readiness(
    root: str | Path,
    *,
    profile: str,
    assurance_path: str | Path = "benchmark/assurance-case.json",
    blockers_path: str | Path = "conductor/release-blockers.json",
) -> ReadinessReport:
    """Evaluate a release profile against explicit claims and blockers.

    This function intentionally checks evidence existence and declared evidence maturity;
    it does not infer empirical validity from code or test presence.
    """

    project = Path(root)
    assurance = _read_object(project / assurance_path)
    blockers = _read_object(project / blockers_path)
    profiles = assurance.get("release_profiles", {})
    if profile not in profiles:
        raise KeyError(f"unknown release profile: {profile}")
    profile_value = profiles[profile]
    required_claims = set(map(str, profile_value.get("required_claims", ())))
    minimum_level = str(profile_value.get("minimum_evidence_level", "E0"))
    if minimum_level not in EVIDENCE_ORDER:
        raise ValueError(f"unknown evidence level in profile {profile}: {minimum_level}")

    errors: list[str] = []
    claim_results: list[ClaimResult] = []
    claims_by_id = {str(item["id"]): item for item in assurance.get("claims", [])}
    unknown_claims = sorted(required_claims - set(claims_by_id))
    if unknown_claims:
        errors.append("profile references unknown claims: " + ", ".join(unknown_claims))
    for claim_id in sorted(required_claims):
        claim = claims_by_id.get(claim_id)
        if claim is None:
            continue
        level = str(claim.get("evidence_level", "E0"))
        if level not in EVIDENCE_ORDER:
            errors.append(f"claim {claim_id} has unknown evidence level {level}")
            level = "E0"
        missing = _missing_paths(project, list(map(str, claim.get("evidence", ()))))
        status = str(claim.get("status", "planned"))
        satisfied = (
            EVIDENCE_ORDER[level] >= EVIDENCE_ORDER[minimum_level]
            and not missing
            and status not in {"planned", "blocked", "reopened"}
        )
        claim_results.append(
            ClaimResult(
                claim_id=claim_id,
                title=str(claim.get("title", claim_id)),
                evidence_level=level,
                required_level=minimum_level,
                satisfied=satisfied,
                missing_evidence=missing,
            )
        )

    blocker_results: list[BlockerResult] = []
    for blocker in blockers.get("blockers", []):
        blocker_id = str(blocker["id"])
        status = str(blocker.get("status", "planned"))
        applies_to_profile = profile in set(map(str, blocker.get("blocks_profiles", ())))
        criteria = blocker.get("closure_criteria", ())
        criterion_values = [item for item in criteria if isinstance(item, dict)]
        open_criteria = tuple(
            str(item.get("id", "criterion"))
            for item in criterion_values
            if str(item.get("status", "planned")) != "complete"
        )
        evidence = list(map(str, blocker.get("evidence", ())))
        for criterion in criterion_values:
            evidence.extend(map(str, criterion.get("evidence", ())))
        missing = _missing_paths(project, evidence)
        blocker_results.append(
            BlockerResult(
                blocker_id=blocker_id,
                title=str(blocker.get("title", blocker_id)),
                status=status,
                blocks_profile=(
                    applies_to_profile and (status in OPEN_BLOCKER_STATES or bool(open_criteria))
                ),
                open_criteria=open_criteria,
                missing_evidence=missing,
            )
        )

    ready = (
        not errors
        and all(item.satisfied for item in claim_results)
        and not any(item.blocks_profile or item.missing_evidence for item in blocker_results)
    )
    return ReadinessReport(
        profile=profile,
        ready=ready,
        claim_results=tuple(claim_results),
        blocker_results=tuple(blocker_results),
        errors=tuple(errors),
    )
