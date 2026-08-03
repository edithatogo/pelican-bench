"""Forward-compatible contracts for animation, video, 3D, and cross-application transfer."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True, slots=True)
class FrameObservation:
    frame_index: int
    identity_score: float
    relation_score: float
    mechanical_score: float

    def __post_init__(self) -> None:
        for value in (self.identity_score, self.relation_score, self.mechanical_score):
            if not 0 <= value <= 1:
                raise ValueError("frame scores must be within [0,1]")


@dataclass(frozen=True, slots=True)
class SequenceScore:
    frames: int
    identity_consistency: float
    relation_consistency: float
    mechanical_consistency: float
    worst_frame: float


def score_sequence(frames: Iterable[FrameObservation]) -> SequenceScore:
    values = sorted(frames, key=lambda item: item.frame_index)
    if not values:
        raise ValueError("at least one frame is required")
    per_frame = [
        mean((item.identity_score, item.relation_score, item.mechanical_score)) for item in values
    ]
    return SequenceScore(
        frames=len(values),
        identity_consistency=mean(item.identity_score for item in values),
        relation_consistency=mean(item.relation_score for item in values),
        mechanical_consistency=mean(item.mechanical_score for item in values),
        worst_frame=min(per_frame),
    )
