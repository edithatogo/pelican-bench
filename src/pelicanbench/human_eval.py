"""Pairwise human-evaluation models and a regularised Bradley-Terry fit."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable


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
    scores = {item: 0.0 for item in items}
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
