"""Transactional worker execution for prospective campaign cells.

A campaign manifest and :mod:`pelicanbench.campaign_store` describe which model-task
trials are permitted to run.  This module closes the remaining execution gap: it atomically
leases cells, executes them through the ordinary benchmark runner, retains every output or
failure, and commits the terminal state and cost back to the store.

The worker is deliberately batch-bounded.  A supervisor can invoke it repeatedly or run
multiple workers against the same SQLite store; the store remains the authority for lease,
budget, and state transitions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable, Iterable, Mapping

from .adapters import ModelAdapter
from .campaign import CampaignManifest
from .campaign_store import (
    StoreEvent,
    StoreLease,
    StoreTerminalState,
    complete_campaign_lease,
    heartbeat_campaign_lease,
    lease_campaign_cells,
    read_store_events,
    reconcile_campaign_store,
)
from .io import content_hash, read_json, write_json, write_jsonl
from .judge_firewall import JudgeFirewallPolicy
from .models import BenchmarkTask
from .runner import RunResult, run_benchmark
from .semantic import SemanticAssessor


@dataclass(frozen=True, slots=True)
class CampaignCellExecution:
    schema_version: str
    campaign_id: str
    cell_id: str
    worker_id: str
    lease_token: str
    model_id: str
    model_revision: str
    adapter_id: str
    task_id: str
    replicate: int
    seed: int
    terminal_state: StoreTerminalState
    terminal_reason: str
    charged_cost: float
    cost_basis: str
    artifact_id: str | None
    run_id: str | None
    scorecard_hash: str | None
    output_directory: str
    error_type: str | None
    error_message: str | None
    heartbeat_count: int
    heartbeat_error: str | None
    attempt: int
    record_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CampaignExecutionReconciliation:
    schema_version: str
    campaign_id: str
    valid: bool
    terminal_events: int
    execution_records: int
    matched_records: int
    errors: tuple[str, ...]
    reconciliation_hash: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["errors"] = list(self.errors)
        return value


@dataclass(frozen=True, slots=True)
class CampaignWorkerResult:
    schema_version: str
    campaign_id: str
    worker_id: str
    model_id: str
    leased_cells: int
    succeeded: int
    quarantined: int
    failed: int
    charged_cost: float
    heartbeat_count: int
    heartbeat_failures: int
    records: tuple[CampaignCellExecution, ...]
    batch_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_identifier(value: str) -> str:
    candidate = "".join(
        character if character.isalnum() or character in "-_." else "_"
        for character in value
    )
    return candidate or "cell"


@dataclass(frozen=True, slots=True)
class _HeartbeatResult:
    count: int
    error: str | None


class _LeaseHeartbeat:
    """Renew one lease in a daemon thread while a blocking adapter executes."""

    def __init__(
        self,
        database: str | Path,
        manifest: CampaignManifest,
        lease: StoreLease,
        *,
        interval_seconds: float,
        extend_seconds: int,
    ) -> None:
        self._database = database
        self._manifest = manifest
        self._lease = lease
        self._interval_seconds = interval_seconds
        self._extend_seconds = extend_seconds
        self._stop = Event()
        self._thread: Thread | None = None
        self._count = 0
        self._error: str | None = None

    def start(self) -> None:
        if self._interval_seconds <= 0:
            return
        self._thread = Thread(
            target=self._run,
            name=f"pelicanbench-heartbeat-{_safe_identifier(self._lease.cell_id)}",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            try:
                heartbeat_campaign_lease(
                    self._database,
                    self._manifest,
                    cell_id=self._lease.cell_id,
                    worker_id=self._lease.worker_id,
                    lease_token=self._lease.lease_token,
                    extend_seconds=self._extend_seconds,
                )
                self._count += 1
            except Exception as exc:  # pragma: no cover - exact provider timing is nondeterministic
                self._error = f"{type(exc).__name__}: {exc}"
                return

    def stop(self) -> _HeartbeatResult:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self._interval_seconds * 2))
            if self._thread.is_alive() and self._error is None:
                self._error = "RuntimeError: lease heartbeat thread did not stop"
        return _HeartbeatResult(count=self._count, error=self._error)


def _write_immutable_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write an immutable record or verify an idempotent replay."""

    if path.exists():
        if read_json(path) != dict(payload):
            raise ValueError(f"immutable campaign record collision: {path}")
        return path
    return write_json(path, payload)


def _record_path(root: Path, record: CampaignCellExecution) -> Path:
    digest = record.record_hash.split(":", 1)[1][:16]
    return (
        root
        / "execution-records"
        / _safe_identifier(record.cell_id)
        / f"attempt-{record.attempt:03d}-{digest}.json"
    )


def read_campaign_execution_records(root: str | Path) -> tuple[dict[str, Any], ...]:
    """Read all immutable campaign execution records in stable order."""

    records: list[dict[str, Any]] = []
    for source in sorted(Path(root).glob("execution-records/*/*.json")):
        value = read_json(source)
        if not isinstance(value, dict):
            raise TypeError(f"campaign execution record must be an object: {source}")
        expected = value.get("record_hash")
        payload = {key: item for key, item in value.items() if key != "record_hash"}
        if expected != content_hash(payload):
            raise ValueError(f"campaign execution record hash mismatch: {source}")
        records.append(value)
    return tuple(
        sorted(
            records,
            key=lambda item: (
                str(item["cell_id"]),
                int(item.get("attempt", 0)),
                str(item["record_hash"]),
            ),
        )
    )


def export_campaign_execution_index(root: str | Path, output: str | Path) -> Path:
    """Build a portable JSONL index from immutable per-attempt records."""

    return write_jsonl(output, read_campaign_execution_records(root))



def _is_worker_terminal_event(event: StoreEvent) -> bool:
    return (
        event.reason in {
            "task-missing-from-worker-corpus",
            "worker-infrastructure-failure",
            "generation-failed",
            "runner-produced-no-outcome",
            "canonical-artifact-retained",
        }
        or event.reason.startswith("artifact-failed-retention-gates:")
    )


def _terminal_event_key(event: StoreEvent) -> tuple[str, str, int]:
    if event.lease_token is None:
        raise ValueError(f"terminal worker event has no lease token: {event.event_id}")
    return event.cell_id, event.lease_token, event.attempt


def reconcile_campaign_execution_records(
    database: str | Path,
    manifest: CampaignManifest,
    root: str | Path,
) -> CampaignExecutionReconciliation:
    """Reconcile immutable worker records with terminal campaign-store events."""

    errors: list[str] = []
    store_reconciliation = reconcile_campaign_store(database, manifest)
    if not store_reconciliation.valid:
        errors.extend(
            f"campaign store: {message}" for message in store_reconciliation.errors
        )
    terminal_events = tuple(
        event
        for event in read_store_events(database)
        if event.new_state in {"succeeded", "failed", "quarantined"}
        and event.worker_id is not None
        and _is_worker_terminal_event(event)
    )
    event_map: dict[tuple[str, str, int], StoreEvent] = {}
    for event in terminal_events:
        try:
            key = _terminal_event_key(event)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if key in event_map:
            errors.append(f"duplicate terminal event key: {key}")
        else:
            event_map[key] = event

    records = read_campaign_execution_records(root)
    record_map: dict[tuple[str, str, int], dict[str, Any]] = {}
    for record in records:
        try:
            key = (
                str(record["cell_id"]),
                str(record["lease_token"]),
                int(record["attempt"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"malformed execution record identity: {exc}")
            continue
        if key in record_map:
            errors.append(f"duplicate execution record key: {key}")
        else:
            record_map[key] = record

    for key in sorted(set(event_map) | set(record_map)):
        event = event_map.get(key)
        record = record_map.get(key)
        if event is None:
            errors.append(f"execution record has no terminal event: {key}")
            continue
        if record is None:
            errors.append(f"terminal event has no execution record: {key}")
            continue
        expected_fields = {
            "campaign_id": event.campaign_id,
            "cell_id": event.cell_id,
            "worker_id": event.worker_id,
            "lease_token": event.lease_token,
            "attempt": event.attempt,
            "terminal_state": event.new_state,
            "terminal_reason": event.reason,
            "artifact_id": event.artifact_id,
        }
        for field, expected in expected_fields.items():
            if record.get(field) != expected:
                errors.append(f"execution record field mismatch for {key}: {field}")
        try:
            charged_cost = float(record["charged_cost"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"execution record has invalid charged_cost: {key}")
        else:
            if abs(charged_cost - event.actual_cost) > 1e-8:
                errors.append(f"execution record cost mismatch for {key}")

    payload = {
        "schema_version": "1.0.0",
        "campaign_id": manifest.campaign_id,
        "valid": not errors,
        "terminal_events": len(terminal_events),
        "execution_records": len(records),
        "matched_records": len(set(event_map) & set(record_map)),
        "errors": errors,
    }
    return CampaignExecutionReconciliation(
        schema_version="1.0.0",
        campaign_id=manifest.campaign_id,
        valid=not errors,
        terminal_events=len(terminal_events),
        execution_records=len(records),
        matched_records=len(set(event_map) & set(record_map)),
        errors=tuple(errors),
        reconciliation_hash=content_hash(payload),
    )


def _reported_cost(metadata: Mapping[str, Any]) -> float | None:
    """Read an explicitly reported non-negative cost from common adapter fields."""

    candidates: list[Any] = [
        metadata.get("actual_cost"),
        metadata.get("cost_usd"),
        metadata.get("cost"),
    ]
    usage = metadata.get("usage")
    if isinstance(usage, Mapping):
        candidates.extend((usage.get("cost_usd"), usage.get("cost")))
    for value in candidates:
        if value is None or isinstance(value, bool):
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(amount) or amount < 0:
            raise ValueError(
                "adapter-reported campaign cost must be finite and non-negative"
            )
        return amount
    return None


def _cost_for_result(lease: StoreLease, result: RunResult) -> tuple[float, str]:
    metadata: Mapping[str, Any] = {}
    if result.trials:
        metadata = result.trials[0].metadata
    try:
        reported = _reported_cost(metadata)
    except ValueError:
        return round(lease.estimated_cost, 8), "invalid-reported-cost-fallback"
    if reported is not None:
        return round(reported, 8), "adapter-reported"
    return round(lease.estimated_cost, 8), "reserved-estimate"


def _terminal_outcome(
    result: RunResult,
) -> tuple[StoreTerminalState, str, str | None, str | None]:
    if result.failures:
        failure = result.failures[0]
        return (
            "failed",
            "generation-failed",
            failure.error_type,
            failure.error_message,
        )
    if not result.trials or not result.scorecards:
        return "failed", "runner-produced-no-outcome", "RuntimeError", "missing run outcome"
    score = result.scorecards[0]
    retention_gates = (
        "safe_and_parseable",
        "nonblank_render",
        "judge_input_safe",
    )
    failed_gates = [name for name in retention_gates if not score.critical_gates.get(name, False)]
    if failed_gates:
        return (
            "quarantined",
            "artifact-failed-retention-gates:" + ",".join(failed_gates),
            None,
            None,
        )
    return "succeeded", "canonical-artifact-retained", None, None


def _record(
    manifest: CampaignManifest,
    lease: StoreLease,
    adapter: ModelAdapter,
    result: RunResult,
    *,
    terminal_state: StoreTerminalState,
    reason: str,
    cost: float,
    cost_basis: str,
    output_directory: Path,
    error_type: str | None,
    error_message: str | None,
    heartbeat_count: int,
    heartbeat_error: str | None,
) -> CampaignCellExecution:
    trial = result.trials[0] if result.trials else None
    score = result.scorecards[0] if result.scorecards else None
    payload = {
        "schema_version": "1.0.0",
        "campaign_id": manifest.campaign_id,
        "cell_id": lease.cell_id,
        "worker_id": lease.worker_id,
        "lease_token": lease.lease_token,
        "model_id": adapter.model_id,
        "model_revision": adapter.model_revision,
        "adapter_id": adapter.adapter_id,
        "task_id": lease.task_id,
        "replicate": lease.replicate,
        "seed": lease.seed,
        "terminal_state": terminal_state,
        "terminal_reason": reason,
        "charged_cost": cost,
        "cost_basis": cost_basis,
        "artifact_id": None if trial is None else trial.artifact_id,
        "run_id": result.manifest.run_id,
        "scorecard_hash": (
            None if score is None else content_hash(score.model_dump(mode="json"))
        ),
        "output_directory": output_directory.as_posix(),
        "error_type": error_type,
        "error_message": error_message,
        "heartbeat_count": heartbeat_count,
        "heartbeat_error": heartbeat_error,
        "attempt": lease.attempt,
    }
    return CampaignCellExecution(
        **payload,
        record_hash=content_hash(payload),
    )


def execute_campaign_batch(
    database: str | Path,
    manifest: CampaignManifest,
    tasks: Iterable[BenchmarkTask],
    adapter: ModelAdapter,
    *,
    worker_id: str,
    output_directory: str | Path,
    limit: int = 1,
    lease_seconds: int = 900,
    stage_id: str | None = None,
    firewall_policy: JudgeFirewallPolicy | None = None,
    semantic_assessor: SemanticAssessor | None = None,
    benchmark_commit: str = "working-tree",
    environment_digest: str = "campaign-worker",
    now: str | None = None,
    token_factory: Callable[[], str] | None = None,
    heartbeat_interval_seconds: float | None = None,
) -> CampaignWorkerResult:
    """Lease and execute at most ``limit`` cells for one model adapter.

    The function never suppresses an attempted cell.  Provider failures are retained by
    :func:`run_benchmark`, and malformed or judge-unsafe artifacts are quarantined.  When
    an adapter does not report a cost, the reserved estimate is charged conservatively.
    """

    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if limit < 1:
        raise ValueError("limit must be positive")
    if heartbeat_interval_seconds is not None and heartbeat_interval_seconds < 0:
        raise ValueError("heartbeat_interval_seconds cannot be negative")
    if now is not None and heartbeat_interval_seconds not in {None, 0, 0.0}:
        raise ValueError(
            "automatic heartbeats cannot be combined with a fixed deterministic time"
        )
    selected_heartbeat_interval = heartbeat_interval_seconds
    if selected_heartbeat_interval is None:
        selected_heartbeat_interval = (
            0.0 if now is not None else max(1.0, min(float(lease_seconds) / 3.0, 300.0))
        )
    if (
        selected_heartbeat_interval >= lease_seconds
        and selected_heartbeat_interval > 0
    ):
        raise ValueError("heartbeat interval must be shorter than the lease duration")
    task_map = {task.task_id: task for task in tasks}
    leases = lease_campaign_cells(
        database,
        manifest,
        worker_id=worker_id,
        limit=limit,
        lease_seconds=lease_seconds,
        stage_id=stage_id,
        model_id=adapter.model_id,
        now=now,
        token_factory=token_factory,
    )
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    records: list[CampaignCellExecution] = []
    for lease in leases:
        task = task_map.get(lease.task_id)
        if task is None:
            # The lease must still be resolved so another worker cannot repeatedly receive
            # an impossible cell.
            complete_campaign_lease(
                database,
                manifest,
                cell_id=lease.cell_id,
                worker_id=worker_id,
                lease_token=lease.lease_token,
                new_state="failed",
                reason="task-missing-from-worker-corpus",
                actual_cost=0.0,
                now=now,
            )
            payload = {
                "schema_version": "1.0.0",
                "campaign_id": manifest.campaign_id,
                "cell_id": lease.cell_id,
                "worker_id": worker_id,
                "lease_token": lease.lease_token,
                "model_id": adapter.model_id,
                "model_revision": adapter.model_revision,
                "adapter_id": adapter.adapter_id,
                "task_id": lease.task_id,
                "replicate": lease.replicate,
                "seed": lease.seed,
                "terminal_state": "failed",
                "terminal_reason": "task-missing-from-worker-corpus",
                "charged_cost": 0.0,
                "cost_basis": "not-invoked",
                "artifact_id": None,
                "run_id": None,
                "scorecard_hash": None,
                "output_directory": "",
                "error_type": "KeyError",
                "error_message": f"task not supplied: {lease.task_id}",
                "heartbeat_count": 0,
                "heartbeat_error": None,
                "attempt": lease.attempt,
            }
            record = CampaignCellExecution(**payload, record_hash=content_hash(payload))
            _write_immutable_json(_record_path(root, record), record.as_dict())
            records.append(record)
            continue

        cell_relative = (
            Path("cells")
            / _safe_identifier(lease.cell_id)
            / f"attempt-{lease.attempt:03d}"
        )
        cell_directory = root / cell_relative
        heartbeat = _LeaseHeartbeat(
            database,
            manifest,
            lease,
            interval_seconds=selected_heartbeat_interval,
            extend_seconds=lease_seconds,
        )
        heartbeat.start()
        try:
            result = run_benchmark(
                [task],
                adapter,
                output_directory=cell_directory,
                seed=lease.seed,
                benchmark_commit=benchmark_commit,
                environment_digest=environment_digest,
                semantic_assessor=semantic_assessor,
                judge_policy=firewall_policy,
                continue_on_error=True,
            )
        except Exception as exc:
            heartbeat_result = heartbeat.stop()
            reason = "worker-infrastructure-failure"
            cost = round(lease.estimated_cost, 8)
            complete_campaign_lease(
                database,
                manifest,
                cell_id=lease.cell_id,
                worker_id=worker_id,
                lease_token=lease.lease_token,
                new_state="failed",
                reason=reason,
                actual_cost=cost,
                now=now,
            )
            payload = {
                "schema_version": "1.0.0",
                "campaign_id": manifest.campaign_id,
                "cell_id": lease.cell_id,
                "worker_id": worker_id,
                "lease_token": lease.lease_token,
                "model_id": adapter.model_id,
                "model_revision": adapter.model_revision,
                "adapter_id": adapter.adapter_id,
                "task_id": lease.task_id,
                "replicate": lease.replicate,
                "seed": lease.seed,
                "terminal_state": "failed",
                "terminal_reason": reason,
                "charged_cost": cost,
                "cost_basis": "worker-exception-conservative-estimate",
                "artifact_id": None,
                "run_id": None,
                "scorecard_hash": None,
                "output_directory": cell_relative.as_posix(),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "heartbeat_count": heartbeat_result.count,
                "heartbeat_error": heartbeat_result.error,
                "attempt": lease.attempt,
            }
            record = CampaignCellExecution(**payload, record_hash=content_hash(payload))
            _write_immutable_json(_record_path(root, record), record.as_dict())
            records.append(record)
            continue

        heartbeat_result = heartbeat.stop()
        terminal_state, reason, error_type, error_message = _terminal_outcome(result)
        cost, cost_basis = _cost_for_result(lease, result)
        trial = result.trials[0] if result.trials else None
        artifact_id = None if trial is None else trial.artifact_id
        complete_campaign_lease(
            database,
            manifest,
            cell_id=lease.cell_id,
            worker_id=worker_id,
            lease_token=lease.lease_token,
            new_state=terminal_state,
            reason=reason,
            actual_cost=cost,
            artifact_id=artifact_id if terminal_state in {"succeeded", "quarantined"} else None,
            now=now,
        )
        record = _record(
            manifest,
            lease,
            adapter,
            result,
            terminal_state=terminal_state,
            reason=reason,
            cost=cost,
            cost_basis=cost_basis,
            output_directory=cell_relative,
            error_type=error_type,
            error_message=error_message,
            heartbeat_count=heartbeat_result.count,
            heartbeat_error=heartbeat_result.error,
        )
        _write_immutable_json(_record_path(root, record), record.as_dict())
        records.append(record)

    states = [item.terminal_state for item in records]
    summary_payload = {
        "schema_version": "1.0.0",
        "campaign_id": manifest.campaign_id,
        "worker_id": worker_id,
        "model_id": adapter.model_id,
        "leased_cells": len(records),
        "succeeded": states.count("succeeded"),
        "quarantined": states.count("quarantined"),
        "failed": states.count("failed"),
        "charged_cost": round(sum(item.charged_cost for item in records), 8),
        "heartbeat_count": sum(item.heartbeat_count for item in records),
        "heartbeat_failures": sum(item.heartbeat_error is not None for item in records),
        "records": [item.as_dict() for item in records],
    }
    batch = CampaignWorkerResult(
        schema_version="1.0.0",
        campaign_id=manifest.campaign_id,
        worker_id=worker_id,
        model_id=adapter.model_id,
        leased_cells=len(records),
        succeeded=states.count("succeeded"),
        quarantined=states.count("quarantined"),
        failed=states.count("failed"),
        charged_cost=round(sum(item.charged_cost for item in records), 8),
        heartbeat_count=sum(item.heartbeat_count for item in records),
        heartbeat_failures=sum(item.heartbeat_error is not None for item in records),
        records=tuple(records),
        batch_hash=content_hash(summary_payload),
    )
    batch_digest = batch.batch_hash.split(":", 1)[1][:16]
    batch_path = (
        root
        / "worker-batches"
        / _safe_identifier(worker_id)
        / f"{batch_digest}.json"
    )
    _write_immutable_json(batch_path, batch.as_dict())
    return batch


__all__ = [
    "CampaignCellExecution",
    "CampaignExecutionReconciliation",
    "CampaignWorkerResult",
    "execute_campaign_batch",
    "export_campaign_execution_index",
    "read_campaign_execution_records",
    "reconcile_campaign_execution_records",
]
