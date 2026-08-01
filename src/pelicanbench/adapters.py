"""Provider-neutral model and drawing-application adapter contracts."""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import BenchmarkTask


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
    """Execute an explicitly configured local command with the prompt on stdin."""

    def __init__(
        self,
        command: list[str],
        *,
        adapter_id: str,
        model_id: str,
        model_revision: str,
        timeout_seconds: int = 120,
    ) -> None:
        if not command:
            raise ValueError("command cannot be empty")
        self.command = command
        self.adapter_id = adapter_id
        self.model_id = model_id
        self.model_revision = model_revision
        self.timeout_seconds = timeout_seconds

    def generate(self, task: BenchmarkTask, *, seed: int) -> GenerationResult:
        environment = os.environ.copy()
        environment["PELICANBENCH_SEED"] = str(seed)
        completed = subprocess.run(
            self.command,
            input=task.prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_seconds,
            check=False,
            env=environment,
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
