"""Deterministic simulation testing for the canonical drawing environment."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .canvas import CanvasEnvironment
from .environments import PelicanCanvasOpenEnv
from .io import content_hash


@dataclass(frozen=True, slots=True)
class SimulationStep:
    index: int
    requested_action: dict[str, Any]
    executed_action: dict[str, Any]
    observation_hash: str
    reward: float
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "requested_action": self.requested_action,
            "executed_action": self.executed_action,
            "observation_hash": self.observation_hash,
            "reward": self.reward,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SimulationReceipt:
    schema_version: str
    seed: int
    steps: tuple[SimulationStep, ...]
    final_state_hash: str
    final_svg_hash: str
    error_count: int
    receipt_hash: str

    def as_dict(self, *, include_receipt_hash: bool = True) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "steps": [step.as_dict() for step in self.steps],
            "final_state_hash": self.final_state_hash,
            "final_svg_hash": self.final_svg_hash,
            "error_count": self.error_count,
        }
        if include_receipt_hash:
            value["receipt_hash"] = self.receipt_hash
        return value


@dataclass(frozen=True, slots=True)
class FaultInjection:
    """A deterministic action replacement at a zero-based simulation index."""

    index: int
    replacement: dict[str, Any]


def run_canvas_simulation(
    actions: Iterable[Mapping[str, Any]],
    *,
    seed: int = 0,
    max_elements: int = 2_000,
    faults: Iterable[FaultInjection] = (),
) -> SimulationReceipt:
    """Replay a bounded action sequence and produce a content-addressed receipt.

    ``seed`` is recorded for experimental identity. The canonical environment itself has
    no hidden randomness, so equal inputs always produce equal receipts.
    """

    if seed < 0:
        raise ValueError("seed cannot be negative")
    if max_elements < 1:
        raise ValueError("max_elements must be positive")
    fault_map: dict[int, dict[str, Any]] = {}
    for fault in faults:
        if fault.index < 0:
            raise ValueError("fault index cannot be negative")
        if fault.index in fault_map:
            raise ValueError(f"duplicate fault index: {fault.index}")
        fault_map[fault.index] = dict(fault.replacement)

    canvas = CanvasEnvironment(max_elements=max_elements)
    environment = PelicanCanvasOpenEnv(canvas)
    environment.reset()
    recorded: list[SimulationStep] = []
    for index, action_value in enumerate(actions):
        requested = dict(action_value)
        executed = dict(fault_map.get(index, requested))
        response = environment.step(executed)
        observation = response["observation"]
        recorded.append(
            SimulationStep(
                index=index,
                requested_action=requested,
                executed_action=executed,
                observation_hash=str(observation["state_hash"]),
                reward=float(response["reward"]),
                error=response.get("error"),
            )
        )

    final_state = environment.state()
    final_svg_hash = content_hash(canvas.to_svg().encode("utf-8"))
    provisional = {
        "schema_version": "1.0.0",
        "seed": seed,
        "steps": [step.as_dict() for step in recorded],
        "final_state_hash": final_state["state_hash"],
        "final_svg_hash": final_svg_hash,
        "error_count": sum(step.error is not None for step in recorded),
    }
    return SimulationReceipt(
        schema_version="1.0.0",
        seed=seed,
        steps=tuple(recorded),
        final_state_hash=str(final_state["state_hash"]),
        final_svg_hash=final_svg_hash,
        error_count=int(provisional["error_count"]),
        receipt_hash=content_hash(provisional),
    )


def assert_deterministic_replay(
    actions: Iterable[Mapping[str, Any]],
    *,
    seed: int = 0,
    faults: Iterable[FaultInjection] = (),
) -> SimulationReceipt:
    """Run the same simulation twice and reject any hidden state or nondeterminism."""

    action_values = tuple(dict(action) for action in actions)
    fault_values = tuple(faults)
    first = run_canvas_simulation(action_values, seed=seed, faults=fault_values)
    second = run_canvas_simulation(action_values, seed=seed, faults=fault_values)
    if first != second:
        raise AssertionError("deterministic simulation replay diverged")
    return first
