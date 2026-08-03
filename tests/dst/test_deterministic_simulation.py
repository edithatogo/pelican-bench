from __future__ import annotations

import pytest

from pelicanbench.simulation import (
    FaultInjection,
    assert_deterministic_replay,
    run_canvas_simulation,
)

pytestmark = pytest.mark.dst

ACTIONS = [
    {
        "type": "add",
        "id": "wheel",
        "element": {"tag": "circle", "attributes": {"cx": 10, "cy": 10, "r": 5}},
    },
    {"type": "checkpoint", "id": "first"},
]


def test_replay_is_byte_deterministic() -> None:
    receipt = assert_deterministic_replay(ACTIONS, seed=17)
    assert receipt.error_count == 0
    assert receipt.receipt_hash.startswith("sha256:")


def test_fault_injection_is_recorded_without_hidden_mutation() -> None:
    fault = FaultInjection(0, {"type": "delete", "id": "missing"})
    first = run_canvas_simulation(ACTIONS, seed=17, faults=[fault])
    second = run_canvas_simulation(ACTIONS, seed=17, faults=[fault])
    assert first == second
    assert first.error_count == 1
    assert first.steps[0].requested_action != first.steps[0].executed_action


def test_duplicate_fault_indices_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate fault"):
        run_canvas_simulation([], faults=[FaultInjection(0, {}), FaultInjection(0, {})])
