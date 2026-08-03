from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from pelicanbench.campaign import CampaignCell, CampaignManifest
from pelicanbench.campaign_store import (
    campaign_store_status,
    complete_campaign_lease,
    export_store_events,
    heartbeat_campaign_lease,
    initialise_campaign_store,
    lease_campaign_cells,
    read_store_events,
    reclaim_expired_leases,
    reconcile_campaign_store,
    requeue_failed_cell,
)


def _manifest(*, hard_budget: float | None = 1.0, budget_gate: str = "pass") -> CampaignManifest:
    cells = tuple(
        CampaignCell(
            cell_id=f"PCEL-{index}",
            stage_id="confirmatory",
            model_id="model-a" if index < 3 else "model-b",
            task_id=f"task-{index}",
            replicate=1,
            seed=index,
            state="ready",
            estimated_cost=0.2,
        )
        for index in range(5)
    )
    return CampaignManifest(
        schema_version="1.0.0",
        generated_at="2026-08-03T00:00:00Z",
        campaign_id="PCAMP-test-store",
        prospective_plan_hash="sha256:" + "1" * 64,
        task_identity_commitment="sha256:" + "2" * 64,
        currency="USD",
        hard_budget=hard_budget,
        max_parallel_per_model=2,
        policy_hash="sha256:" + "3" * 64,
        budget_gate=budget_gate,
        estimated_cost=1.0,
        estimated_cost_with_reserve=1.0,
        unknown_cost_cells=0,
        cells=cells,
        shards=(),
    )


def test_transactional_store_leases_heartbeats_and_completes(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initial = initialise_campaign_store(database, manifest)
    assert initial.state_counts == {"ready": 5}
    assert initialise_campaign_store(database, manifest) == initial

    leases = lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        limit=5,
        lease_seconds=60,
        model_id="model-a",
        now="2026-08-03T00:00:00Z",
    )
    assert len(leases) == 2
    assert {item.model_id for item in leases} == {"model-a"}
    assert (
        campaign_store_status(database, manifest, now="2026-08-03T00:00:10Z").reserved_cost == 0.4
    )

    heartbeat = heartbeat_campaign_lease(
        database,
        manifest,
        cell_id=leases[0].cell_id,
        worker_id="worker-a",
        lease_token=leases[0].lease_token,
        extend_seconds=120,
        now="2026-08-03T00:00:30Z",
    )
    assert heartbeat.lease_expires_at == "2026-08-03T00:02:30Z"
    repeated = heartbeat_campaign_lease(
        database,
        manifest,
        cell_id=leases[0].cell_id,
        worker_id="worker-a",
        lease_token=leases[0].lease_token,
        extend_seconds=120,
        now="2026-08-03T00:00:30Z",
    )
    assert repeated.lease_expires_at == "2026-08-03T00:02:30Z"

    event = complete_campaign_lease(
        database,
        manifest,
        cell_id=heartbeat.cell_id,
        worker_id="worker-a",
        lease_token=heartbeat.lease_token,
        new_state="succeeded",
        reason="canonical-artifact-retained",
        actual_cost=0.18,
        artifact_id="sha256:" + "a" * 64,
        now="2026-08-03T00:01:00Z",
    )
    assert event.new_state == "succeeded"
    status = campaign_store_status(database, manifest, now="2026-08-03T00:01:00Z")
    assert status.spent_cost == 0.18
    assert status.reserved_cost == 0.2
    assert status.active_leases == 1
    assert reconcile_campaign_store(database, manifest).valid

    exported = export_store_events(database, tmp_path / "events.jsonl")
    assert exported.read_text(encoding="utf-8").count("\n") == 5
    assert len(read_store_events(database)) == 5


def test_expired_lease_is_reclaimed_and_cannot_complete(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    lease = lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        limit=1,
        lease_seconds=10,
        now="2026-08-03T00:00:00Z",
    )[0]
    with pytest.raises(TimeoutError, match="expired"):
        complete_campaign_lease(
            database,
            manifest,
            cell_id=lease.cell_id,
            worker_id=lease.worker_id,
            lease_token=lease.lease_token,
            new_state="failed",
            reason="late-provider-timeout",
            now="2026-08-03T00:00:11Z",
        )
    reclaimed = reclaim_expired_leases(database, manifest, now="2026-08-03T00:00:11Z")
    assert len(reclaimed) == 1
    assert reclaimed[0].new_state == "ready"
    assert (
        campaign_store_status(database, manifest, now="2026-08-03T00:00:11Z").state_counts["ready"]
        == 5
    )


def test_failed_cell_can_be_requeued_without_erasing_failure(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    lease = lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        now="2026-08-03T00:00:00Z",
    )[0]
    complete_campaign_lease(
        database,
        manifest,
        cell_id=lease.cell_id,
        worker_id=lease.worker_id,
        lease_token=lease.lease_token,
        new_state="failed",
        reason="provider-timeout",
        actual_cost=0.02,
        now="2026-08-03T00:00:05Z",
    )
    requeued = requeue_failed_cell(
        database,
        manifest,
        cell_id=lease.cell_id,
        reason="retry-approved",
        now="2026-08-03T00:00:06Z",
    )
    assert requeued.previous_state == "failed"
    assert requeued.new_state == "ready"
    events = read_store_events(database)
    assert [item.new_state for item in events] == ["leased", "failed", "ready"]
    assert campaign_store_status(database, manifest).spent_cost == 0.02


def test_store_fails_closed_for_budget_ownership_and_invalid_inputs(tmp_path: Path) -> None:
    database = tmp_path / "campaign.sqlite"
    with pytest.raises(ValueError, match="hard budget"):
        lease_campaign_cells(database, _manifest(hard_budget=None), worker_id="worker")
    with pytest.raises(ValueError, match="not executable"):
        lease_campaign_cells(
            database,
            _manifest(budget_gate="blocked-budget-exceeded"),
            worker_id="worker",
        )

    manifest = _manifest()
    initialise_campaign_store(database, manifest)
    with pytest.raises(ValueError, match="worker_id"):
        lease_campaign_cells(database, manifest, worker_id=" ")
    with pytest.raises(ValueError, match="limit"):
        lease_campaign_cells(database, manifest, worker_id="worker", limit=0)
    with pytest.raises(ValueError, match="lease_seconds"):
        lease_campaign_cells(database, manifest, worker_id="worker", lease_seconds=0)
    lease = lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        now="2026-08-03T00:00:00Z",
    )[0]
    with pytest.raises(PermissionError, match="ownership"):
        heartbeat_campaign_lease(
            database,
            manifest,
            cell_id=lease.cell_id,
            worker_id="worker-b",
            lease_token=lease.lease_token,
            now="2026-08-03T00:00:01Z",
        )
    with pytest.raises(PermissionError, match="ownership"):
        complete_campaign_lease(
            database,
            manifest,
            cell_id=lease.cell_id,
            worker_id="worker-b",
            lease_token=lease.lease_token,
            new_state="failed",
            reason="wrong-owner",
            now="2026-08-03T00:00:01Z",
        )
    with pytest.raises(ValueError, match="artifact_id"):
        complete_campaign_lease(
            database,
            manifest,
            cell_id=lease.cell_id,
            worker_id=lease.worker_id,
            lease_token=lease.lease_token,
            new_state="succeeded",
            reason="missing-artifact",
            now="2026-08-03T00:00:01Z",
        )


def test_reconciliation_detects_event_column_tampering(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        now="2026-08-03T00:00:00Z",
    )
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE events SET reason = 'tampered' WHERE sequence = 0")
        connection.commit()
    finally:
        connection.close()
    report = reconcile_campaign_store(database, manifest)
    assert not report.valid
    assert not report.event_chain_valid
    assert any("immutable payload" in error for error in report.errors)


def test_store_rejects_manifest_drift_and_supports_explicit_overwrite(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    changed = replace(manifest, campaign_id="PCAMP-different")
    with pytest.raises(ValueError, match="different campaign"):
        initialise_campaign_store(database, changed)
    overwritten = initialise_campaign_store(database, changed, overwrite=True)
    assert overwritten.campaign_id == "PCAMP-different"


def test_concurrent_leasing_is_atomic_unique_and_respects_model_caps(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)

    def lease(worker_id: str):
        return lease_campaign_cells(
            database,
            manifest,
            worker_id=worker_id,
            limit=5,
            lease_seconds=60,
            now="2026-08-03T00:00:00Z",
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        batches = tuple(executor.map(lease, ("worker-a", "worker-b", "worker-c")))

    leases = tuple(item for batch in batches for item in batch)
    assert len(leases) == 4
    assert len({item.cell_id for item in leases}) == len(leases)
    assert len({item.lease_token for item in leases}) == len(leases)
    by_model = {}
    for item in leases:
        by_model[item.model_id] = by_model.get(item.model_id, 0) + 1
    assert by_model == {"model-a": 2, "model-b": 2}
    status = campaign_store_status(database, manifest, now="2026-08-03T00:00:01Z")
    assert status.state_counts == {"leased": 4, "ready": 1}
    assert status.reserved_cost == 0.8
    assert reconcile_campaign_store(database, manifest).valid


def test_duplicate_lease_tokens_fail_atomically_without_partial_events(tmp_path: Path) -> None:
    manifest = _manifest()
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    first = lease_campaign_cells(
        database,
        manifest,
        worker_id="worker-a",
        limit=1,
        now="2026-08-03T00:00:00Z",
        token_factory=lambda: "fixed-token",
    )
    assert first[0].lease_token == "LEASE-fixed-token"

    with pytest.raises(RuntimeError, match="unique non-empty token"):
        lease_campaign_cells(
            database,
            manifest,
            worker_id="worker-b",
            limit=1,
            model_id="model-b",
            now="2026-08-03T00:00:01Z",
            token_factory=lambda: "fixed-token",
        )

    status = campaign_store_status(database, manifest, now="2026-08-03T00:00:01Z")
    assert status.state_counts == {"leased": 1, "ready": 4}
    assert status.event_count == 1
    assert reconcile_campaign_store(database, manifest).valid
