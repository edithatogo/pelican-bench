"""Transactional SQLite state for prospective campaign execution.

The JSONL event chain in :mod:`pelicanbench.campaign` is a portable interchange
format, but it is intentionally a single-writer contract.  This module adds a
standard-library-only SQLite implementation for atomic leasing, bounded parallelism,
budget reservation, lease expiry, resumability, and deterministic audit export.

SQLite is not presented as a globally distributed scheduler.  It is the normative
single-host and shared-filesystem reference store; larger deployments can implement the
same transition and hash-chain contract in a serialisable database.
"""

from __future__ import annotations

import json
import math
import secrets
import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

from .campaign import CELL_STATES, TERMINAL_STATES, CampaignManifest, CellState
from .io import content_hash
from .timeutil import utc_now_iso

StoreTerminalState = Literal["succeeded", "failed", "quarantined", "cancelled"]
CompletionState = Literal["ready", "succeeded", "failed", "quarantined", "cancelled"]

_ALLOWED_STORE_TRANSITIONS: dict[str, frozenset[str]] = {
    "ready": frozenset({"leased", "cancelled"}),
    "leased": frozenset({"leased", "ready", "succeeded", "failed", "quarantined", "cancelled"}),
    "failed": frozenset({"ready"}),
}

_SCHEMA = "2"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_utc(value: str) -> datetime:
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError("campaign timestamps must include a timezone")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _state(value: Any, *, field: str) -> CellState:
    candidate = str(value)
    if candidate not in CELL_STATES:
        raise ValueError(f"{field} is not a valid campaign state: {candidate}")
    return cast(CellState, candidate)


def _new_lease_token(
    connection: sqlite3.Connection,
    token_factory: Callable[[], str],
) -> str:
    """Return a non-empty lease token that is not already active or recorded.

    Production callers use cryptographically random tokens. Deterministic evidence
    generators may inject a token factory, which keeps fixture snapshots stable without
    weakening the default execution path.
    """

    for _ in range(8):
        raw = token_factory().strip()
        if not raw:
            continue
        token = raw if raw.startswith("LEASE-") else "LEASE-" + raw
        active = connection.execute(
            "SELECT 1 FROM cells WHERE lease_token = ? LIMIT 1", (token,)
        ).fetchone()
        recorded = connection.execute(
            "SELECT 1 FROM events WHERE lease_token = ? LIMIT 1", (token,)
        ).fetchone()
        if active is None and recorded is None:
            return token
    raise RuntimeError("lease token factory did not produce a unique non-empty token")


def _connect(path: str | Path) -> sqlite3.Connection:
    database = Path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=30.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def _manifest_hash(manifest: CampaignManifest) -> str:
    return content_hash(manifest.as_dict())


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    try:
        rows = connection.execute("SELECT key, value FROM metadata ORDER BY key")
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc).lower():
            raise
        return {}
    return {str(row["key"]): str(row["value"]) for row in rows}


def _verify_manifest(connection: sqlite3.Connection, manifest: CampaignManifest) -> None:
    values = _metadata(connection)
    if not values:
        raise ValueError("campaign store is not initialised")
    if values.get("schema_version") != _SCHEMA:
        raise ValueError("campaign store schema version is unsupported")
    if values.get("campaign_id") != manifest.campaign_id:
        raise ValueError("campaign store belongs to a different campaign")
    if values.get("manifest_hash") != _manifest_hash(manifest):
        raise ValueError("campaign manifest does not match the initialised store")


def _last_event_hash(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    return None if row is None else str(row["event_hash"])


def _next_sequence(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT MAX(sequence) AS value FROM events").fetchone()
    value = None if row is None else row["value"]
    return 0 if value is None else int(value) + 1


def _event_payload_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Project immutable event columns into the content-addressed payload."""

    return {
        "schema_version": "1.0.0",
        "sequence": int(row["sequence"]),
        "campaign_id": str(row["campaign_id"]),
        "cell_id": str(row["cell_id"]),
        "previous_state": str(row["previous_state"]),
        "new_state": str(row["new_state"]),
        "occurred_at": str(row["occurred_at"]),
        "worker_id": None if row["worker_id"] is None else str(row["worker_id"]),
        "lease_token": None if row["lease_token"] is None else str(row["lease_token"]),
        "attempt": int(row["attempt"]),
        "reason": str(row["reason"]),
        "estimated_cost": float(row["estimated_cost"]),
        "actual_cost": float(row["actual_cost"]),
        "artifact_id": None if row["artifact_id"] is None else str(row["artifact_id"]),
        "previous_event_hash": (
            None if row["previous_event_hash"] is None else str(row["previous_event_hash"])
        ),
    }


@dataclass(frozen=True, slots=True)
class StoreLease:
    cell_id: str
    stage_id: str
    model_id: str
    task_id: str
    replicate: int
    seed: int
    worker_id: str
    lease_token: str
    leased_at: str
    lease_expires_at: str
    attempt: int
    estimated_cost: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StoreEvent:
    schema_version: str
    sequence: int
    event_id: str
    campaign_id: str
    cell_id: str
    previous_state: CellState
    new_state: CellState
    occurred_at: str
    worker_id: str | None
    lease_token: str | None
    attempt: int
    reason: str
    estimated_cost: float
    actual_cost: float
    artifact_id: str | None
    previous_event_hash: str | None
    event_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StoreStatus:
    campaign_id: str
    manifest_hash: str
    state_counts: dict[str, int]
    cell_count: int
    event_count: int
    spent_cost: float
    reserved_cost: float
    hard_budget: float | None
    remaining_budget: float | None
    active_leases: int
    expired_leases: int
    terminal_cells: int
    complete: bool
    budget_exceeded: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StoreReconciliation:
    campaign_id: str
    valid: bool
    manifest_matches: bool
    event_chain_valid: bool
    cell_state_matches: bool
    cost_matches: bool
    lease_invariants_valid: bool
    event_count: int
    replayed_cost: float
    stored_cost: float
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["errors"] = list(self.errors)
        return value


def initialise_campaign_store(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    overwrite: bool = False,
) -> StoreStatus:
    """Create a transactional campaign store from an immutable manifest.

    Re-running the function against an existing matching store is idempotent.  An
    existing mismatched store is rejected unless ``overwrite`` is explicit.
    """

    database = Path(path)
    if overwrite and database.exists():
        database.unlink()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(database) + suffix)
            if sidecar.exists():
                sidecar.unlink()

    connection = _connect(database)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cells (
                cell_id TEXT PRIMARY KEY,
                stage_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                replicate INTEGER NOT NULL CHECK (replicate >= 0),
                seed INTEGER NOT NULL CHECK (seed >= 0),
                initial_state TEXT NOT NULL,
                state TEXT NOT NULL,
                estimated_cost REAL,
                actual_cost REAL NOT NULL DEFAULT 0 CHECK (actual_cost >= 0),
                attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
                lease_owner TEXT,
                lease_token TEXT,
                leased_at TEXT,
                lease_expires_at TEXT,
                artifact_id TEXT,
                reason TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS cells_state_idx
                ON cells(state, stage_id, model_id, task_id, replicate);
            CREATE INDEX IF NOT EXISTS cells_lease_idx
                ON cells(state, lease_expires_at);
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                campaign_id TEXT NOT NULL,
                cell_id TEXT NOT NULL REFERENCES cells(cell_id),
                previous_state TEXT NOT NULL,
                new_state TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                worker_id TEXT,
                lease_token TEXT,
                attempt INTEGER NOT NULL CHECK (attempt >= 0),
                reason TEXT NOT NULL,
                estimated_cost REAL NOT NULL CHECK (estimated_cost >= 0),
                actual_cost REAL NOT NULL CHECK (actual_cost >= 0),
                artifact_id TEXT,
                previous_event_hash TEXT,
                event_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL
            );
            """
        )
        connection.execute("BEGIN IMMEDIATE")
        existing = _metadata(connection)
        if existing:
            _verify_manifest(connection, manifest)
            connection.execute("COMMIT")
            return campaign_store_status(database, manifest)

        created_at = manifest.generated_at or utc_now_iso()
        metadata = {
            "schema_version": _SCHEMA,
            "campaign_id": manifest.campaign_id,
            "manifest_hash": _manifest_hash(manifest),
            "task_identity_commitment": manifest.task_identity_commitment,
            "policy_hash": manifest.policy_hash,
            "hard_budget": _canonical_json(manifest.hard_budget),
            "max_parallel_per_model": str(manifest.max_parallel_per_model),
            "created_at": created_at,
        }
        connection.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
        rows = [
            (
                cell.cell_id,
                cell.stage_id,
                cell.model_id,
                cell.task_id,
                cell.replicate,
                cell.seed,
                cell.state,
                cell.state,
                cell.estimated_cost,
                created_at,
            )
            for cell in manifest.cells
        ]
        connection.executemany(
            """
            INSERT INTO cells(
                cell_id, stage_id, model_id, task_id, replicate, seed,
                initial_state, state, estimated_cost, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.execute("COMMIT")
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    return campaign_store_status(database, manifest)


def _insert_event(
    connection: sqlite3.Connection,
    *,
    manifest: CampaignManifest,
    cell_id: str,
    previous_state: CellState,
    new_state: CellState,
    occurred_at: str,
    worker_id: str | None,
    lease_token: str | None,
    attempt: int,
    reason: str,
    estimated_cost: float,
    actual_cost: float,
    artifact_id: str | None,
) -> StoreEvent:
    if new_state not in _ALLOWED_STORE_TRANSITIONS.get(previous_state, frozenset()):
        raise ValueError(f"illegal campaign transition: {previous_state} -> {new_state}")
    if not reason.strip():
        raise ValueError("campaign event reason is required")
    if estimated_cost < 0 or actual_cost < 0:
        raise ValueError("campaign costs cannot be negative")
    if new_state in {"succeeded", "quarantined"} and not artifact_id:
        raise ValueError(f"{new_state} events require an artifact_id")
    sequence = _next_sequence(connection)
    previous_event_hash = _last_event_hash(connection)
    payload = {
        "schema_version": "1.0.0",
        "sequence": sequence,
        "campaign_id": manifest.campaign_id,
        "cell_id": cell_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "occurred_at": occurred_at,
        "worker_id": worker_id,
        "lease_token": lease_token,
        "attempt": attempt,
        "reason": reason,
        "estimated_cost": round(estimated_cost, 8),
        "actual_cost": round(actual_cost, 8),
        "artifact_id": artifact_id,
        "previous_event_hash": previous_event_hash,
    }
    event_hash = content_hash(payload)
    event_id = "CEVT-" + event_hash.split(":", 1)[1][:24]
    connection.execute(
        """
        INSERT INTO events(
            sequence, event_id, campaign_id, cell_id, previous_state, new_state,
            occurred_at, worker_id, lease_token, attempt, reason, estimated_cost,
            actual_cost, artifact_id, previous_event_hash, event_hash, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sequence,
            event_id,
            manifest.campaign_id,
            cell_id,
            previous_state,
            new_state,
            occurred_at,
            worker_id,
            lease_token,
            attempt,
            reason,
            round(estimated_cost, 8),
            round(actual_cost, 8),
            artifact_id,
            previous_event_hash,
            event_hash,
            _canonical_json(payload),
        ),
    )
    return StoreEvent(event_id=event_id, event_hash=event_hash, **cast(Any, payload))


def _reclaim_expired_in_transaction(
    connection: sqlite3.Connection,
    manifest: CampaignManifest,
    *,
    now: str,
) -> tuple[StoreEvent, ...]:
    now_value = _parse_utc(now)
    rows = connection.execute(
        """
        SELECT * FROM cells
        WHERE state = 'leased' AND lease_expires_at IS NOT NULL
        ORDER BY stage_id, model_id, task_id, replicate
        """
    ).fetchall()
    events: list[StoreEvent] = []
    for row in rows:
        expiry = _parse_utc(str(row["lease_expires_at"]))
        if expiry > now_value:
            continue
        event = _insert_event(
            connection,
            manifest=manifest,
            cell_id=str(row["cell_id"]),
            previous_state="leased",
            new_state="ready",
            occurred_at=now,
            worker_id=(None if row["lease_owner"] is None else str(row["lease_owner"])),
            lease_token=(None if row["lease_token"] is None else str(row["lease_token"])),
            attempt=int(row["attempt_count"]),
            reason="lease-expired",
            estimated_cost=float(row["estimated_cost"] or 0.0),
            actual_cost=0.0,
            artifact_id=None,
        )
        connection.execute(
            """
            UPDATE cells
            SET state = 'ready', lease_owner = NULL, lease_token = NULL,
                leased_at = NULL, lease_expires_at = NULL,
                reason = 'lease-expired', updated_at = ?
            WHERE cell_id = ?
            """,
            (now, row["cell_id"]),
        )
        events.append(event)
    return tuple(events)


def reclaim_expired_leases(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    now: str | None = None,
) -> tuple[StoreEvent, ...]:
    selected_now = now or utc_now_iso()
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_manifest(connection, manifest)
        events = _reclaim_expired_in_transaction(connection, manifest, now=selected_now)
        connection.execute("COMMIT")
        return events
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def lease_campaign_cells(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    worker_id: str,
    limit: int = 1,
    lease_seconds: int = 900,
    stage_id: str | None = None,
    model_id: str | None = None,
    now: str | None = None,
    token_factory: Callable[[], str] | None = None,
) -> tuple[StoreLease, ...]:
    """Atomically lease ready cells without duplicating work or overspending."""

    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if limit < 1:
        raise ValueError("limit must be positive")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be positive")
    if manifest.hard_budget is None:
        raise ValueError("campaign is not executable: hard budget required")
    if manifest.budget_gate.startswith("blocked-"):
        raise ValueError(f"campaign is not executable: {manifest.budget_gate}")

    selected_now = now or utc_now_iso()
    selected_token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
    now_value = _parse_utc(selected_now)
    expires_at = _format_utc(now_value + timedelta(seconds=lease_seconds))
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_manifest(connection, manifest)
        _reclaim_expired_in_transaction(connection, manifest, now=selected_now)
        spent_row = connection.execute(
            "SELECT COALESCE(SUM(actual_cost), 0) AS value FROM cells"
        ).fetchone()
        reserved_row = connection.execute(
            "SELECT COALESCE(SUM(estimated_cost), 0) AS value FROM cells WHERE state = 'leased'"
        ).fetchone()
        spent = float(spent_row["value"] if spent_row is not None else 0.0)
        reserved = float(reserved_row["value"] if reserved_row is not None else 0.0)
        active = Counter(
            str(row["model_id"])
            for row in connection.execute("SELECT model_id FROM cells WHERE state = 'leased'")
        )
        clauses = ["state = 'ready'"]
        parameters: list[Any] = []
        if stage_id is not None:
            clauses.append("stage_id = ?")
            parameters.append(stage_id)
        if model_id is not None:
            clauses.append("model_id = ?")
            parameters.append(model_id)
        query = (
            "SELECT * FROM cells WHERE "  # nosec B608
            + " AND ".join(clauses)
            + " ORDER BY stage_id, model_id, task_id, replicate"
        )
        rows = connection.execute(query, parameters).fetchall()
        leases: list[StoreLease] = []
        for row in rows:
            if len(leases) >= limit:
                break
            row_model = str(row["model_id"])
            if active[row_model] >= manifest.max_parallel_per_model:
                continue
            estimate = row["estimated_cost"]
            if estimate is None:
                continue
            estimate_value = float(estimate)
            if spent + reserved + estimate_value > manifest.hard_budget:
                continue
            attempt = int(row["attempt_count"]) + 1
            lease_token = _new_lease_token(connection, selected_token_factory)
            event = _insert_event(
                connection,
                manifest=manifest,
                cell_id=str(row["cell_id"]),
                previous_state="ready",
                new_state="leased",
                occurred_at=selected_now,
                worker_id=worker_id,
                lease_token=lease_token,
                attempt=attempt,
                reason=f"worker-lease:{worker_id}",
                estimated_cost=estimate_value,
                actual_cost=0.0,
                artifact_id=None,
            )
            connection.execute(
                """
                UPDATE cells
                SET state = 'leased', attempt_count = ?, lease_owner = ?, lease_token = ?,
                    leased_at = ?, lease_expires_at = ?, reason = ?, updated_at = ?
                WHERE cell_id = ? AND state = 'ready'
                """,
                (
                    attempt,
                    worker_id,
                    lease_token,
                    selected_now,
                    expires_at,
                    event.reason,
                    selected_now,
                    row["cell_id"],
                ),
            )
            leases.append(
                StoreLease(
                    cell_id=str(row["cell_id"]),
                    stage_id=str(row["stage_id"]),
                    model_id=row_model,
                    task_id=str(row["task_id"]),
                    replicate=int(row["replicate"]),
                    seed=int(row["seed"]),
                    worker_id=worker_id,
                    lease_token=lease_token,
                    leased_at=selected_now,
                    lease_expires_at=expires_at,
                    attempt=attempt,
                    estimated_cost=estimate_value,
                )
            )
            active[row_model] += 1
            reserved += estimate_value
        connection.execute("COMMIT")
        return tuple(leases)
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def heartbeat_campaign_lease(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    cell_id: str,
    worker_id: str,
    lease_token: str,
    extend_seconds: int = 900,
    now: str | None = None,
) -> StoreLease:
    """Extend an active lease while preserving a content-addressed audit event."""

    if extend_seconds < 1:
        raise ValueError("extend_seconds must be positive")
    selected_now = now or utc_now_iso()
    now_value = _parse_utc(selected_now)
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_manifest(connection, manifest)
        row = connection.execute("SELECT * FROM cells WHERE cell_id = ?", (cell_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown campaign cell: {cell_id}")
        if str(row["state"]) != "leased":
            raise ValueError("campaign cell is not currently leased")
        if str(row["lease_owner"]) != worker_id or str(row["lease_token"]) != lease_token:
            raise PermissionError("campaign lease ownership token does not match")
        expiry = _parse_utc(str(row["lease_expires_at"]))
        if expiry <= now_value:
            raise TimeoutError("campaign lease has expired")
        # Renew to a fixed horizon from the heartbeat time without cumulatively
        # adding a full lease duration on every heartbeat. Rapid heartbeats must
        # not extend a lease arbitrarily far into the future.
        renewal_target = now_value + timedelta(seconds=extend_seconds)
        extended_expiry = _format_utc(max(expiry, renewal_target))
        estimate = float(row["estimated_cost"] or 0.0)
        event = _insert_event(
            connection,
            manifest=manifest,
            cell_id=cell_id,
            previous_state="leased",
            new_state="leased",
            occurred_at=selected_now,
            worker_id=worker_id,
            lease_token=lease_token,
            attempt=int(row["attempt_count"]),
            reason=f"lease-heartbeat:{worker_id}",
            estimated_cost=estimate,
            actual_cost=0.0,
            artifact_id=None,
        )
        connection.execute(
            """
            UPDATE cells
            SET lease_expires_at = ?, reason = ?, updated_at = ?
            WHERE cell_id = ?
            """,
            (extended_expiry, event.reason, selected_now, cell_id),
        )
        connection.execute("COMMIT")
        return StoreLease(
            cell_id=cell_id,
            stage_id=str(row["stage_id"]),
            model_id=str(row["model_id"]),
            task_id=str(row["task_id"]),
            replicate=int(row["replicate"]),
            seed=int(row["seed"]),
            worker_id=worker_id,
            lease_token=lease_token,
            leased_at=str(row["leased_at"]),
            lease_expires_at=extended_expiry,
            attempt=int(row["attempt_count"]),
            estimated_cost=estimate,
        )
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def complete_campaign_lease(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    cell_id: str,
    worker_id: str,
    lease_token: str,
    new_state: CompletionState,
    reason: str,
    actual_cost: float = 0.0,
    artifact_id: str | None = None,
    now: str | None = None,
) -> StoreEvent:
    """Complete or release a lease using an ownership token."""

    if new_state not in {"ready", "succeeded", "failed", "quarantined", "cancelled"}:
        raise ValueError(f"unsupported completion state: {new_state}")
    if not math.isfinite(actual_cost) or actual_cost < 0:
        raise ValueError("actual_cost must be finite and non-negative")
    selected_now = now or utc_now_iso()
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_manifest(connection, manifest)
        row = connection.execute("SELECT * FROM cells WHERE cell_id = ?", (cell_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown campaign cell: {cell_id}")
        if str(row["state"]) != "leased":
            raise ValueError("campaign cell is not currently leased")
        if str(row["lease_owner"]) != worker_id or str(row["lease_token"]) != lease_token:
            raise PermissionError("campaign lease ownership token does not match")
        expiry = _parse_utc(str(row["lease_expires_at"]))
        if expiry <= _parse_utc(selected_now):
            raise TimeoutError("campaign lease has expired")
        estimate = float(row["estimated_cost"] or 0.0)
        event = _insert_event(
            connection,
            manifest=manifest,
            cell_id=cell_id,
            previous_state="leased",
            new_state=new_state,
            occurred_at=selected_now,
            worker_id=worker_id,
            lease_token=lease_token,
            attempt=int(row["attempt_count"]),
            reason=reason,
            estimated_cost=estimate,
            actual_cost=actual_cost,
            artifact_id=artifact_id,
        )
        connection.execute(
            """
            UPDATE cells
            SET state = ?, actual_cost = actual_cost + ?, artifact_id = ?, reason = ?,
                lease_owner = NULL, lease_token = NULL, leased_at = NULL,
                lease_expires_at = NULL, updated_at = ?
            WHERE cell_id = ?
            """,
            (new_state, actual_cost, artifact_id, reason, selected_now, cell_id),
        )
        connection.execute("COMMIT")
        return event
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def requeue_failed_cell(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    cell_id: str,
    reason: str,
    worker_id: str | None = None,
    now: str | None = None,
) -> StoreEvent:
    selected_now = now or utc_now_iso()
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _verify_manifest(connection, manifest)
        row = connection.execute("SELECT * FROM cells WHERE cell_id = ?", (cell_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown campaign cell: {cell_id}")
        previous = _state(row["state"], field="state")
        event = _insert_event(
            connection,
            manifest=manifest,
            cell_id=cell_id,
            previous_state=previous,
            new_state="ready",
            occurred_at=selected_now,
            worker_id=worker_id,
            lease_token=None,
            attempt=int(row["attempt_count"]),
            reason=reason,
            estimated_cost=float(row["estimated_cost"] or 0.0),
            actual_cost=0.0,
            artifact_id=None,
        )
        connection.execute(
            """
            UPDATE cells
            SET state = 'ready', reason = ?, updated_at = ?, artifact_id = NULL
            WHERE cell_id = ?
            """,
            (reason, selected_now, cell_id),
        )
        connection.execute("COMMIT")
        return event
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def campaign_store_status(
    path: str | Path,
    manifest: CampaignManifest,
    *,
    now: str | None = None,
) -> StoreStatus:
    selected_now = now or utc_now_iso()
    now_value = _parse_utc(selected_now)
    connection = _connect(path)
    try:
        _verify_manifest(connection, manifest)
        counts = Counter(
            str(row["state"])
            for row in connection.execute("SELECT state FROM cells ORDER BY cell_id")
        )
        row = connection.execute(
            "SELECT COUNT(*) AS cells, COALESCE(SUM(actual_cost), 0) AS spent FROM cells"
        ).fetchone()
        event_row = connection.execute("SELECT COUNT(*) AS events FROM events").fetchone()
        reserved_row = connection.execute(
            "SELECT COALESCE(SUM(estimated_cost), 0) AS value FROM cells WHERE state = 'leased'"
        ).fetchone()
        expired = 0
        for lease in connection.execute(
            "SELECT lease_expires_at FROM cells WHERE state = 'leased' AND lease_expires_at IS NOT NULL"
        ):
            if _parse_utc(str(lease["lease_expires_at"])) <= now_value:
                expired += 1
        cell_count = int(row["cells"] if row is not None else 0)
        spent = float(row["spent"] if row is not None else 0.0)
        reserved = float(reserved_row["value"] if reserved_row is not None else 0.0)
        hard_budget = manifest.hard_budget
        remaining = None if hard_budget is None else hard_budget - spent - reserved
        terminal = sum(counts.get(state, 0) for state in TERMINAL_STATES)
        blocked = counts.get("blocked-qualification", 0) + counts.get("blocked-price", 0)
        budget_exceeded = hard_budget is not None and spent > hard_budget
        complete = (
            terminal == cell_count
            and blocked == 0
            and counts.get("ready", 0) == 0
            and counts.get("leased", 0) == 0
            and not budget_exceeded
        )
        return StoreStatus(
            campaign_id=manifest.campaign_id,
            manifest_hash=_manifest_hash(manifest),
            state_counts=dict(sorted(counts.items())),
            cell_count=cell_count,
            event_count=int(event_row["events"] if event_row is not None else 0),
            spent_cost=round(spent, 8),
            reserved_cost=round(reserved, 8),
            hard_budget=hard_budget,
            remaining_budget=(None if remaining is None else round(remaining, 8)),
            active_leases=counts.get("leased", 0),
            expired_leases=expired,
            terminal_cells=terminal,
            complete=complete,
            budget_exceeded=budget_exceeded,
        )
    finally:
        connection.close()


def read_store_events(path: str | Path) -> tuple[StoreEvent, ...]:
    connection = _connect(path)
    try:
        rows = connection.execute("SELECT * FROM events ORDER BY sequence").fetchall()
        return tuple(
            StoreEvent(
                schema_version="1.0.0",
                sequence=int(row["sequence"]),
                event_id=str(row["event_id"]),
                campaign_id=str(row["campaign_id"]),
                cell_id=str(row["cell_id"]),
                previous_state=_state(row["previous_state"], field="previous_state"),
                new_state=_state(row["new_state"], field="new_state"),
                occurred_at=str(row["occurred_at"]),
                worker_id=(None if row["worker_id"] is None else str(row["worker_id"])),
                lease_token=(None if row["lease_token"] is None else str(row["lease_token"])),
                attempt=int(row["attempt"]),
                reason=str(row["reason"]),
                estimated_cost=float(row["estimated_cost"]),
                actual_cost=float(row["actual_cost"]),
                artifact_id=(None if row["artifact_id"] is None else str(row["artifact_id"])),
                previous_event_hash=(
                    None if row["previous_event_hash"] is None else str(row["previous_event_hash"])
                ),
                event_hash=str(row["event_hash"]),
            )
            for row in rows
        )
    finally:
        connection.close()


def export_store_events(path: str | Path, output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    events = read_store_events(path)
    destination.write_text(
        "".join(_canonical_json(event.as_dict()) + "\n" for event in events),
        encoding="utf-8",
    )
    return destination


def reconcile_campaign_store(
    path: str | Path,
    manifest: CampaignManifest,
) -> StoreReconciliation:
    errors: list[str] = []
    manifest_matches = True
    event_chain_valid = True
    cell_state_matches = True
    cost_matches = True
    lease_invariants_valid = True
    connection = _connect(path)
    try:
        try:
            _verify_manifest(connection, manifest)
        except ValueError as exc:
            manifest_matches = False
            errors.append(str(exc))
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }
        missing_tables = sorted({"cells", "events"} - tables)
        if missing_tables:
            errors.append("campaign store is missing tables: " + ", ".join(missing_tables))
            return StoreReconciliation(
                campaign_id=manifest.campaign_id,
                valid=False,
                manifest_matches=manifest_matches,
                event_chain_valid=False,
                cell_state_matches=False,
                cost_matches=False,
                lease_invariants_valid=False,
                event_count=0,
                replayed_cost=0.0,
                stored_cost=0.0,
                errors=tuple(errors),
            )
        events = connection.execute("SELECT * FROM events ORDER BY sequence").fetchall()
        states = {cell.cell_id: cell.state for cell in manifest.cells}
        costs = {cell.cell_id: 0.0 for cell in manifest.cells}
        previous_hash: str | None = None
        for expected_sequence, row in enumerate(events):
            try:
                payload = json.loads(str(row["payload_json"]))
                if int(row["sequence"]) != expected_sequence:
                    raise ValueError("event sequence is not contiguous")
                if row["previous_event_hash"] != previous_hash:
                    raise ValueError("event hash chain is broken")
                projected_payload = _event_payload_from_row(row)
                if payload != projected_payload:
                    raise ValueError("event columns do not match the immutable payload")
                expected_event_hash = content_hash(payload)
                if str(row["event_hash"]) != expected_event_hash:
                    raise ValueError("event payload hash does not match")
                expected_event_id = "CEVT-" + expected_event_hash.split(":", 1)[1][:24]
                if str(row["event_id"]) != expected_event_id:
                    raise ValueError("event_id does not match the content-addressed event hash")
                cell_id = str(row["cell_id"])
                if cell_id not in states:
                    raise ValueError(f"event references unknown cell: {cell_id}")
                previous_state = _state(row["previous_state"], field="previous_state")
                new_state = _state(row["new_state"], field="new_state")
                if states[cell_id] != previous_state:
                    raise ValueError("event previous_state does not match replay state")
                if new_state not in _ALLOWED_STORE_TRANSITIONS.get(previous_state, frozenset()):
                    raise ValueError(f"illegal event transition: {previous_state} -> {new_state}")
                states[cell_id] = new_state
                costs[cell_id] += float(row["actual_cost"])
                previous_hash = str(row["event_hash"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                event_chain_valid = False
                errors.append(f"event {expected_sequence}: {exc}")
                break

        stored_rows = {
            str(row["cell_id"]): row
            for row in connection.execute("SELECT * FROM cells ORDER BY cell_id")
        }
        if set(stored_rows) != set(states):
            cell_state_matches = False
            errors.append("stored cells do not match manifest cells")
        for cell_id in sorted(set(stored_rows) & set(states)):
            row = stored_rows[cell_id]
            if str(row["state"]) != states[cell_id]:
                cell_state_matches = False
                errors.append(f"state drift for {cell_id}")
            if abs(float(row["actual_cost"]) - costs[cell_id]) > 1e-8:
                cost_matches = False
                errors.append(f"cost drift for {cell_id}")
            state = str(row["state"])
            lease_values = (
                row["lease_owner"],
                row["lease_token"],
                row["leased_at"],
                row["lease_expires_at"],
            )
            if state == "leased" and any(value is None for value in lease_values):
                lease_invariants_valid = False
                errors.append(f"incomplete lease metadata for {cell_id}")
            if state != "leased" and any(value is not None for value in lease_values):
                lease_invariants_valid = False
                errors.append(f"stale lease metadata for {cell_id}")
        stored_cost = sum(float(row["actual_cost"]) for row in stored_rows.values())
        replayed_cost = sum(costs.values())
        valid = all(
            (
                manifest_matches,
                event_chain_valid,
                cell_state_matches,
                cost_matches,
                lease_invariants_valid,
            )
        )
        return StoreReconciliation(
            campaign_id=manifest.campaign_id,
            valid=valid,
            manifest_matches=manifest_matches,
            event_chain_valid=event_chain_valid,
            cell_state_matches=cell_state_matches,
            cost_matches=cost_matches,
            lease_invariants_valid=lease_invariants_valid,
            event_count=len(events),
            replayed_cost=round(replayed_cost, 8),
            stored_cost=round(stored_cost, 8),
            errors=tuple(errors),
        )
    finally:
        connection.close()


__all__ = [
    "StoreEvent",
    "StoreLease",
    "StoreReconciliation",
    "StoreStatus",
    "StoreTerminalState",
    "campaign_store_status",
    "complete_campaign_lease",
    "export_store_events",
    "heartbeat_campaign_lease",
    "initialise_campaign_store",
    "lease_campaign_cells",
    "read_store_events",
    "reclaim_expired_leases",
    "reconcile_campaign_store",
    "requeue_failed_cell",
]
