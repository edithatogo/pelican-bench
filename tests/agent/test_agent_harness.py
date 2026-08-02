from __future__ import annotations

import pytest

from pelicanbench.autonomous import ScriptedPolicy, reference_pelican_bicycle_actions, run_autonomous_agent

pytestmark = pytest.mark.agent


def test_reference_agent_creates_editable_groups_and_checkpoint() -> None:
    result = run_autonomous_agent(ScriptedPolicy(reference_pelican_bicycle_actions()), max_steps=32)
    assert result.terminated
    assert result.termination_reason == "policy-complete"
    assert 'id="bicycle"' in result.final_svg
    assert 'id="pelican"' in result.final_svg
    assert result.run_hash.startswith("sha256:")


def test_agent_failure_is_visible_in_trajectory() -> None:
    actions = [{"type": "delete", "id": "missing"}]
    result = run_autonomous_agent(ScriptedPolicy(actions), max_steps=2)
    assert result.events[0].error is not None
    assert result.events[0].reward < 0
