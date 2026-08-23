"""Pairwise human-evaluation models and a regularised Bradley-Terry fit."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from math import exp
from pathlib import Path

from .calibration import PairwiseCalibrationTask
from .io import write_json
from .timeutil import utc_now_iso


@dataclass(frozen=True, slots=True)
class PairwiseVote:
    task_id: str
    left_id: str
    right_id: str
    winner: str
    rater_hash: str
    criterion: str = "overall"

    def __post_init__(self) -> None:
        if self.left_id == self.right_id:
            raise ValueError("pairwise alternatives must differ")
        if self.winner not in {self.left_id, self.right_id, "tie"}:
            raise ValueError("winner must be one alternative or tie")


def fit_bradley_terry(
    votes: Iterable[PairwiseVote],
    *,
    iterations: int = 1_000,
    learning_rate: float = 0.05,
    l2: float = 0.01,
) -> dict[str, float]:
    vote_values = list(votes)
    items = sorted({vote.left_id for vote in vote_values} | {vote.right_id for vote in vote_values})
    if len(items) < 2:
        raise ValueError("at least two alternatives are required")
    if iterations < 1 or learning_rate <= 0 or l2 < 0:
        raise ValueError("invalid optimisation settings")
    scores = dict.fromkeys(items, 0.0)
    for _ in range(iterations):
        gradients = {item: -l2 * scores[item] for item in items}
        for vote in vote_values:
            left = scores[vote.left_id]
            right = scores[vote.right_id]
            probability_left = 1.0 / (1.0 + exp(max(-40.0, min(40.0, right - left))))
            observed_left = 0.5 if vote.winner == "tie" else float(vote.winner == vote.left_id)
            error = observed_left - probability_left
            gradients[vote.left_id] += error
            gradients[vote.right_id] -= error
        for item in items:
            scores[item] += learning_rate * gradients[item] / max(1, len(vote_values))
        centre = sum(scores.values()) / len(scores)
        for item in items:
            scores[item] -= centre
    return scores


def probability_superior(left_score: float, right_score: float) -> float:
    return 1.0 / (1.0 + exp(max(-40.0, min(40.0, right_score - left_score))))


# ---- Interoperable human-rating exchange ---------------------------------


@dataclass(frozen=True, slots=True)
class HumanEvaluationBatch:
    schema_version: str
    generated_at: str
    seed: int
    assignments: int
    criteria: tuple[str, ...]
    assignment_sha256: str
    contains_direct_identifiers: bool = False


@dataclass(frozen=True, slots=True)
class AgreementReport:
    items: int
    votes: int
    pairwise_comparisons: int
    observed_agreement: float
    expected_agreement: float
    kappa: float


SENSITIVE_RATING_COLUMNS = {
    "name",
    "email",
    "phone",
    "address",
    "ip",
    "ip_address",
    "user_agent",
    "participant_name",
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def export_pairwise_evaluation_batch(
    pairs: Iterable[PairwiseCalibrationTask],
    output_directory: str | Path,
    *,
    seed: int = 20260801,
) -> HumanEvaluationBatch:
    """Export a privacy-minimised CSV/metadata package for panel collection.

    The package contains artifact identifiers and blinded model aliases only. It has no
    names, emails, IP addresses, free-text notes, or embedded media. A collection platform
    can resolve artifact IDs to signed URLs outside the dataset and return only hashed
    rater IDs plus categorical responses.
    """

    values = sorted(pairs, key=lambda item: (item.pair_id, item.criterion))
    if not values:
        raise ValueError("at least one pairwise task is required")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    assignment_path = output / "assignments.csv"
    columns = [
        "pair_id",
        "task_id",
        "criterion",
        "left_artifact_id",
        "right_artifact_id",
        "left_alias",
        "right_alias",
        "presentation_order_seed",
        "winner",
        "rater_hash",
        "panel",
        "consent_version",
    ]
    with assignment_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for item in values:
            writer.writerow(
                {
                    "pair_id": item.pair_id,
                    "task_id": item.task_id,
                    "criterion": item.criterion,
                    "left_artifact_id": item.left_artifact_id,
                    "right_artifact_id": item.right_artifact_id,
                    "left_alias": "A",
                    "right_alias": "B",
                    "presentation_order_seed": item.presentation_order_seed,
                    "winner": "",
                    "rater_hash": "",
                    "panel": "",
                    "consent_version": "",
                }
            )
    dictionary = {
        "schema_version": "1.0.0",
        "privacy": {
            "direct_identifiers_permitted": False,
            "rater_identifier": "one-way salted hash generated outside PelicanBench",
            "free_text": "not collected in the V1 calibration table",
        },
        "fields": {
            "pair_id": "Stable blinded comparison identifier.",
            "task_id": "Stable benchmark prompt-condition identifier.",
            "criterion": "One prespecified evaluation criterion.",
            "left_artifact_id": "Content-addressed artifact reference presented as A.",
            "right_artifact_id": "Content-addressed artifact reference presented as B.",
            "winner": "A, B, or tie.",
            "rater_hash": "Non-reversible participant pseudonym; no raw account identifier.",
            "panel": "Prespecified sampling panel, such as public, illustrator, ornithology, or bicycle-mechanics.",
            "consent_version": "Version of the approved participant information and consent text.",
        },
        "open_social_data_compatibility": {
            "tabular_exchange": "UTF-8 CSV with stable identifiers",
            "recommended_archive": "Parquet conversion plus this data dictionary and source/provenance metadata",
            "rights": "Human rating release is governed separately from image redistribution rights.",
        },
    }
    write_json(output / "data-dictionary.json", dictionary)
    batch = HumanEvaluationBatch(
        schema_version="1.0.0",
        generated_at=utc_now_iso(),
        seed=seed,
        assignments=len(values),
        criteria=tuple(sorted({item.criterion for item in values})),
        assignment_sha256=_file_sha256(assignment_path),
        contains_direct_identifiers=False,
    )
    write_json(output / "manifest.json", asdict(batch))
    (output / "README.md").write_text(
        "# PelicanBench human-evaluation batch\n\n"
        "The assignments table is blinded and contains no direct participant identifiers. "
        "Return only A, B, or tie, a salted one-way rater hash, the panel code, and the "
        "approved consent version. Do not add names, emails, IP addresses, user agents, or "
        "unstructured participant notes.\n",
        encoding="utf-8",
    )
    return batch


def load_pairwise_votes_csv(path: str | Path) -> list[PairwiseVote]:
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = {str(item).strip().lower() for item in (reader.fieldnames or [])}
        sensitive = sorted(fieldnames & SENSITIVE_RATING_COLUMNS)
        if sensitive:
            raise ValueError("direct identifier columns are prohibited: " + ", ".join(sensitive))
        required = {
            "pair_id",
            "task_id",
            "criterion",
            "left_artifact_id",
            "right_artifact_id",
            "winner",
            "rater_hash",
        }
        missing = sorted(required - fieldnames)
        if missing:
            raise ValueError("missing rating columns: " + ", ".join(missing))
        votes: list[PairwiseVote] = []
        for row_number, row in enumerate(reader, 2):
            left = str(row["left_artifact_id"]).strip()
            right = str(row["right_artifact_id"]).strip()
            raw_winner = str(row["winner"]).strip().lower()
            winner = {"a": left, "left": left, "b": right, "right": right, "tie": "tie"}.get(
                raw_winner
            )
            if winner is None:
                raise ValueError(f"row {row_number}: winner must be A, B, left, right, or tie")
            rater_hash = str(row["rater_hash"]).strip().lower()
            if len(rater_hash) < 16 or any(char not in "0123456789abcdef" for char in rater_hash):
                raise ValueError(
                    f"row {row_number}: rater_hash must be at least 16 hexadecimal characters"
                )
            votes.append(
                PairwiseVote(
                    task_id=str(row["task_id"]).strip(),
                    left_id=left,
                    right_id=right,
                    winner=winner,
                    rater_hash=rater_hash,
                    criterion=str(row["criterion"]).strip(),
                )
            )
    return votes


def inter_rater_agreement(votes: Iterable[PairwiseVote]) -> AgreementReport:
    values = list(votes)
    grouped: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for vote in values:
        category = "tie"
        if vote.winner == vote.left_id:
            category = "left"
        elif vote.winner == vote.right_id:
            category = "right"
        grouped[vote.task_id, vote.left_id, vote.right_id, vote.criterion].append(category)
    comparisons = 0
    agreements = 0
    category_counts: Counter[str] = Counter()
    eligible_items = 0
    for ratings in grouped.values():
        category_counts.update(ratings)
        if len(ratings) < 2:
            continue
        eligible_items += 1
        for index, first in enumerate(ratings):
            for second in ratings[index + 1 :]:
                comparisons += 1
                agreements += int(first == second)
    if comparisons == 0:
        raise ValueError("at least one item requires two or more ratings")
    observed = agreements / comparisons
    total = sum(category_counts.values())
    expected = sum((count / total) ** 2 for count in category_counts.values())
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return AgreementReport(
        items=eligible_items,
        votes=len(values),
        pairwise_comparisons=comparisons,
        observed_agreement=observed,
        expected_agreement=expected,
        kappa=kappa,
    )
