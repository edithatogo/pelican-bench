"""Provider-neutral model and drawing-application adapter contracts."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .io import content_hash, write_json
from .models import BenchmarkTask


class AdapterGenerationError(RuntimeError):
    """A retry wrapper exhausted its bounded attempts."""

    def __init__(self, message: str, *, attempts: int, errors: tuple[str, ...]) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.errors = errors


@dataclass(frozen=True, slots=True)
class GenerationResult:
    task_id: str
    output: str
    media_type: str
    raw_response: str | None
    metadata: dict[str, Any]


class ModelAdapter(ABC):
    adapter_id: str
    model_id: str
    model_revision: str

    @abstractmethod
    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        raise NotImplementedError


class CallableAdapter(ModelAdapter):
    def __init__(
        self,
        function: Callable[[BenchmarkTask, int], str],
        *,
        adapter_id: str = "callable",
        model_id: str = "fixture/model",
        model_revision: str = "local",
    ) -> None:
        self.function = function
        self.adapter_id = adapter_id
        self.model_id = model_id
        self.model_revision = model_revision

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        output = self.function(task, seed)
        return GenerationResult(task.task_id, output, "image/svg+xml", output, {"seed": seed})


class DirectoryAdapter(ModelAdapter):
    """Read pre-generated outputs by task ID for bridge studies."""

    def __init__(
        self,
        directory: str | Path,
        *,
        adapter_id: str = "directory",
        model_id: str = "archived/model",
        model_revision: str = "unknown",
    ) -> None:
        self.directory = Path(directory)
        self.adapter_id = adapter_id
        self.model_id = model_id
        self.model_revision = model_revision

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        path = self.directory / f"{task.task_id.replace(':', '_')}.svg"
        output = path.read_text(encoding="utf-8")
        return GenerationResult(
            task.task_id,
            output,
            "image/svg+xml",
            None,
            {"source_path": path.as_posix(), "seed": seed},
        )


class CommandAdapter(ModelAdapter):
    """Execute an explicitly configured local command with the prompt on stdin.

    Only an explicit environment allowlist is inherited. This prevents unrelated provider
    credentials and repository secrets from leaking into a child process by default.
    """

    DEFAULT_ENVIRONMENT_ALLOWLIST = (
        "PATH",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SYSTEMROOT",
        "WINDIR",
    )

    def __init__(
        self,
        command: list[str],
        *,
        adapter_id: str,
        model_id: str,
        model_revision: str,
        timeout_seconds: int = 120,
        environment_allowlist: tuple[str, ...] = DEFAULT_ENVIRONMENT_ALLOWLIST,
        extra_environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError("command cannot be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = command
        self.adapter_id = adapter_id
        self.model_id = model_id
        self.model_revision = model_revision
        self.timeout_seconds = timeout_seconds
        self.environment_allowlist = tuple(dict.fromkeys(environment_allowlist))
        self.extra_environment = dict(extra_environment or {})

    def _environment(self, *, seed: int) -> dict[str, str]:
        environment = {
            key: os.environ[key] for key in self.environment_allowlist if key in os.environ
        }
        environment.update(self.extra_environment)
        environment["PELICANBENCH_SEED"] = str(seed)
        return environment

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        completed = subprocess.run(
            self.command,
            input=task.prompt,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
            env=self._environment(seed=seed),
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"adapter command failed with {completed.returncode}: {completed.stderr[-1000:]}"
            )
        return GenerationResult(
            task.task_id,
            completed.stdout,
            "image/svg+xml",
            completed.stdout,
            {"seed": seed, "stderr": completed.stderr[-2000:]},
        )


class OpenAICompatibleAdapter(ModelAdapter):
    """Call a bounded OpenAI-compatible chat-completions endpoint.

    The adapter works with local Ollama, llama.cpp, MLX servers, Hermes gateways, and
    compatible hosted endpoints. Credentials are read only from the explicitly named
    environment variable and are never included in result metadata or raw responses.
    """

    def __init__(
        self,
        base_url: str,
        *,
        adapter_id: str,
        model_id: str,
        model_revision: str,
        timeout_seconds: int = 180,
        api_key_environment: str | None = None,
        system_prompt: str = (
            "Return one complete, self-contained SVG document and no explanatory prose. "
            "Do not embed raster images, scripts, external resources, or hidden text."
        ),
        first_user_prefix: str = "",
        assistant_prefill: str = "",
        temperature: float = 0.0,
        max_tokens: int = 12000,
        stream: bool = False,
        extra_body: Mapping[str, Any] | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use http or https")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if temperature < 0:
            raise ValueError("temperature cannot be negative")
        self.base_url = base_url.rstrip("/")
        self.adapter_id = adapter_id
        self.model_id = model_id
        self.model_revision = model_revision
        self.timeout_seconds = timeout_seconds
        self.api_key_environment = api_key_environment
        self.system_prompt = system_prompt
        self.first_user_prefix = first_user_prefix
        self.assistant_prefill = assistant_prefill
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.extra_body = dict(extra_body or {})

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/v1/chat/completions"

    @staticmethod
    def _message_content(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:  # pyright: ignore[reportUnknownVariableType]
                if isinstance(item, dict):
                    item_dict: dict[str, Any] = cast("dict[str, Any]", item)
                    text = item_dict.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "".join(parts)
        raise RuntimeError("OpenAI-compatible response did not contain textual content")

    @staticmethod
    def _extract_svg(value: str) -> str:
        start = value.find("<svg")
        end = value.rfind("</svg>")
        if start < 0 or end < start:
            raise RuntimeError("model response did not contain a complete SVG document")
        return value[start : end + len("</svg>")]

    def _payload(self, task: BenchmarkTask, *, seed: int) -> dict[str, Any]:
        user_content = f"{self.first_user_prefix}{task.prompt}"
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        if self.assistant_prefill:
            messages.append({"role": "assistant", "content": self.assistant_prefill})
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "seed": seed,
            "stream": self.stream,
        }
        payload.update(self.extra_body)
        return payload

    @classmethod
    def _stream_value(cls, raw: str) -> dict[str, Any]:
        parts: list[str] = []
        usage: dict[str, Any] = {}
        finish_reason: str | None = None
        event_count = 0
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(":"):
                continue
            if not stripped.startswith("data:"):
                continue
            data = stripped[5:].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError as exc:
                raise RuntimeError("invalid OpenAI-compatible streaming response") from exc
            if not isinstance(event, dict):
                raise RuntimeError("invalid OpenAI-compatible streaming response")
            event_dict: dict[str, Any] = cast("dict[str, Any]", event)
            event_count += 1
            event_usage = event_dict.get("usage")
            if isinstance(event_usage, dict):
                usage = cast("dict[str, Any]", event_usage)
            choices = event_dict.get("choices", [])
            if not isinstance(choices, list) or not choices:
                continue
            choice = choices[0]  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(choice, dict):
                continue
            choice_dict: dict[str, Any] = cast("dict[str, Any]", choice)
            reason = choice_dict.get("finish_reason")
            if isinstance(reason, str):
                finish_reason = reason
            delta = choice_dict.get("delta")
            if isinstance(delta, dict):
                delta_dict: dict[str, Any] = cast("dict[str, Any]", delta)
                content = delta_dict.get("content")
                if isinstance(content, str):
                    parts.append(content)
            message = choice_dict.get("message")
            if isinstance(message, dict) and not parts:
                message_dict: dict[str, Any] = cast("dict[str, Any]", message)
                content = message_dict.get("content")
                if isinstance(content, str):
                    parts.append(content)
        if event_count == 0 or not parts:
            raise RuntimeError("OpenAI-compatible stream did not contain textual content")
        return {
            "choices": [
                {
                    "message": {"content": "".join(parts)},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": usage,
            "stream_event_count": event_count,
        }

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        payload = self._payload(task, seed=seed)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key_environment:
            token = os.getenv(self.api_key_environment)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                status = int(getattr(response, "status", 200))
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")[-2000:]
            finally:
                exc.close()
            raise RuntimeError(
                f"OpenAI-compatible endpoint returned HTTP {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible endpoint unavailable: {exc.reason}") from exc
        try:
            value = (
                self._stream_value(raw) if self.stream else cast("dict[str, Any]", json.loads(raw))
            )
            choice = cast("dict[str, Any]", value["choices"][0])
            content = self._message_content(choice["message"]["content"])
        except RuntimeError:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("invalid OpenAI-compatible response structure") from exc
        output = self._extract_svg(content)
        usage = value.get("usage", {})
        finish_reason = choice.get("finish_reason")
        return GenerationResult(
            task_id=task.task_id,
            output=output,
            media_type="image/svg+xml",
            raw_response=content,
            metadata={
                "seed": seed,
                "endpoint": self.endpoint,
                "http_status": status,
                "usage": usage if isinstance(usage, dict) else {},
                "finish_reason": finish_reason,
                "stream": self.stream,
                "stream_event_count": int(value.get("stream_event_count", 0)),
                "prompt_profile": {
                    "first_user_prefix": self.first_user_prefix,
                    "assistant_prefill": self.assistant_prefill,
                },
            },
        )


class RetryingAdapter(ModelAdapter):
    """Retry transient adapter failures while retaining attempt metadata."""

    def __init__(
        self,
        inner: ModelAdapter,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 0.0,
        retryable: tuple[type[Exception], ...] = (TimeoutError, RuntimeError),
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        if not retryable:
            raise ValueError("retryable cannot be empty")
        self.inner = inner
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.retryable = retryable
        self.adapter_id = f"retry:{inner.adapter_id}"
        self.model_id = inner.model_id
        self.model_revision = inner.model_revision

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        errors: list[str] = []
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.inner.generate(task, seed=seed)
            except self.retryable as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                if attempt >= self.max_attempts:
                    raise AdapterGenerationError(
                        f"adapter failed after {attempt} attempts: {errors[-1]}",
                        attempts=attempt,
                        errors=tuple(errors),
                    ) from exc
                if self.backoff_seconds:
                    time.sleep(self.backoff_seconds * attempt)
                continue
            metadata = dict(result.metadata)
            metadata.update(
                {
                    "attempts": attempt,
                    "retry_errors": errors,
                    "inner_adapter_id": self.inner.adapter_id,
                }
            )
            return GenerationResult(
                task_id=result.task_id,
                output=result.output,
                media_type=result.media_type,
                raw_response=result.raw_response,
                metadata=metadata,
            )
        raise AssertionError("retry loop exited unexpectedly")


class CheckpointingAdapter(ModelAdapter):
    """Cache completed model invocations for idempotent resumable benchmark runs."""

    def __init__(self, inner: ModelAdapter, directory: str | Path) -> None:
        self.inner = inner
        self.directory = Path(directory)
        self.adapter_id = f"checkpoint:{inner.adapter_id}"
        self.model_id = inner.model_id
        self.model_revision = inner.model_revision

    def _path(self, task: BenchmarkTask, *, seed: int) -> Path:
        identity = content_hash(
            {
                "task_id": task.task_id,
                "prompt": task.prompt,
                "seed": seed,
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "inner_adapter_id": self.inner.adapter_id,
            }
        ).split(":", 1)[1]
        return self.directory / f"{identity}.json"

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        path = self._path(task, seed=seed)
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            metadata = dict(value.get("metadata", {}))
            metadata.update(
                {
                    "checkpoint_status": "hit",
                    "checkpoint_path": path.as_posix(),
                    "inner_adapter_id": self.inner.adapter_id,
                }
            )
            return GenerationResult(
                task_id=str(value["task_id"]),
                output=str(value["output"]),
                media_type=str(value["media_type"]),
                raw_response=(
                    str(value["raw_response"]) if value.get("raw_response") is not None else None
                ),
                metadata=metadata,
            )
        result = self.inner.generate(task, seed=seed)
        stored = {
            "schema_version": "1.0.0",
            "task_id": result.task_id,
            "output": result.output,
            "media_type": result.media_type,
            "raw_response": result.raw_response,
            "metadata": result.metadata,
        }
        write_json(path, stored)
        metadata = dict(result.metadata)
        metadata.update(
            {
                "checkpoint_status": "miss",
                "checkpoint_path": path.as_posix(),
                "inner_adapter_id": self.inner.adapter_id,
            }
        )
        return GenerationResult(
            task_id=result.task_id,
            output=result.output,
            media_type=result.media_type,
            raw_response=result.raw_response,
            metadata=metadata,
        )
