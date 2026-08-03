from __future__ import annotations

from pathlib import Path

import pytest

from pelicanbench.autonomous import ScriptedPolicy, run_autonomous_agent
from pelicanbench.campaign import CampaignCell, CampaignManifest, lease_ready_cells
from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.coercion import parse_bool
from pelicanbench.contracts import load_contract, verify_contract_payload
from pelicanbench.judge_firewall import evaluate_judge_input
from pelicanbench.render import render_svg
from pelicanbench.pilot import build_pilot_execution_plan
from pelicanbench.simulation import run_canvas_simulation
from pelicanbench.svg import inspect_svg
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

def _campaign_manifest(*, hard_budget: float | None, budget_gate: str) -> CampaignManifest:
    cell = CampaignCell(
        cell_id="PCELL-test",
        stage_id="canary",
        model_id="model-a",
        task_id="task-a",
        replicate=0,
        seed=0,
        state="ready",
        estimated_cost=0.0,
    )
    return CampaignManifest(
        schema_version="1.0.0",
        generated_at="2026-08-02T00:00:00Z",
        campaign_id="PCAMP-test",
        prospective_plan_hash="sha256:" + "1" * 64,
        task_identity_commitment="sha256:" + "2" * 64,
        currency="USD",
        hard_budget=hard_budget,
        max_parallel_per_model=1,
        policy_hash="sha256:" + "3" * 64,
        budget_gate=budget_gate,
        estimated_cost=0.0,
        estimated_cost_with_reserve=0.0,
        unknown_cost_cells=0,
        cells=(cell,),
        shards=(),
    )


def test_kills_campaign_hard_budget_bypass_mutant() -> None:
    manifest = _campaign_manifest(hard_budget=None, budget_gate="pass")
    with pytest.raises(ValueError, match="hard budget required"):
        lease_ready_cells(manifest, worker_id="mutation-worker")


def test_kills_campaign_budget_gate_bypass_mutant() -> None:
    manifest = _campaign_manifest(hard_budget=0.01, budget_gate="blocked-budget-exceeded")
    with pytest.raises(ValueError, match="not executable"):
        lease_ready_cells(manifest, worker_id="mutation-worker")


def test_kills_false_string_truthiness_mutant() -> None:
    assert parse_bool("false", field="qualified") is False


def test_kills_judge_firewall_eligibility_mutant() -> None:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "benchmark/fixtures/adversarial/visible-judge-prompt-injection.svg"
    )
    svg = fixture.read_text(encoding="utf-8")
    inspection = inspect_svg(svg)
    rendered = render_svg(svg, inspection=inspection)
    report = evaluate_judge_input(svg, inspection, rendered)
    assert report.decision == "quarantined"
    assert report.eligible is False
