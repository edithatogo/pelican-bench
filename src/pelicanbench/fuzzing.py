"""Bounded deterministic mutation-fuzz smoke tests for untrusted SVGs."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable

from .render import SVGRenderError, render_svg
from .svg import inspect_svg

Mutation = Callable[[str, random.Random], str]


@dataclass(frozen=True, slots=True)
class FuzzFailure:
    case_index: int
    mutation: str
    error_type: str
    message: str
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class FuzzReport:
    schema_version: str
    seed: int
    cases: int
    accepted: int
    rejected: int
    rendered: int
    render_rejected: int
    maximum_elapsed_ms: float
    budget_ms: float
    failures: tuple[FuzzFailure, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "cases": self.cases,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "rendered": self.rendered,
            "render_rejected": self.render_rejected,
            "maximum_elapsed_ms": self.maximum_elapsed_ms,
            "budget_ms": self.budget_ms,
            "passed": self.passed,
            "failures": [
                {
                    "case_index": item.case_index,
                    "mutation": item.mutation,
                    "error_type": item.error_type,
                    "message": item.message,
                    "elapsed_ms": item.elapsed_ms,
                }
                for item in self.failures
            ],
        }


def _before_close(svg: str, addition: str) -> str:
    marker = "</svg>"
    position = svg.rfind(marker)
    if position < 0:
        return svg + addition
    return svg[:position] + addition + svg[position:]


def _event_handler(svg: str, _: random.Random) -> str:
    return svg.replace("<svg", '<svg onload="alert(1)"', 1)


def _external_image(svg: str, rng: random.Random) -> str:
    return _before_close(
        svg,
        f'<image x="{rng.randint(0, 100)}" y="0" href="https://example.invalid/x.png"/>',
    )


def _external_css(svg: str, _: random.Random) -> str:
    return _before_close(svg, '<style>.x{fill:url(https://example.invalid/a)}</style>')


def _entity(svg: str, _: random.Random) -> str:
    return '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>' + svg.replace(
        "</svg>", "&xxe;</svg>", 1
    )


def _nested_groups(svg: str, rng: random.Random) -> str:
    depth = rng.randint(1, 48)
    content = '<circle cx="1" cy="1" r="1"/>'
    for index in range(depth):
        content = f'<g transform="translate({index % 3} {index % 5})">{content}</g>'
    return _before_close(svg, content)


def _path_burst(svg: str, rng: random.Random) -> str:
    segments = rng.randint(1, 1600)
    path = "M0 0 " + " ".join(f"L{i % 640} {(i * 7) % 480}" for i in range(segments))
    return _before_close(svg, f'<path d="{path}" fill="none" stroke="black"/>')


def _transparent_labels(svg: str, rng: random.Random) -> str:
    return _before_close(
        svg,
        (
            f'<rect id="pelican-pouch-pedal-{rng.randrange(1_000_000)}" '
            'x="0" y="0" width="100" height="100" opacity="0"/>'
        ),
    )


def _off_canvas(svg: str, rng: random.Random) -> str:
    coordinate = rng.randint(10_000, 100_000)
    return _before_close(
        svg,
        f'<circle id="wheel" cx="{coordinate}" cy="{coordinate}" r="500"/>',
    )


def _duplicate_ids(svg: str, rng: random.Random) -> str:
    identifier = f"duplicate-{rng.randint(0, 4)}"
    return _before_close(
        svg,
        f'<circle id="{identifier}" cx="20" cy="20" r="4"/>'
        f'<rect id="{identifier}" x="30" y="30" width="4" height="4"/>',
    )


def _transform_extremes(svg: str, rng: random.Random) -> str:
    scale = rng.choice((0, 1e-9, 1e6, -1, 3.14159))
    rotate = rng.randint(-100_000, 100_000)
    return _before_close(
        svg,
        f'<g transform="scale({scale}) rotate({rotate})"><path d="M0 0 L1 1"/></g>',
    )


def _clip_mask(svg: str, rng: random.Random) -> str:
    identifier = f"clip-{rng.randrange(1_000_000)}"
    return _before_close(
        svg,
        (
            f'<defs><clipPath id="{identifier}"><circle cx="20" cy="20" r="10"/>'
            f'</clipPath></defs><rect x="0" y="0" width="40" height="40" '
            f'clip-path="url(#{identifier})"/>'
        ),
    )


def _truncate(svg: str, rng: random.Random) -> str:
    if not svg:
        return svg
    return svg[: rng.randrange(0, len(svg))]


def _comment_burst(svg: str, rng: random.Random) -> str:
    words = "pelican bicycle pouch pedal saddle handlebar " * rng.randint(1, 100)
    return _before_close(svg, f"<!-- {words} -->")


DEFAULT_MUTATIONS: tuple[tuple[str, Mutation], ...] = (
    ("event-handler", _event_handler),
    ("external-image", _external_image),
    ("external-css", _external_css),
    ("entity", _entity),
    ("nested-groups", _nested_groups),
    ("path-burst", _path_burst),
    ("transparent-labels", _transparent_labels),
    ("off-canvas", _off_canvas),
    ("duplicate-ids", _duplicate_ids),
    ("transform-extremes", _transform_extremes),
    ("clip-mask", _clip_mask),
    ("truncate", _truncate),
    ("comment-burst", _comment_burst),
)


def run_svg_fuzz_campaign(
    baseline_svg: str,
    *,
    cases: int = 100,
    seed: int = 20260801,
    budget_ms: float = 1000.0,
    mutations: tuple[tuple[str, Mutation], ...] = DEFAULT_MUTATIONS,
) -> FuzzReport:
    if cases < 1:
        raise ValueError("cases must be positive")
    if budget_ms <= 0:
        raise ValueError("budget_ms must be positive")
    if not mutations:
        raise ValueError("at least one mutation is required")
    rng = random.Random(seed)
    accepted = 0
    rejected = 0
    rendered = 0
    render_rejected = 0
    maximum_elapsed = 0.0
    failures: list[FuzzFailure] = []
    for index in range(cases):
        mutation_name, mutation = mutations[index % len(mutations)]
        case_rng = random.Random(rng.getrandbits(64))
        start = time.perf_counter()
        try:
            candidate = mutation(baseline_svg, case_rng)
            inspection = inspect_svg(candidate)
            if inspection.valid:
                accepted += 1
                try:
                    render_svg(candidate, inspection=inspection, size=128)
                except SVGRenderError:
                    render_rejected += 1
                else:
                    rendered += 1
            else:
                rejected += 1
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            failures.append(
                FuzzFailure(
                    case_index=index,
                    mutation=mutation_name,
                    error_type=type(exc).__name__,
                    message=str(exc)[-1000:],
                    elapsed_ms=elapsed,
                )
            )
            maximum_elapsed = max(maximum_elapsed, elapsed)
            continue
        elapsed = (time.perf_counter() - start) * 1000
        maximum_elapsed = max(maximum_elapsed, elapsed)
        if elapsed > budget_ms:
            failures.append(
                FuzzFailure(
                    case_index=index,
                    mutation=mutation_name,
                    error_type="ResourceBudgetExceeded",
                    message=f"case exceeded {budget_ms:.1f} ms budget",
                    elapsed_ms=elapsed,
                )
            )
    return FuzzReport(
        schema_version="1.0.0",
        seed=seed,
        cases=cases,
        accepted=accepted,
        rejected=rejected,
        rendered=rendered,
        render_rejected=render_rejected,
        maximum_elapsed_ms=maximum_elapsed,
        budget_ms=budget_ms,
        failures=tuple(failures),
    )
