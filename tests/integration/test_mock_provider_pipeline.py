from __future__ import annotations

import json
from pathlib import Path

import pytest

from pelicanbench.adapters import OpenAICompatibleAdapter, RetryingAdapter
from pelicanbench.contracts import load_contract, verify_contract_payload
from pelicanbench.mock_services import (
    MockHTTPResponse,
    ScriptedOpenAIService,
    ScriptedVisualJudge,
    openai_stream_completion,
    openai_svg_completion,
)
from pelicanbench.runner import run_benchmark
from pelicanbench.semantic import EnsembleSemanticAssessor

pytestmark = pytest.mark.integration


def test_retrying_adapter_recovers_from_rate_limit_and_satisfies_contract(
    root: Path, heritage, monkeypatch: pytest.MonkeyPatch
) -> None:
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")
    contract = load_contract(root / "benchmark/contracts/openai-compatible-chat.json")
    with ScriptedOpenAIService(
        [
            MockHTTPResponse(status_code=429, payload={"error": {"message": "rate limited"}}),
            openai_svg_completion(svg),
        ],
        models=("mock/model",),
        required_bearer_token="secret",
    ) as service:
        monkeypatch.setenv("PB_MOCK_TOKEN", "secret")
        adapter = RetryingAdapter(
            OpenAICompatibleAdapter(
                service.base_url,
                adapter_id="mock-openai",
                model_id="mock/model",
                model_revision="fixture-r1",
                api_key_environment="PB_MOCK_TOKEN",
            ),
            max_attempts=2,
        )
        result = adapter.generate(heritage, seed=11)

    assert result.metadata["attempts"] == 2
    posts = [request for request in service.requests if request.method == "POST"]
    assert len(posts) == 2
    assert verify_contract_payload(contract, "request", posts[0].payload).valid
    assert posts[0].headers["Authorization"] == "Bearer secret"
    assert "secret" not in json.dumps(result.metadata)


def test_mock_provider_exercises_malformed_and_exhausted_response_failures(heritage) -> None:
    with ScriptedOpenAIService(
        [MockHTTPResponse(payload="not-json", content_type="application/json")]
    ) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-openai",
            model_id="mock/model",
            model_revision="fixture-r1",
        )
        with pytest.raises(RuntimeError, match="invalid OpenAI-compatible response"):
            adapter.generate(heritage, seed=3)
        with pytest.raises(RuntimeError, match="HTTP 503"):
            adapter.generate(heritage, seed=4)


def test_full_runner_uses_mock_provider_and_mock_judge(
    root: Path, heritage, tmp_path: Path
) -> None:
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")
    with ScriptedOpenAIService([openai_svg_completion(svg)]) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-openai",
            model_id="mock/model",
            model_revision="fixture-r1",
        )
        assessor = EnsembleSemanticAssessor(
            (
                ScriptedVisualJudge(
                    judge_id="mock/judge-a",
                    judge_revision="1",
                    default_probability=0.9,
                ),
                ScriptedVisualJudge(
                    judge_id="mock/judge-b",
                    judge_revision="1",
                    default_probability=0.8,
                ),
            )
        )
        run = run_benchmark(
            [heritage],
            adapter,
            output_directory=tmp_path / "run",
            seed=17,
            benchmark_commit="fixture-commit",
            environment_digest="fixture-env",
            semantic_assessor=assessor,
        )

    assert len(run.trials) == 1
    assert run.trials[0].status == "success"
    assert run.scorecards[0].semantic_assessment_id is not None
    assert run.manifest.configuration["success_count"] == 1
    assert (tmp_path / "run/ro-crate-metadata.json").is_file()


def test_streaming_openai_compatible_response_is_reassembled(root: Path, heritage) -> None:
    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text(encoding="utf-8")
    with ScriptedOpenAIService([openai_stream_completion(svg, chunk_size=19)]) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-streaming-openai",
            model_id="mock/model",
            model_revision="fixture-r1",
            stream=True,
        )
        result = adapter.generate(heritage, seed=29)

    assert result.output == svg.rstrip()
    assert result.metadata["stream"] is True
    assert result.metadata["stream_event_count"] > 2
    payload = next(request.payload for request in service.requests if request.method == "POST")
    assert payload["stream"] is True


def test_streaming_adapter_rejects_malformed_or_empty_event_stream(heritage) -> None:
    malformed = MockHTTPResponse(
        payload="data: {not-json}\n\ndata: [DONE]\n",
        content_type="text/event-stream",
    )
    empty = MockHTTPResponse(
        payload="data: [DONE]\n",
        content_type="text/event-stream",
    )
    with ScriptedOpenAIService([malformed, empty]) as service:
        adapter = OpenAICompatibleAdapter(
            service.base_url,
            adapter_id="mock-streaming-openai",
            model_id="mock/model",
            model_revision="fixture-r1",
            stream=True,
        )
        with pytest.raises(RuntimeError, match="streaming response"):
            adapter.generate(heritage, seed=1)
        with pytest.raises(RuntimeError, match="did not contain textual content"):
            adapter.generate(heritage, seed=2)


def test_streaming_mock_events_satisfy_consumer_contract(root: Path) -> None:
    contract = load_contract(root / "benchmark/contracts/openai-compatible-stream.json")
    response = openai_stream_completion("<svg></svg>", chunk_size=5)
    events = []
    for line in response.body().decode("utf-8").splitlines():
        if not line.startswith("data:"):
            continue
        value = line[5:].strip()
        if value == "[DONE]":
            continue
        events.append(json.loads(value))
    assert events
    assert all(verify_contract_payload(contract, "event", event).valid for event in events)
