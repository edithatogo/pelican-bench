"""Bounded autonomous-agent harness for deterministic drawing experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .canvas import CanvasEnvironment
from .environments import PelicanCanvasOpenEnv
from .io import content_hash


class CanvasPolicy(Protocol):
    def next_action(
        self,
        observation: dict[str, Any],
        *,
        step: int,
        previous_error: str | None,
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class AgentEvent:
    step: int
    action: dict[str, Any]
    reward: float
    error: str | None
    state_hash: str


@dataclass(frozen=True, slots=True)
class AutonomousRun:
    terminated: bool
    termination_reason: str
    events: tuple[AgentEvent, ...]
    recovery_count: int
    final_state_hash: str
    final_svg: str
    run_hash: str


class ScriptedPolicy:
    """A deterministic policy used as a reference and agent-harness canary."""

    def __init__(
        self,
        actions: list[dict[str, Any]],
        *,
        recovery_actions: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.actions = tuple(dict(action) for action in actions)
        self.recovery_actions = dict(recovery_actions or {})

    def next_action(
        self,
        observation: dict[str, Any],
        *,
        step: int,
        previous_error: str | None,
    ) -> dict[str, Any] | None:
        del observation
        if previous_error is not None and step in self.recovery_actions:
            return dict(self.recovery_actions[step])
        if step >= len(self.actions):
            return None
        return dict(self.actions[step])


def run_autonomous_agent(
    policy: CanvasPolicy,
    *,
    max_steps: int = 64,
    canvas: CanvasEnvironment | None = None,
) -> AutonomousRun:
    """Execute a policy with explicit stopping, error and resource boundaries."""

    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    drawing = canvas or CanvasEnvironment()
    environment = PelicanCanvasOpenEnv(drawing)
    reset = environment.reset()
    observation = reset["observation"]
    previous_error: str | None = None
    events: list[AgentEvent] = []
    recovery_count = 0
    termination_reason = "step-budget-exhausted"
    terminated = False

    for step in range(max_steps):
        action = policy.next_action(
            observation,
            step=step,
            previous_error=previous_error,
        )
        if action is None:
            termination_reason = "policy-complete"
            terminated = True
            break
        response = environment.step(action)
        observation = response["observation"]
        error = response.get("error")
        if previous_error is not None and error is None:
            recovery_count += 1
        events.append(
            AgentEvent(
                step=step,
                action=dict(action),
                reward=float(response["reward"]),
                error=error,
                state_hash=str(observation["state_hash"]),
            )
        )
        previous_error = error

    final_svg = drawing.to_svg()
    run_payload = {
        "terminated": terminated,
        "termination_reason": termination_reason,
        "events": [
            {
                "step": event.step,
                "action": event.action,
                "reward": event.reward,
                "error": event.error,
                "state_hash": event.state_hash,
            }
            for event in events
        ],
        "recovery_count": recovery_count,
        "final_state_hash": drawing.state()["state_hash"],
        "final_svg_hash": content_hash(final_svg.encode("utf-8")),
    }
    return AutonomousRun(
        terminated=terminated,
        termination_reason=termination_reason,
        events=tuple(events),
        recovery_count=recovery_count,
        final_state_hash=str(drawing.state()["state_hash"]),
        final_svg=final_svg,
        run_hash=content_hash(run_payload),
    )


def reference_pelican_bicycle_actions() -> list[dict[str, Any]]:
    """Return a small editable scene used to test agent plumbing, not visual quality."""

    return [
        {
            "type": "add",
            "id": "rear-wheel",
            "element": {
                "tag": "circle",
                "attributes": {"cx": 170, "cy": 330, "r": 72, "fill": "none", "stroke": "black"},
            },
        },
        {
            "type": "add",
            "id": "front-wheel",
            "element": {
                "tag": "circle",
                "attributes": {"cx": 430, "cy": 330, "r": 72, "fill": "none", "stroke": "black"},
            },
        },
        {
            "type": "add",
            "id": "frame",
            "element": {
                "tag": "path",
                "attributes": {
                    "d": "M170 330 L260 220 L335 330 L170 330 M260 220 L430 330",
                    "fill": "none",
                    "stroke": "black",
                },
            },
        },
        {
            "type": "add",
            "id": "pelican-body",
            "element": {
                "tag": "ellipse",
                "attributes": {"cx": 280, "cy": 170, "rx": 90, "ry": 58, "fill": "white", "stroke": "black"},
            },
        },
        {
            "type": "add",
            "id": "pelican-head",
            "element": {
                "tag": "circle",
                "attributes": {"cx": 375, "cy": 125, "r": 38, "fill": "white", "stroke": "black"},
            },
        },
        {
            "type": "add",
            "id": "pelican-bill",
            "element": {
                "tag": "path",
                "attributes": {"d": "M405 115 L535 130 L405 145 Z", "fill": "orange", "stroke": "black"},
            },
        },
        {"type": "group", "ids": ["rear-wheel", "front-wheel", "frame"], "group": "bicycle"},
        {"type": "group", "ids": ["pelican-body", "pelican-head", "pelican-bill"], "group": "pelican"},
        {"type": "checkpoint", "id": "reference-complete"},
    ]
