from dataclasses import replace

import pytest

from pelicanbench.campaign import (
    CampaignEvent,
    CampaignManifest,
    append_campaign_event,
    campaign_status,
    lease_ready_cells,
    next_ready_cells,
    replay_campaign_events,
)
from pelicanbench.io import content_hash


def _manifest(root):
    import json

    return CampaignManifest.from_mapping(
        json.loads((root / "benchmark/fixtures/campaign/manifest.json").read_text())
    )


def test_append_replay_lease_and_completion(root):
    manifest = _manifest(root)
    assert next_ready_cells(manifest)[0].cell_id == "PCEL-fixture-001"
    events, cells = lease_ready_cells(manifest, worker_id="worker")
    assert len(cells) == 1
    events = append_campaign_event(
        manifest,
        events,
        cell_id=cells[0].cell_id,
        new_state="succeeded",
        reason="fixture-success",
        cost=0.01,
        artifact_id="sha256:" + "4" * 64,
    )
    states, cost = replay_campaign_events(manifest, events)
    assert states[cells[0].cell_id] == "succeeded"
    assert cost == 0.01
    assert campaign_status(manifest, events).complete


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"sequence": 2}, "sequence"),
        ({"previous_event_hash": "sha256:" + "0" * 64}, "hash chain"),
        ({"cell_id": "missing"}, "unknown cell"),
        ({"previous_state": "failed"}, "previous_state"),
        ({"new_state": "succeeded"}, "illegal campaign transition"),
        ({"cost": -1.0}, "cost cannot be negative"),
        ({"event_hash": "sha256:" + "0" * 64}, "content hash"),
    ],
)
def test_replay_rejects_corrupt_events(root, change, message):
    manifest = _manifest(root)
    events = append_campaign_event(
        manifest,
        (),
        cell_id="PCEL-fixture-001",
        new_state="leased",
        reason="fixture",
    )
    broken = replace(events[0], **change)
    with pytest.raises(ValueError, match=message):
        replay_campaign_events(manifest, [broken])


def test_append_and_lease_guards(root):
    manifest = _manifest(root)
    with pytest.raises(ValueError, match="unknown campaign cell"):
        append_campaign_event(manifest, (), cell_id="missing", new_state="leased", reason="x")
    with pytest.raises(ValueError, match="cost cannot be negative"):
        append_campaign_event(
            manifest, (), cell_id="PCEL-fixture-001", new_state="leased", reason="x", cost=-1
        )
    with pytest.raises(ValueError, match="reason is required"):
        append_campaign_event(
            manifest, (), cell_id="PCEL-fixture-001", new_state="leased", reason=" "
        )
    leased = append_campaign_event(
        manifest, (), cell_id="PCEL-fixture-001", new_state="leased", reason="x"
    )
    with pytest.raises(ValueError, match="artifact_id"):
        append_campaign_event(
            manifest, leased, cell_id="PCEL-fixture-001", new_state="succeeded", reason="x"
        )
    with pytest.raises(ValueError, match="worker_id"):
        lease_ready_cells(manifest, worker_id=" ")
    with pytest.raises(ValueError, match="limit"):
        next_ready_cells(manifest, limit=0)
    with pytest.raises(ValueError, match="hard budget"):
        lease_ready_cells(replace(manifest, hard_budget=None), worker_id="x")
    with pytest.raises(ValueError, match="not executable"):
        lease_ready_cells(replace(manifest, budget_gate="blocked-budget-exceeded"), worker_id="x")
    assert lease_ready_cells(replace(manifest, hard_budget=0.001), worker_id="x")[1] == ()


def test_event_mapping_and_status_budget(root):
    manifest = _manifest(root)
    payload = {
        "schema_version": "1.0.0",
        "sequence": 0,
        "cell_id": "PCEL-fixture-001",
        "previous_state": "ready",
        "new_state": "leased",
        "reason": "fixture",
        "cost": 0.0,
        "artifact_id": None,
        "previous_event_hash": None,
    }
    event = CampaignEvent.from_mapping({**payload, "event_hash": content_hash(payload)})
    assert event.as_dict()["sequence"] == 0
    assert campaign_status(manifest, [event], hard_budget=-1).budget_exceeded
