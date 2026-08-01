"""Provider-neutral model and drawing-application adapter contracts."""

from __future__ import annotations

import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
                    str(value["raw_response"])
                    if value.get("raw_response") is not None
                    else None
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
