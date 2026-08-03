from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import pelicanbench.campaign_worker as campaign_worker
from pelicanbench.adapters import CallableAdapter, GenerationResult, ModelAdapter
from pelicanbench.campaign import CampaignCell, CampaignManifest
from pelicanbench.campaign_store import (
    StoreEvent,
    StoreLease,
    campaign_store_status,
    initialise_campaign_store,
    requeue_failed_cell,
)
from pelicanbench.campaign_worker import (
    execute_campaign_batch,
    export_campaign_execution_index,
    read_campaign_execution_records,
    reconcile_campaign_execution_records,
)
from pelicanbench.taskgen import heritage_task


class _CostAdapter(ModelAdapter):
    adapter_id = "cost-adapter"
    model_id = "fixture/model"
    model_revision = "r1"

    def __init__(self, svg: str, *, cost: float = 0.03) -> None:
        self.svg = svg
        self.cost = cost

    def generate(self, task, *, seed: int) -> GenerationResult:
        return GenerationResult(
            task_id=task.task_id,
            output=self.svg,
            media_type="image/svg+xml",
            raw_response=self.svg,
            metadata={"seed": seed, "usage": {"cost_usd": self.cost}},
        )


def _manifest(task_id: str, *, count: int = 2) -> CampaignManifest:
    return CampaignManifest(
        schema_version="1.0.0",
        generated_at="2026-08-03T00:00:00Z",
        campaign_id="PCAMP-worker",
        prospective_plan_hash="sha256:" + "1" * 64,
        task_identity_commitment="sha256:" + "2" * 64,
        currency="USD",
        hard_budget=1.0,
        max_parallel_per_model=2,
        policy_hash="sha256:" + "3" * 64,
        budget_gate="pass",
        estimated_cost=0.2 * count,
        estimated_cost_with_reserve=0.2 * count,
        unknown_cost_cells=0,
        cells=tuple(
            CampaignCell(
                cell_id=f"PCEL-worker-{index}",
                stage_id="confirmatory",
                model_id="fixture/model",
                task_id=task_id,
                replicate=index + 1,
                seed=100 + index,
                state="ready",
                estimated_cost=0.2,
            )
            for index in range(count)
        ),
        shards=(),
    )


@pytest.mark.integration
def test_campaign_worker_executes_and_accounts_for_success(tmp_path: Path, valid_svg: str) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)

    first = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-a",
        output_directory=tmp_path / "runs",
        limit=1,
        now="2026-08-03T00:00:00Z",
    )
    assert first.leased_cells == 1
    assert first.succeeded == 1
    assert first.failed == first.quarantined == 0
    assert first.charged_cost == pytest.approx(0.03)
    record = first.records[0]
    assert record.cost_basis == "adapter-reported"
    assert record.artifact_id and record.record_hash.startswith("sha256:")
    assert (tmp_path / "runs" / record.output_directory / "run-manifest.json").exists()
    records_directory = tmp_path / "runs" / "execution-records" / record.cell_id
    assert len(tuple(records_directory.glob("*.json"))) == 1

    second = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-b",
        output_directory=tmp_path / "runs",
        limit=2,
        now="2026-08-03T00:01:00Z",
    )
    assert second.leased_cells == 1
    status = campaign_store_status(database, manifest)
    assert status.complete
    assert status.state_counts == {"succeeded": 2}
    assert status.spent_cost == pytest.approx(0.06)
    index = export_campaign_execution_index(
        tmp_path / "runs", tmp_path / "runs" / "campaign-executions.jsonl"
    )
    assert index.read_text(encoding="utf-8").count("\n") == 2
    assert len(read_campaign_execution_records(tmp_path / "runs")) == 2
    reconciliation = reconcile_campaign_execution_records(database, manifest, tmp_path / "runs")
    assert reconciliation.valid
    assert reconciliation.matched_records == 2


@pytest.mark.integration
def test_campaign_worker_quarantines_unsafe_artifact_and_uses_reserved_cost(
    tmp_path: Path,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    unsafe = "<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        CallableAdapter(
            lambda _task, _seed: unsafe,
            model_id="fixture/model",
            model_revision="r1",
        ),
        worker_id="worker-a",
        output_directory=tmp_path / "runs",
        now="2026-08-03T00:00:00Z",
    )
    assert result.quarantined == 1
    assert result.records[0].cost_basis == "reserved-estimate"
    assert result.records[0].charged_cost == pytest.approx(0.2)
    assert campaign_store_status(database, manifest).state_counts == {"quarantined": 1}


@pytest.mark.integration
def test_campaign_worker_retains_generation_failure_and_missing_task(
    tmp_path: Path,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)

    def fail(_task, _seed):
        raise TimeoutError("provider timeout")

    failed = execute_campaign_batch(
        database,
        manifest,
        [task],
        CallableAdapter(
            fail,
            model_id="fixture/model",
            model_revision="r1",
        ),
        worker_id="worker-a",
        output_directory=tmp_path / "runs",
        limit=1,
        now="2026-08-03T00:00:00Z",
    )
    assert failed.failed == 1
    assert failed.records[0].error_type == "TimeoutError"
    assert failed.records[0].charged_cost == pytest.approx(0.2)

    missing = execute_campaign_batch(
        database,
        manifest,
        [],
        CallableAdapter(
            lambda _task, _seed: "<svg/>",
            model_id="fixture/model",
            model_revision="r1",
        ),
        worker_id="worker-b",
        output_directory=tmp_path / "runs",
        limit=1,
        now="2026-08-03T00:01:00Z",
    )
    assert missing.failed == 1
    assert missing.records[0].error_type == "KeyError"
    assert campaign_store_status(database, manifest).state_counts == {"failed": 2}


@pytest.mark.edge
def test_campaign_worker_rejects_invalid_cost_and_worker(tmp_path: Path, valid_svg: str) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    with pytest.raises(ValueError, match="worker_id"):
        execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id=" ",
            output_directory=tmp_path / "runs",
        )
    with pytest.raises(ValueError, match="limit"):
        execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id="worker",
            output_directory=tmp_path / "runs",
            limit=0,
        )
    with pytest.raises(ValueError, match="cannot be negative"):
        execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id="worker",
            output_directory=tmp_path / "runs",
            heartbeat_interval_seconds=-0.1,
        )
    with pytest.raises(ValueError, match="fixed deterministic time"):
        execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id="worker",
            output_directory=tmp_path / "runs",
            now="2026-08-03T00:00:00Z",
            heartbeat_interval_seconds=0.1,
        )
    with pytest.raises(ValueError, match="shorter than the lease"):
        execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id="worker",
            output_directory=tmp_path / "runs",
            lease_seconds=1,
            heartbeat_interval_seconds=1.0,
        )
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg, cost=-1.0),
        worker_id="worker",
        output_directory=tmp_path / "runs",
    )
    assert result.records[0].cost_basis == "invalid-reported-cost-fallback"
    assert result.records[0].charged_cost == pytest.approx(0.2)


@pytest.mark.parametrize("cost", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.edge
def test_campaign_worker_rejects_nonfinite_reported_costs(
    tmp_path: Path,
    valid_svg: str,
    cost: float,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg, cost=cost),
        worker_id="worker",
        output_directory=tmp_path / "runs",
        now="2026-08-03T00:00:00Z",
    )
    assert result.records[0].cost_basis == "invalid-reported-cost-fallback"
    assert result.records[0].charged_cost == pytest.approx(0.2)


class _SlowAdapter(_CostAdapter):
    def __init__(self, svg: str, *, delay_seconds: float) -> None:
        super().__init__(svg)
        self.delay_seconds = delay_seconds

    def generate(self, task, *, seed: int) -> GenerationResult:
        time.sleep(self.delay_seconds)
        return super().generate(task, seed=seed)


@pytest.mark.integration
def test_campaign_worker_renews_live_lease_during_blocking_generation(
    tmp_path: Path,
    valid_svg: str,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)

    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _SlowAdapter(valid_svg, delay_seconds=1.15),
        worker_id="worker-heartbeat",
        output_directory=tmp_path / "runs",
        lease_seconds=1,
        heartbeat_interval_seconds=0.1,
    )

    assert result.succeeded == 1
    assert result.heartbeat_count >= 1
    assert result.heartbeat_failures == 0
    assert result.records[0].heartbeat_count >= 1
    assert campaign_store_status(database, manifest).complete


@pytest.mark.integration
def test_campaign_worker_preserves_every_retry_attempt(
    tmp_path: Path,
    valid_svg: str,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    output = tmp_path / "runs"
    initialise_campaign_store(database, manifest)

    def fail(_task, _seed):
        raise TimeoutError("first attempt")

    first = execute_campaign_batch(
        database,
        manifest,
        [task],
        CallableAdapter(fail, model_id="fixture/model", model_revision="r1"),
        worker_id="worker-first",
        output_directory=output,
        now="2026-08-03T00:00:00Z",
    )
    assert first.failed == 1
    requeue_failed_cell(
        database,
        manifest,
        cell_id=first.records[0].cell_id,
        reason="retry-approved",
        now="2026-08-03T00:00:01Z",
    )
    second = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-second",
        output_directory=output,
        now="2026-08-03T00:00:02Z",
    )

    assert second.succeeded == 1
    records = read_campaign_execution_records(output)
    assert [item["attempt"] for item in records] == [1, 2]
    assert [item["terminal_state"] for item in records] == ["failed", "succeeded"]
    assert len(tuple((output / "worker-batches").glob("*/*.json"))) == 2


@pytest.mark.integration
def test_concurrent_workers_write_disjoint_immutable_records(
    tmp_path: Path,
    valid_svg: str,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=2)
    database = tmp_path / "campaign.sqlite"
    output = tmp_path / "runs"
    initialise_campaign_store(database, manifest)

    def run(worker_id: str):
        return execute_campaign_batch(
            database,
            manifest,
            [task],
            _CostAdapter(valid_svg),
            worker_id=worker_id,
            output_directory=output,
            limit=1,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(run, ("worker-a", "worker-b")))

    assert sum(item.succeeded for item in results) == 2
    records = read_campaign_execution_records(output)
    assert len(records) == 2
    assert len({item["cell_id"] for item in records}) == 2
    assert len({item["record_hash"] for item in records}) == 2
    assert campaign_store_status(database, manifest).complete


@pytest.mark.integration
def test_worker_infrastructure_exception_resolves_lease(
    tmp_path: Path,
    valid_svg: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    initialise_campaign_store(database, manifest)

    def crash(*_args, **_kwargs):
        raise OSError("output filesystem unavailable")

    monkeypatch.setattr("pelicanbench.campaign_worker.run_benchmark", crash)
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-crash",
        output_directory=tmp_path / "runs",
        now="2026-08-03T00:00:00Z",
    )

    assert result.failed == 1
    assert result.records[0].terminal_reason == "worker-infrastructure-failure"
    assert result.records[0].error_type == "OSError"
    assert result.records[0].cost_basis == "worker-exception-conservative-estimate"
    assert campaign_store_status(database, manifest).state_counts == {"failed": 1}


@pytest.mark.edge
def test_campaign_record_reader_detects_tampering(tmp_path: Path, valid_svg: str) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    output = tmp_path / "runs"
    initialise_campaign_store(database, manifest)
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-a",
        output_directory=output,
        now="2026-08-03T00:00:00Z",
    )
    record_path = next((output / "execution-records" / result.records[0].cell_id).glob("*.json"))
    record_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        read_campaign_execution_records(output)


@pytest.mark.edge
def test_campaign_execution_reconciliation_detects_missing_record(
    tmp_path: Path,
    valid_svg: str,
) -> None:
    task = heritage_task()
    manifest = _manifest(task.task_id, count=1)
    database = tmp_path / "campaign.sqlite"
    output = tmp_path / "runs"
    initialise_campaign_store(database, manifest)
    result = execute_campaign_batch(
        database,
        manifest,
        [task],
        _CostAdapter(valid_svg),
        worker_id="worker-a",
        output_directory=output,
        now="2026-08-03T00:00:00Z",
    )
    record_path = next((output / "execution-records" / result.records[0].cell_id).glob("*.json"))
    record_path.unlink()

    reconciliation = reconcile_campaign_execution_records(database, manifest, output)
    assert not reconciliation.valid
    assert reconciliation.terminal_events == 1
    assert reconciliation.execution_records == 0
    assert "terminal event has no execution record" in reconciliation.errors[0]


def _event(
    *,
    sequence: int,
    cell_id: str,
    lease_token: str | None,
    attempt: int = 1,
    actual_cost: float = 0.2,
    artifact_id: str | None = None,
) -> StoreEvent:
    return StoreEvent(
        schema_version="1.0.0",
        sequence=sequence,
        event_id=f"event-{sequence}",
        campaign_id="PCAMP-worker",
        cell_id=cell_id,
        previous_state="leased",
        new_state="succeeded",
        occurred_at="2026-08-03T00:00:00Z",
        worker_id="worker",
        lease_token=lease_token,
        attempt=attempt,
        reason="canonical-artifact-retained",
        estimated_cost=0.2,
        actual_cost=actual_cost,
        artifact_id=artifact_id,
        previous_event_hash=None,
        event_hash="sha256:" + f"{sequence:064x}",
    )


@pytest.mark.edge
def test_campaign_execution_reconciliation_reports_corrupt_identity_and_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("task-a", count=1)
    events = (
        _event(sequence=1, cell_id="cell-a", lease_token="token-a"),
        _event(sequence=2, cell_id="cell-a", lease_token="token-a"),
        _event(sequence=3, cell_id="cell-no-token", lease_token=None),
        _event(sequence=4, cell_id="cell-cost", lease_token="token-cost"),
    )
    records = (
        {
            "campaign_id": "wrong-campaign",
            "cell_id": "cell-a",
            "worker_id": "wrong-worker",
            "lease_token": "token-a",
            "attempt": 1,
            "terminal_state": "failed",
            "terminal_reason": "wrong-reason",
            "artifact_id": None,
            "charged_cost": "not-a-number",
            "record_hash": "sha256:" + "1" * 64,
        },
        {
            "campaign_id": "PCAMP-worker",
            "cell_id": "cell-a",
            "worker_id": "worker",
            "lease_token": "token-a",
            "attempt": 1,
            "terminal_state": "succeeded",
            "terminal_reason": "canonical-artifact-retained",
            "artifact_id": None,
            "charged_cost": 0.2,
            "record_hash": "sha256:" + "2" * 64,
        },
        {"cell_id": "malformed"},
        {
            "campaign_id": "PCAMP-worker",
            "cell_id": "cell-orphan",
            "worker_id": "worker",
            "lease_token": "token-orphan",
            "attempt": 1,
            "terminal_state": "succeeded",
            "terminal_reason": "canonical-artifact-retained",
            "artifact_id": None,
            "charged_cost": 0.2,
            "record_hash": "sha256:" + "3" * 64,
        },
        {
            "campaign_id": "PCAMP-worker",
            "cell_id": "cell-cost",
            "worker_id": "worker",
            "lease_token": "token-cost",
            "attempt": 1,
            "terminal_state": "succeeded",
            "terminal_reason": "canonical-artifact-retained",
            "artifact_id": None,
            "charged_cost": 0.3,
            "record_hash": "sha256:" + "4" * 64,
        },
    )
    monkeypatch.setattr(campaign_worker, "read_store_events", lambda _database: events)
    monkeypatch.setattr(
        campaign_worker,
        "read_campaign_execution_records",
        lambda _root: records,
    )

    report = reconcile_campaign_execution_records(
        tmp_path / "campaign.sqlite", manifest, tmp_path / "runs"
    )
    assert not report.valid
    assert report.matched_records == 2
    assert isinstance(report.as_dict()["errors"], list)
    combined = "\n".join(report.errors)
    assert "duplicate terminal event key" in combined
    assert "no lease token" in combined
    assert "duplicate execution record key" in combined
    assert "malformed execution record identity" in combined
    assert "execution record has no terminal event" in combined
    assert "execution record field mismatch" in combined
    assert "invalid charged_cost" in combined
    assert "cost mismatch" in combined


@pytest.mark.edge
def test_campaign_execution_record_io_is_immutable_and_typed(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    assert campaign_worker._write_immutable_json(target, {"value": 1}) == target
    assert campaign_worker._write_immutable_json(target, {"value": 1}) == target
    with pytest.raises(ValueError, match="immutable campaign record collision"):
        campaign_worker._write_immutable_json(target, {"value": 2})

    invalid = tmp_path / "records" / "execution-records" / "cell" / "record.json"
    invalid.parent.mkdir(parents=True)
    invalid.write_text(json.dumps(["not", "an", "object"]) + "\n", encoding="utf-8")
    with pytest.raises(TypeError, match="must be an object"):
        read_campaign_execution_records(tmp_path / "records")


@pytest.mark.edge
def test_campaign_worker_internal_boundary_helpers() -> None:
    lease = StoreLease(
        cell_id="cell-a",
        stage_id="stage-a",
        model_id="fixture/model",
        task_id="task-a",
        replicate=1,
        seed=1,
        worker_id="worker",
        lease_token="LEASE-token",
        leased_at="2026-08-03T00:00:00Z",
        lease_expires_at="2026-08-03T00:01:00Z",
        attempt=1,
        estimated_cost=0.2,
    )
    empty_result = SimpleNamespace(failures=(), trials=(), scorecards=())
    assert campaign_worker._terminal_outcome(empty_result) == (
        "failed",
        "runner-produced-no-outcome",
        "RuntimeError",
        "missing run outcome",
    )
    assert campaign_worker._cost_for_result(lease, empty_result) == (
        0.2,
        "reserved-estimate",
    )
    assert campaign_worker._reported_cost({"cost": "invalid"}) is None
    assert campaign_worker._reported_cost({"cost": True}) is None
    assert campaign_worker._safe_identifier("") == "cell"
