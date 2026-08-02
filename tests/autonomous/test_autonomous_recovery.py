from __future__ import annotations

import pytest

from pelicanbench.autonomous import ScriptedPolicy, run_autonomous_agent

pytestmark = pytest.mark.autonomous


def test_bounded_policy_recovers_after_failed_action() -> None:
    policy = ScriptedPolicy(
        [{"type": "delete", "id": "missing"}, {"type": "delete", "id": "still-missing"}],
        recovery_actions={
            1: {
                "type": "add",
                "id": "recovered",
                "element": {"tag": "circle", "attributes": {"cx": 2, "cy": 2, "r": 1}},
            }
        },
    )
    result = run_autonomous_agent(policy, max_steps=3)
    assert result.terminated
    assert result.recovery_count == 1
    assert "recovered" in result.final_svg


def test_step_budget_exhaustion_is_explicit() -> None:
    policy = ScriptedPolicy(
        [
            {"type": "checkpoint", "id": "a"},
            {"type": "checkpoint", "id": "b"},
        ]
    )
    result = run_autonomous_agent(policy, max_steps=1)
    assert not result.terminated
    assert result.termination_reason == "step-budget-exhausted"
