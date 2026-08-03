"""Fail-closed preparation of canonical renders for automatic visual judges.

Automatic judges must never receive SVG source, author-controlled labels, or a render
containing evaluator-directed text.  V1 tasks do not require visible text, so any visible
text is quarantined by default.  The policy is explicit and content-addressed so a future
text-bearing benchmark can introduce a separate, validated masking or OCR protocol rather
than silently weakening this gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Literal, Mapping

from .coercion import parse_bool
from .io import content_hash
from .render import RenderedSVG
from .svg import SVGInspection

Decision = Literal["eligible", "quarantined", "rejected"]

_INSTRUCTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore-instructions", re.compile(r"\bignore\b.{0,40}\b(?:instruction|prompt|system)\b", re.I | re.S)),
    ("evaluator-direction", re.compile(r"\b(?:judge|evaluator|scorer|rating)\b", re.I)),
    (
        "answer-direction",
        re.compile(
            r"\b(?:answer|respond|output)\b.{0,24}\b(?:yes|no|true|false|[0-9])\b",
            re.I | re.S,
        ),
    ),
    (
        "score-direction",
        re.compile(
            r"\b(?:give|assign|return|set)\b.{0,24}\b(?:score|rating|probability)\b",
            re.I | re.S,
        ),
    ),
    ("role-direction", re.compile(r"\b(?:system|assistant|developer)\s*:", re.I)),
)


@dataclass(frozen=True, slots=True)
class JudgeFirewallPolicy:
    schema_version: str = "1.0.0"
    allow_visible_text: bool = False
    max_visible_text_characters: int = 0
    quarantine_instruction_like_text: bool = True
    require_safe_source: bool = True
    require_nonblank_render: bool = True

    def __post_init__(self) -> None:
        if self.max_visible_text_characters < 0:
            raise ValueError("max_visible_text_characters cannot be negative")

    @property
    def policy_hash(self) -> str:
        return content_hash(asdict(self))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> JudgeFirewallPolicy:
        return cls(
            schema_version=str(value.get("schema_version", "1.0.0")),
            allow_visible_text=parse_bool(
                value.get("allow_visible_text", False), field="allow_visible_text"
            ),
            max_visible_text_characters=int(value.get("max_visible_text_characters", 0)),
            quarantine_instruction_like_text=parse_bool(
                value.get("quarantine_instruction_like_text", True),
                field="quarantine_instruction_like_text",
            ),
            require_safe_source=parse_bool(
                value.get("require_safe_source", True), field="require_safe_source"
            ),
            require_nonblank_render=parse_bool(
                value.get("require_nonblank_render", True), field="require_nonblank_render"
            ),
        )


@dataclass(frozen=True, slots=True)
class JudgeFirewallReport:
    schema_version: str
    decision: Decision
    eligible: bool
    source_hash: str
    render_hash: str | None
    policy_hash: str
    visible_text_characters: int
    visible_text_elements: int
    instruction_markers: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["instruction_markers"] = list(self.instruction_markers)
        value["reasons"] = list(self.reasons)
        return value


def _instruction_markers(svg: str) -> tuple[str, ...]:
    """Return diagnostic markers without retaining source text in the report."""

    return tuple(name for name, pattern in _INSTRUCTION_PATTERNS if pattern.search(svg))


def evaluate_judge_input(
    svg: str,
    inspection: SVGInspection,
    rendered: RenderedSVG | None,
    *,
    policy: JudgeFirewallPolicy | None = None,
) -> JudgeFirewallReport:
    """Decide whether the canonical render can be sent to an automatic judge.

    The decision is deliberately stricter than source validity.  A safe SVG can still
    contain visible text intended to influence a multimodal evaluator.  Such an artifact
    remains a retained benchmark output, but semantic judging is quarantined and the
    failure remains in the denominator.
    """

    selected = policy or JudgeFirewallPolicy()
    reasons: list[str] = []
    decision: Decision = "eligible"
    text_characters = int(inspection.features.get("text_character_count", 0))
    text_elements = int(inspection.features.get("visible_text_element_count", 0))
    markers = _instruction_markers(svg) if text_characters else ()

    if selected.require_safe_source and not inspection.valid:
        decision = "rejected"
        reasons.append("source-security-gate-failed")
    if selected.require_nonblank_render and (rendered is None or not rendered.nonblank):
        decision = "rejected"
        reasons.append("canonical-render-missing-or-blank")

    if decision != "rejected":
        if not selected.allow_visible_text and text_characters > 0:
            decision = "quarantined"
            reasons.append("visible-text-not-permitted-for-v1-judging")
        elif text_characters > selected.max_visible_text_characters:
            decision = "quarantined"
            reasons.append("visible-text-character-budget-exceeded")
        if selected.quarantine_instruction_like_text and markers:
            decision = "quarantined"
            reasons.append("instruction-like-visible-text-detected")

    return JudgeFirewallReport(
        schema_version="1.0.0",
        decision=decision,
        eligible=decision == "eligible",
        source_hash=content_hash(svg),
        render_hash=rendered.render_hash if rendered is not None else None,
        policy_hash=selected.policy_hash,
        visible_text_characters=text_characters,
        visible_text_elements=text_elements,
        instruction_markers=markers,
        reasons=tuple(dict.fromkeys(reasons)),
    )


__all__ = [
    "JudgeFirewallPolicy",
    "JudgeFirewallReport",
    "evaluate_judge_input",
]
