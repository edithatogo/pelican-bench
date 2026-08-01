"""Executable metamorphic and adversarial checks for the normative SVG scorer.

These checks encode invariances that must hold even when an SVG author controls the
source representation.  They are deliberately independent of ordinary unit fixtures so
that CI and releases can emit a machine-readable scorer challenge report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Callable

from .io import content_hash
from .models import BenchmarkTask, ScoreCard
from .render import render_svg
from .scoring import score_svg
from .semantic import SemanticAssessor, StaticSemanticAssessor

_LABEL_ATTRIBUTE = re.compile(r'\s(?:id|class|data-role|aria-label)="[^"]*"')
_LABEL_VALUE = re.compile(r'(\s(?:id|class|data-role|aria-label)=")[^"]*(")')
_SEMANTIC_DIMENSIONS = {
    "animal_anatomy",
    "vehicle_mechanics",
    "interaction",
    "instruction_coverage",
}


@dataclass(frozen=True, slots=True)
class ChallengeCase:
    challenge_id: str
    description: str
    transform: Callable[[str], str]
    require_render_equivalence: bool = True
    require_full_score_equivalence: bool = False
    forbid_aggregate_improvement: bool = True


@dataclass(frozen=True, slots=True)
class ChallengeOutcome:
    challenge_id: str
    passed: bool
    description: str
    baseline_render_hash: str
    transformed_render_hash: str
    baseline_aggregate: float
    transformed_aggregate: float
    render_equivalent: bool
    semantic_dimensions_equal: bool
    full_score_equal: bool
    aggregate_not_improved: bool
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChallengeReport:
    schema_version: str
    scorer_version: str
    task_id: str
    baseline_submission_id: str
    passed: bool
    outcomes: tuple[ChallengeOutcome, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _insert_before_svg_close(svg: str, payload: str) -> str:
    position = svg.rfind("</svg>")
    if position < 0:
        raise ValueError("SVG closing tag not found")
    return svg[:position] + payload + svg[position:]


def strip_source_labels(svg: str) -> str:
    """Remove author-controlled semantic attributes without changing the render."""

    return _LABEL_ATTRIBUTE.sub("", svg)


def rename_source_labels(svg: str) -> str:
    """Replace every author-controlled label with neutral content."""

    counter = 0

    def replacement(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f'{match.group(1)}pb-meta-{counter}{match.group(2)}'

    return _LABEL_VALUE.sub(replacement, svg)


def add_source_comment(svg: str) -> str:
    return _insert_before_svg_close(
        svg,
        "<!-- pelican pouch wing bicycle pedal saddle handlebar riding contact -->\n",
    )


def add_transparent_labelled_shape(svg: str) -> str:
    return _insert_before_svg_close(
        svg,
        '<rect id="pelican-pouch-pedal-rider-contact" data-role="pelican bicycle rider '
        'pouch wing pedal saddle handlebar" x="1" y="1" width="80" height="80" '
        'opacity="0"/>\n',
    )


def add_offcanvas_labelled_shape(svg: str) -> str:
    return _insert_before_svg_close(
        svg,
        '<rect id="pelican-pouch-pedal-rider-contact-offcanvas" data-role="pelican '
        'bicycle rider pouch wing pedal saddle handlebar" x="1000000" y="1000000" '
        'width="80" height="80"/>\n',
    )


def default_challenges() -> tuple[ChallengeCase, ...]:
    return (
        ChallengeCase(
            "META-0001",
            "Stripping IDs, classes and role labels preserves the render and full score.",
            strip_source_labels,
            require_full_score_equivalence=True,
        ),
        ChallengeCase(
            "META-0002",
            "Renaming all source labels preserves the render and full score.",
            rename_source_labels,
            require_full_score_equivalence=True,
        ),
        ChallengeCase(
            "META-0003",
            "Semantic source comments cannot affect the score.",
            add_source_comment,
            require_full_score_equivalence=True,
        ),
        ChallengeCase(
            "META-0004",
            "A transparent labelled shape cannot add semantic credit or improve aggregate score.",
            add_transparent_labelled_shape,
        ),
        ChallengeCase(
            "META-0005",
            "An off-canvas labelled shape cannot add semantic credit or improve aggregate score.",
            add_offcanvas_labelled_shape,
        ),
    )


def _dimension_map(scorecard: ScoreCard) -> dict[str, float]:
    return {item.name: item.value for item in scorecard.dimensions}


def _score(
    task: BenchmarkTask,
    svg: str,
    assessor: SemanticAssessor,
    *,
    submission_label: str,
) -> ScoreCard:
    rendered = render_svg(svg)
    assessment = assessor.assess(task, rendered)
    return score_svg(
        task,
        svg,
        submission_id=f"{submission_label}:{content_hash(svg)}",
        semantic_assessment=assessment,
        rendered=rendered,
    )


def run_scorer_challenges(
    task: BenchmarkTask,
    svg: str,
    *,
    assessor: SemanticAssessor | None = None,
    challenges: tuple[ChallengeCase, ...] | None = None,
) -> ChallengeReport:
    """Execute scorer invariants and return a release-suitable report.

    ``StaticSemanticAssessor`` is used only as a deterministic fixture instrument.  It is
    independently bound to each canonical render and does not inspect source labels.
    Production calibration is a separate E3 requirement.
    """

    selected_assessor = assessor or StaticSemanticAssessor()
    selected_challenges = challenges or default_challenges()
    baseline = _score(task, svg, selected_assessor, submission_label="baseline")
    if not baseline.valid:
        raise ValueError("baseline SVG must pass the fixture scorer before metamorphic checks")
    baseline_dimensions = _dimension_map(baseline)

    outcomes: list[ChallengeOutcome] = []
    for challenge in selected_challenges:
        transformed_svg = challenge.transform(svg)
        transformed = _score(
            task,
            transformed_svg,
            selected_assessor,
            submission_label=challenge.challenge_id,
        )
        transformed_dimensions = _dimension_map(transformed)
        render_equivalent = baseline.render_hash == transformed.render_hash
        semantic_equal = all(
            baseline_dimensions[name] == transformed_dimensions[name]
            for name in _SEMANTIC_DIMENSIONS
        )
        full_score_equal = (
            baseline.aggregate == transformed.aggregate
            and baseline.dimensions == transformed.dimensions
            and baseline.critical_gates == transformed.critical_gates
            and baseline.valid == transformed.valid
        )
        aggregate_not_improved = transformed.aggregate <= baseline.aggregate
        failures: list[str] = []
        if challenge.require_render_equivalence and not render_equivalent:
            failures.append("canonical render changed")
        if not semantic_equal:
            failures.append("semantic dimensions changed")
        if challenge.require_full_score_equivalence and not full_score_equal:
            failures.append("full score changed")
        if challenge.forbid_aggregate_improvement and not aggregate_not_improved:
            failures.append("aggregate score improved")
        outcomes.append(
            ChallengeOutcome(
                challenge_id=challenge.challenge_id,
                passed=not failures,
                description=challenge.description,
                baseline_render_hash=baseline.render_hash or "",
                transformed_render_hash=transformed.render_hash or "",
                baseline_aggregate=baseline.aggregate,
                transformed_aggregate=transformed.aggregate,
                render_equivalent=render_equivalent,
                semantic_dimensions_equal=semantic_equal,
                full_score_equal=full_score_equal,
                aggregate_not_improved=aggregate_not_improved,
                failures=tuple(failures),
            )
        )

    return ChallengeReport(
        schema_version="1.0.0",
        scorer_version=baseline.scorer_version,
        task_id=task.task_id,
        baseline_submission_id=baseline.submission_id,
        passed=all(item.passed for item in outcomes),
        outcomes=tuple(outcomes),
    )
