from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import Mock, patch

import pytest

from pelicanbench.adapters import (
    AdapterGenerationError,
    GenerationResult,
    ModelAdapter,
    OpenAICompatibleAdapter,
    RetryingAdapter,
)
from pelicanbench.taskgen import heritage_task

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload: object, *, status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status
        self.closed = False

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


class _FlakyAdapter(ModelAdapter):
    adapter_id = "fixture-flaky"
    model_id = "fixture/model"
    model_revision = "fixture-r1"

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def generate(self, task, *, seed: int) -> GenerationResult:  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(f"transient-{self.calls}")
        return GenerationResult(
            task_id=task.task_id,
            output="<svg xmlns='http://www.w3.org/2000/svg'></svg>",
            media_type="image/svg+xml",
            raw_response=None,
            metadata={"seed": seed},
        )


def test_openai_adapter_builds_bounded_request_and_closes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = heritage_task()
    svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    response = _Response(
        {
            "choices": [{"message": {"content": svg}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 11},
        }
    )
    monkeypatch.setenv("PB_TEST_TOKEN", "secret")
    adapter = OpenAICompatibleAdapter(
        "https://mock.invalid/v1",
        adapter_id="mocked-openai",
        model_id="fixture/model",
        model_revision="fixture-r1",
        api_key_environment="PB_TEST_TOKEN",
        timeout_seconds=19,
        extra_body={"reasoning": {"effort": "medium"}},
    )

    with patch("pelicanbench.adapters.urllib.request.urlopen", return_value=response) as urlopen:
        result = adapter.generate(task, seed=41)

    request = urlopen.call_args.args[0]
    assert urlopen.call_args.kwargs == {"timeout": 19}
    assert request.full_url == "https://mock.invalid/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret"
    payload = json.loads(request.data)
    assert payload["model"] == "fixture/model"
    assert payload["seed"] == 41
    assert payload["reasoning"] == {"effort": "medium"}
    assert result.output == svg
    assert result.metadata["usage"]["completion_tokens"] == 11
    assert response.closed is True
    assert "secret" not in json.dumps(result.metadata)


def test_openai_adapter_closes_http_error_before_raising() -> None:
    task = heritage_task()
    error = urllib.error.HTTPError(
        "https://mock.invalid/v1/chat/completions",
        429,
        "rate limited",
        {},
        io.BytesIO(b'{"error":{"message":"rate limited"}}'),
    )
    close = Mock(wraps=error.close)
    error.close = close  # type: ignore[method-assign]
    adapter = OpenAICompatibleAdapter(
        "https://mock.invalid/v1",
        adapter_id="mocked-openai",
        model_id="fixture/model",
        model_revision="fixture-r1",
    )

    with (
        patch("pelicanbench.adapters.urllib.request.urlopen", side_effect=error),
        pytest.raises(RuntimeError, match="HTTP 429"),
    ):
        adapter.generate(task, seed=1)

    close.assert_called_once_with()


def test_retrying_adapter_uses_mocked_backoff_and_retains_attempt_history() -> None:
    task = heritage_task()
    inner = _FlakyAdapter(failures=2)
    adapter = RetryingAdapter(inner, max_attempts=3, backoff_seconds=0.25)

    with patch("pelicanbench.adapters.time.sleep") as sleep:
        result = adapter.generate(task, seed=9)

    assert inner.calls == 3
    assert result.metadata["attempts"] == 3
    assert result.metadata["retry_errors"] == [
        "RuntimeError: transient-1",
        "RuntimeError: transient-2",
    ]
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]


def test_retrying_adapter_exhaustion_is_a_typed_failure() -> None:
    task = heritage_task()
    inner = _FlakyAdapter(failures=3)
    adapter = RetryingAdapter(inner, max_attempts=2)

    with pytest.raises(AdapterGenerationError) as captured:
        adapter.generate(task, seed=9)

    assert captured.value.attempts == 2
    assert len(captured.value.errors) == 2
