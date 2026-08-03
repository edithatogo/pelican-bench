"""Deterministic mock providers and judges for adapter and campaign verification.

These utilities are deliberately fixture-only. They exercise the same HTTP and visual-judge
interfaces used by real providers while making retries, malformed responses, authentication,
latency and schema failures reproducible without network credentials.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

from .semantic import AtomicQuestion, JudgeAnswer


@dataclass(frozen=True, slots=True)
class MockHTTPResponse:
    """One scripted HTTP response emitted by a mock OpenAI-compatible service."""

    status_code: int = 200
    payload: object = None
    content_type: str = "application/json"
    delay_seconds: float = 0.0
    headers: tuple[tuple[str, str], ...] = ()
    close_connection: bool = False

    def __post_init__(self) -> None:
        if not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be a valid HTTP response code")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative")

    def body(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        if isinstance(self.payload, str):
            return self.payload.encode("utf-8")
        return json.dumps(self.payload, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True, slots=True)
class MockHTTPRequest:
    sequence: int
    method: str
    path: str
    headers: dict[str, str]
    payload: object

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def openai_svg_completion(
    svg: str,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    finish_reason: str = "stop",
    prefix: str = "",
) -> MockHTTPResponse:
    """Build a valid non-streaming OpenAI-compatible SVG completion response."""

    return MockHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {"content": f"{prefix}{svg}"},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
    )


def openai_stream_completion(
    text: str,
    *,
    chunk_size: int = 32,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MockHTTPResponse:
    """Build a deterministic OpenAI-compatible server-sent-event response."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    chunks = [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
    lines = [
        "data: "
        + json.dumps(
            {
                "choices": [
                    {
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }
                ]
            },
            separators=(",", ":"),
        )
        for chunk in chunks
    ]
    lines.append(
        "data: "
        + json.dumps(
            {
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            },
            separators=(",", ":"),
        )
    )
    lines.extend(("data: [DONE]", ""))
    return MockHTTPResponse(
        payload="\n\n".join(lines),
        content_type="text/event-stream",
    )


def openai_text_completion(
    text: str,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MockHTTPResponse:
    return MockHTTPResponse(
        payload={
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
    )


class _MockHTTPServer(HTTPServer):
    """Single-request-at-a-time server with deterministic socket ownership."""

    allow_reuse_address = True


class ScriptedOpenAIService:
    """Thread-safe local server with a deterministic response queue.

    ``GET /v1/models`` returns the configured catalogue. Each
    ``POST /v1/chat/completions`` consumes exactly one scripted response. Requests are
    retained for contract assertions. The server is intended for tests and local harness
    fixtures only; it is not a production inference gateway.
    """

    def __init__(
        self,
        responses: Iterable[MockHTTPResponse],
        *,
        models: Iterable[str] = ("mock/model",),
        required_bearer_token: str | None = None,
    ) -> None:
        self._responses = deque(responses)
        self._models = tuple(dict.fromkeys(str(model) for model in models))
        if not self._models:
            raise ValueError("at least one mock model is required")
        self.required_bearer_token = required_bearer_token
        self._requests: list[MockHTTPRequest] = []
        self._lock = threading.Lock()
        self._server: _MockHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("mock service has not been started")
        host, port = self._server.server_address[:2]
        return f"http://{host!s}:{port}"

    @property
    def requests(self) -> tuple[MockHTTPRequest, ...]:
        with self._lock:
            return tuple(self._requests)

    @property
    def remaining_responses(self) -> int:
        with self._lock:
            return len(self._responses)

    def _record(
        self, *, method: str, path: str, headers: Mapping[str, str], payload: object
    ) -> None:
        with self._lock:
            self._requests.append(
                MockHTTPRequest(
                    sequence=len(self._requests),
                    method=method,
                    path=path,
                    headers={str(key): str(value) for key, value in headers.items()},
                    payload=payload,
                )
            )

    def _next_response(self) -> MockHTTPResponse:
        with self._lock:
            if not self._responses:
                return MockHTTPResponse(
                    status_code=503,
                    payload={"error": {"message": "mock response queue exhausted"}},
                )
            return self._responses.popleft()

    def start(self) -> ScriptedOpenAIService:
        if self._server is not None:
            raise RuntimeError("mock service is already running")
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def _write(self, response: MockHTTPResponse) -> None:
                if response.delay_seconds:
                    time.sleep(response.delay_seconds)
                if response.close_connection:
                    self.close_connection = True
                    return
                body = response.body()
                self.send_response(response.status_code)
                self.send_header("Content-Type", response.content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                for name, value in response.headers:
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                self.close_connection = True

            def do_GET(self) -> None:
                owner._record(
                    method="GET",
                    path=self.path,
                    headers=dict(self.headers.items()),
                    payload=None,
                )
                if self.path.rstrip("/") != "/v1/models":
                    self._write(MockHTTPResponse(status_code=404, payload={"error": "not found"}))
                    return
                self._write(
                    MockHTTPResponse(
                        payload={
                            "object": "list",
                            "data": [
                                {"id": model, "object": "model", "owned_by": "pelicanbench-mock"}
                                for model in owner._models
                            ],
                        }
                    )
                )

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    payload: object = json.loads(raw) if raw else None
                except json.JSONDecodeError:
                    payload = raw.decode("utf-8", errors="replace")
                owner._record(
                    method="POST",
                    path=self.path,
                    headers=dict(self.headers.items()),
                    payload=payload,
                )
                if self.path.rstrip("/") != "/v1/chat/completions":
                    self._write(MockHTTPResponse(status_code=404, payload={"error": "not found"}))
                    return
                if owner.required_bearer_token is not None:
                    expected = f"Bearer {owner.required_bearer_token}"
                    if self.headers.get("Authorization") != expected:
                        self._write(
                            MockHTTPResponse(
                                status_code=401,
                                payload={"error": {"message": "missing or invalid bearer token"}},
                            )
                        )
                        return
                self._write(owner._next_response())

            def log_message(self, _format: str, *args: object) -> None:
                del args

        self._server = _MockHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        if server is None:
            return
        server.shutdown()
        if thread is not None:
            thread.join(timeout=5)
        server.server_close()
        self._server = None
        self._thread = None

    def __enter__(self) -> ScriptedOpenAIService:
        return self.start()

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.stop()


class ScriptedVisualJudge:
    """Deterministic source-independent visual judge for ensemble and failure tests."""

    def __init__(
        self,
        *,
        judge_id: str,
        judge_revision: str,
        probabilities: Mapping[str, float] | None = None,
        default_probability: float = 1.0,
        fail_questions: Iterable[str] = (),
        mismatched_identity: bool = False,
    ) -> None:
        if not judge_id.strip() or not judge_revision.strip():
            raise ValueError("judge identity and revision are required")
        if not 0.0 <= default_probability <= 1.0:
            raise ValueError("default_probability must be within [0,1]")
        self.judge_id = judge_id
        self.judge_revision = judge_revision
        self._probabilities = dict(probabilities or {})
        self._default = default_probability
        self._fail_questions = frozenset(fail_questions)
        self._mismatched_identity = mismatched_identity
        self.calls: list[tuple[str, int]] = []

    def answer(self, *, image: bytes, question: AtomicQuestion) -> JudgeAnswer:
        self.calls.append((question.question_id, len(image)))
        if question.question_id in self._fail_questions:
            raise RuntimeError(f"scripted judge failure for {question.question_id}")
        return JudgeAnswer(
            question_id=question.question_id,
            probability_yes=self._probabilities.get(question.question_id, self._default),
            rationale="deterministic mock judge response; not empirical evidence",
            judge_id=("wrong/judge" if self._mismatched_identity else self.judge_id),
            judge_revision=self.judge_revision,
        )


__all__ = [
    "MockHTTPRequest",
    "MockHTTPResponse",
    "ScriptedOpenAIService",
    "ScriptedVisualJudge",
    "openai_stream_completion",
    "openai_svg_completion",
    "openai_text_completion",
]
