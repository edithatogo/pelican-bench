from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pelicanbench.adapters import ModelAdapter, OpenAICompatibleAdapter, RetryingAdapter
from pelicanbench.campaign import CampaignManifest, CampaignPolicy, PriceSchedule, build_campaign_manifest
from pelicanbench.campaign_store import CampaignLedgerStore
from pelicanbench.campaign_worker import CampaignWorker
from pelicanbench.judge_firewall import JudgeFirewallPolicy
from pelicanbench.models import BenchmarkTask
from pelicanbench.mock_services import (
    MockHTTPResponse,
    ScriptedOpenAIService,
    openai_svg_completion,
    openai_text_completion,
)
from pelicanbench.pilot import load_tasks
from pelicanbench.prospective import build_prospective_pilot_plan
from pelicanbench.semantic import StaticSemanticAssessor

pytestmark = pytest.mark.e2e


def _single_cell_campaign(root: Path) -> tuple[CampaignManifest, dict[str, BenchmarkTask], str]:
    tasks = load_tasks(root / "benchmark/tasks/v1-candidate.jsonl")
    panel = json.loads((root / "benchmark/models/prospective-panel.json").read_text())
    commitment = json.loads(
        (root / "benchmark/tasks/v1-candidate-commitment.json").read_text()
    )["commitment"]
    model_id = str(panel["cohorts"][0]["models"][0])
    plan = build_prospective_pilot_plan(
        tasks,
        panel,
        task_identity_commitment=commitment,
        replicates=1,
    )
    manifest = build_campaign_manifest(
        plan,
        qualified_models={model_id: True},
        prices=(PriceSchedule(model_id, "USD", 0.0, 0.0, request_fee=0.001),),
        policy=CampaignPolicy(hard_budget=1.0, reserve_fraction=0.0),
    )
    eligible = next(cell for cell in manifest.cells if cell.state == "ready")
    manifest = replace(
        manifest,
        cells=(eligible,),
        shards=(),
        estimated_cost=eligible.estimated_cost or 0.0,
        estimated_cost_with_reserve=eligible.estimated_cost or 0.0,
    )
    return manifest, {task.task_id: task for task in tasks}, model_id


def _worker(
    *,
    manifest: CampaignManifest,
    tasks: dict[str, BenchmarkTask],
    adapters: dict[str, ModelAdapter],
    tmp_path: Path,
    judge_policy: JudgeFirewallPolicy | None = None,
) -> CampaignWorker:
    return CampaignWorker(
        manifest=manifest,
        ledger=CampaignLedgerStore(tmp_path / "campaign-events.jsonl"),
        tasks=tasks,
        adapters=adapters,
        output_root=tmp_path / "runs",
        benchmark_commit="fixture-commit",
        environment_digest="fixture-env",
        semantic_assessor=StaticSemanticAssessor(default=1.0),
        judge_policy=judge_policy,
    )


def test_mocked_provider_completes_one_owned_campaign_cell(root: Path, tmp_path: Path) -> None:
    manifest, tasks, model_id = _single_cell_campaign(root)
    eligible = manifest.cells[0]
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")

    with ScriptedOpenAIService([openai_svg_completion(svg)], models=(model_id,)) as service:
        worker = _worker(
            manifest=manifest,
            tasks=tasks,
            adapters={
                model_id: OpenAICompatibleAdapter(
                    service.base_url,
                    adapter_id="mock-campaign-provider",
                    model_id=model_id,
                    model_revision="fixture-r1",
                )
            },
            tmp_path=tmp_path,
        )
        batch = worker.run_once(
            worker_id="mock-worker",
            limit=1,
            now=datetime(2026, 8, 3, tzinfo=UTC),
        )

    assert batch.leased_cell_ids == (eligible.cell_id,)
    assert batch.outcomes[0].state == "succeeded"
    assert batch.outcomes[0].artifact_id is not None
    assert batch.ledger_head.event_count == 2
    assert Path(batch.outcomes[0].run_directory, "run-manifest.json").is_file()


def test_mocked_campaign_retries_rate_limit_and_commits_once(root: Path, tmp_path: Path) -> None:
    manifest, tasks, model_id = _single_cell_campaign(root)
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")
    with ScriptedOpenAIService(
        [
            MockHTTPResponse(status_code=429, payload={"error": {"message": "rate limited"}}),
            openai_svg_completion(svg),
        ],
        models=(model_id,),
    ) as service:
        adapter = RetryingAdapter(
            OpenAICompatibleAdapter(
                service.base_url,
                adapter_id="mock-campaign-provider",
                model_id=model_id,
                model_revision="fixture-r1",
            ),
            max_attempts=2,
        )
        batch = _worker(
            manifest=manifest,
            tasks=tasks,
            adapters={model_id: adapter},
            tmp_path=tmp_path,
        ).run_once(worker_id="mock-worker", now=datetime(2026, 8, 3, tzinfo=UTC))

    assert batch.outcomes[0].state == "succeeded"
    assert len([request for request in service.requests if request.method == "POST"]) == 2
    assert batch.ledger_head.event_count == 2


def test_mocked_campaign_retains_missing_adapter_as_terminal_failure(
    root: Path, tmp_path: Path
) -> None:
    manifest, tasks, _model_id = _single_cell_campaign(root)
    batch = _worker(
        manifest=manifest,
        tasks=tasks,
        adapters={},
        tmp_path=tmp_path,
    ).run_once(worker_id="mock-worker", now=datetime(2026, 8, 3, tzinfo=UTC))

    assert batch.outcomes[0].state == "failed"
    assert batch.outcomes[0].error_type == "KeyError"
    assert "adapter" in str(batch.outcomes[0].error_message)
    assert batch.ledger_head.event_count == 2


def test_mocked_campaign_retains_malformed_provider_output(root: Path, tmp_path: Path) -> None:
    manifest, tasks, model_id = _single_cell_campaign(root)
    with ScriptedOpenAIService([openai_text_completion("not an svg")], models=(model_id,)) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-campaign-provider",
            model_id=model_id,
            model_revision="fixture-r1",
        )
        batch = _worker(
            manifest=manifest,
            tasks=tasks,
            adapters={model_id: adapter},
            tmp_path=tmp_path,
        ).run_once(worker_id="mock-worker", now=datetime(2026, 8, 3, tzinfo=UTC))

    assert batch.outcomes[0].state == "failed"
    assert batch.outcomes[0].artifact_id is None
    assert batch.ledger_head.event_count == 2


def test_mocked_campaign_quarantines_invalid_rendered_artifact(root: Path, tmp_path: Path) -> None:
    manifest, tasks, model_id = _single_cell_campaign(root)
    svg = (
        root / "benchmark/fixtures/adversarial/visible-judge-prompt-injection.svg"
    ).read_text(encoding="utf-8")
    with ScriptedOpenAIService([openai_svg_completion(svg)], models=(model_id,)) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-campaign-provider",
            model_id=model_id,
            model_revision="fixture-r1",
        )
        batch = _worker(
            manifest=manifest,
            tasks=tasks,
            adapters={model_id: adapter},
            tmp_path=tmp_path,
            judge_policy=JudgeFirewallPolicy(),
        ).run_once(worker_id="mock-worker", now=datetime(2026, 8, 3, tzinfo=UTC))

    assert batch.outcomes[0].state == "quarantined"
    assert batch.outcomes[0].artifact_id is not None
    assert batch.outcomes[0].error_type == "InvalidScorecard"
    assert batch.ledger_head.event_count == 2
