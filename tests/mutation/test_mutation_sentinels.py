from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.autonomous import ScriptedPolicy, run_autonomous_agent
from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.contracts import load_contract, verify_contract_payload
from pelicanbench.pilot import build_pilot_execution_plan
from pelicanbench.simulation import run_canvas_simulation
from pelicanbench.taskgen import heritage_task

pytestmark = pytest.mark.mutation


def _circle(identifier: str) -> dict[str, object]:
    return {
        "type": "add",
        "id": identifier,
        "element": {"tag": "circle", "attributes": {"cx": 1, "cy": 1, "r": 1}},
    }


def test_kills_canvas_limit_boundary_mutant() -> None:
    canvas = CanvasEnvironment(max_elements=1)
    canvas.step(_circle("one"))
    with pytest.raises(ValueError, match="element limit"):
        canvas.step(_circle("two"))


def test_kills_zero_replicate_mutant() -> None:
    with pytest.raises(ValueError, match="replicates"):
        build_pilot_execution_plan([heritage_task()], [], replicates=0)



def test_kills_empty_task_acceptance_mutant() -> None:
    with pytest.raises(ValueError, match="pilot tasks"):
        build_pilot_execution_plan([], [], replicates=1)

def test_kills_contract_validity_mutant(root: Path) -> None:
    contract = load_contract(root / "benchmark/contracts/human-rating-exchange.json")
    result = verify_contract_payload(contract, "event", {"email": "forbidden@example.org"})
    assert not result.valid
    assert result.errors


def test_kills_zero_seed_rejection_mutant() -> None:
    receipt = run_canvas_simulation([], seed=0)
    assert receipt.seed == 0


def test_kills_zero_budget_acceptance_mutant() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        run_autonomous_agent(ScriptedPolicy([]), max_steps=0)
