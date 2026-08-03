from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.adapters import OpenAICompatibleAdapter, RetryingAdapter
from pelicanbench.campaign import CampaignManifest
from pelicanbench.campaign_store import campaign_store_status, initialise_campaign_store
from pelicanbench.campaign_worker import execute_campaign_batch
from pelicanbench.mock_services import (
    MockHTTPResponse,
    ScriptedOpenAIService,
    openai_svg_completion,
)
from pelicanbench.pilot import load_tasks
from pelicanbench.semantic import StaticSemanticAssessor

pytestmark = pytest.mark.e2e


def _fixture(root: Path) -> tuple[CampaignManifest, list]:
    manifest = CampaignManifest.from_mapping(
        json.loads((root / "benchmark/fixtures/campaign/manifest.json").read_text())
    )
    return manifest, load_tasks(root / "benchmark/fixtures/campaign/tasks.jsonl")


def test_mocked_provider_completes_transactional_campaign_cell(root: Path, tmp_path: Path) -> None:
    manifest, tasks = _fixture(root)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text()
    with ScriptedOpenAIService([openai_svg_completion(svg)], models=("fixture/model",)) as service:
        result = execute_campaign_batch(
            database,
            manifest,
            tasks,
            OpenAICompatibleAdapter(
                service.base_url,
                adapter_id="mock-provider",
                model_id="fixture/model",
                model_revision="fixture-r1",
            ),
            worker_id="mock-worker",
            output_directory=tmp_path / "runs",
            semantic_assessor=StaticSemanticAssessor(),
            now="2026-08-03T00:00:00Z",
        )
    assert result.succeeded == 1
    assert campaign_store_status(database, manifest).complete


def test_mocked_provider_retry_is_retained_without_duplicate_completion(
    root: Path, tmp_path: Path
) -> None:
    manifest, tasks = _fixture(root)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text()
    with ScriptedOpenAIService(
        [
            MockHTTPResponse(status_code=429, payload={"error": {"message": "rate limited"}}),
            openai_svg_completion(svg),
        ],
        models=("fixture/model",),
    ) as service:
        adapter = RetryingAdapter(
            OpenAICompatibleAdapter(
                service.base_url,
                adapter_id="mock-provider",
                model_id="fixture/model",
                model_revision="fixture-r1",
            ),
            max_attempts=2,
        )
        result = execute_campaign_batch(
            database,
            manifest,
            tasks,
            adapter,
            worker_id="mock-worker",
            output_directory=tmp_path / "runs",
            semantic_assessor=StaticSemanticAssessor(),
            now="2026-08-03T00:00:00Z",
        )
    assert result.succeeded == 1
    assert len([request for request in service.requests if request.method == "POST"]) == 2
