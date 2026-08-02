from __future__ import annotations

import pytest

from pelicanbench.autonomous import run_autonomous_agent
from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.contracts import ContractDocument, verify_contract_payload
from pelicanbench.simulation import FaultInjection, run_canvas_simulation

pytestmark = pytest.mark.edge


def test_canvas_rejects_active_attribute_values() -> None:
    canvas = CanvasEnvironment()
    with pytest.raises(ValueError, match="active or external"):
        canvas.step(
            {
                "type": "add",
                "id": "unsafe",
                "element": {"tag": "path", "attributes": {"fill": "url(https://example.org/a)"}},
            }
        )


def test_contract_rejects_unknown_surface() -> None:
    contract = ContractDocument(
        contract_id="contract:edge",
        schema_version="1.0.0",
        provider="fixture",
        description="edge",
        request_schema={"type": "object"},
    )
    with pytest.raises(ValueError, match="does not define"):
        verify_contract_payload(contract, "response", {})


def test_negative_simulation_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="seed"):
        run_canvas_simulation([], seed=-1)
    with pytest.raises(ValueError, match="fault index"):
        run_canvas_simulation([], faults=[FaultInjection(-1, {})])


def test_autonomous_protocol_error_propagates() -> None:
    class BrokenPolicy:
        def next_action(self, observation, *, step, previous_error):
            del observation, step, previous_error
            raise RuntimeError("policy failure")

    with pytest.raises(RuntimeError, match="policy failure"):
        run_autonomous_agent(BrokenPolicy())
