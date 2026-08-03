"""Deterministic orchestration for the prospective multi-model campaign.

The campaign layer sits above provider-specific runners. It converts a committed
prospective plan into qualification- and budget-gated cells, deterministic shards, and an
append-only execution ledger. External workers can execute shards independently while the
ledger preserves resumability, failure denominators, cost accounting, and legal state
transitions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal, Mapping, cast

from .coercion import parse_bool
from .io import content_hash
from .prospective import ProspectivePilotPlan
from .timeutil import utc_now_iso

CellState = Literal[
    "blocked-qualification",
    "blocked-price",
    "ready",
    "leased",
    "succeeded",
    "failed",
    "quarantined",
    "cancelled",
]

TERMINAL_STATES: frozenset[str] = frozenset({"succeeded", "failed", "quarantined", "cancelled"})
CELL_STATES: frozenset[str] = frozenset(
    {
        "blocked-qualification",
        "blocked-price",
        "ready",
        "leased",
        "succeeded",
        "failed",
        "quarantined",
        "cancelled",
    }
)
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "ready": frozenset({"leased", "cancelled"}),
    "leased": frozenset({"ready", "succeeded", "failed", "quarantined", "cancelled"}),
    "failed": frozenset({"ready"}),
}

_DEFAULT_PRICE_POLICY = (
    "Provider prices must be captured on the qualification date; stale hard-coded prices "
    "are not current evidence."
)
_DEFAULT_FAILURE_POLICY = (
    "Every completed attempt and terminal failure remains in the campaign ledger and "
    "benchmark denominator."
)


def _cell_state(value: Any, *, field: str) -> CellState:
    state = str(value)
    if state not in CELL_STATES:
        raise ValueError(f"{field} is not a valid campaign state: {state}")
    return cast(CellState, state)


@dataclass(frozen=True, slots=True)
class PriceSchedule:
    model_id: str
    currency: str
    input_per_million: float
    output_per_million: float
    request_fee: float = 0.0
    effective_at: str = ""
    source: str = "run-date-provider-catalogue"

    def __post_init__(self) -> None:
        values = (self.input_per_million, self.output_per_million, self.request_fee)
        if any(value < 0 for value in values):
            raise ValueError("price schedule values cannot be negative")
        if not self.currency:
            raise ValueError("price schedule currency is required")

    def estimate(self, *, input_tokens: int, output_tokens: int) -> float:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token assumptions cannot be negative")
        return (
            self.request_fee
            + input_tokens * self.input_per_million / 1_000_000
            + output_tokens * self.output_per_million / 1_000_000
        )


@dataclass(frozen=True, slots=True)
class CampaignPolicy:
    schema_version: str = "1.0.0"
    shard_size: int = 24
    max_parallel_per_model: int = 4
    default_input_tokens: int = 300
    default_output_tokens: int = 8_000
    reserve_fraction: float = 0.15
    hard_budget: float | None = None
    currency: str = "USD"
    require_price_schedule: bool = True
    require_hard_budget_before_execution: bool = True
    price_policy: str = _DEFAULT_PRICE_POLICY
    failure_policy: str = _DEFAULT_FAILURE_POLICY

    def __post_init__(self) -> None:
        if self.shard_size < 1:
            raise ValueError("shard_size must be positive")
        if self.max_parallel_per_model < 1:
            raise ValueError("max_parallel_per_model must be positive")
        if self.default_input_tokens < 0 or self.default_output_tokens < 0:
            raise ValueError("default token assumptions cannot be negative")
        if not 0 <= self.reserve_fraction <= 1:
            raise ValueError("reserve_fraction must be within [0,1]")
        if self.hard_budget is not None and self.hard_budget <= 0:
            raise ValueError("hard_budget must be positive when supplied")
        if not self.price_policy.strip() or not self.failure_policy.strip():
            raise ValueError("campaign policy explanations cannot be blank")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CampaignPolicy:
        hard_budget = value.get("hard_budget")
        return cls(
            schema_version=str(value.get("schema_version", "1.0.0")),
            shard_size=int(value.get("shard_size", 24)),
            max_parallel_per_model=int(value.get("max_parallel_per_model", 4)),
            default_input_tokens=int(value.get("default_input_tokens", 300)),
            default_output_tokens=int(value.get("default_output_tokens", 8_000)),
            reserve_fraction=float(value.get("reserve_fraction", 0.15)),
            hard_budget=None if hard_budget is None else float(hard_budget),
            currency=str(value.get("currency", "USD")),
            require_price_schedule=parse_bool(
                value.get("require_price_schedule", True), field="require_price_schedule"
            ),
            require_hard_budget_before_execution=parse_bool(
                value.get("require_hard_budget_before_execution", True),
                field="require_hard_budget_before_execution",
            ),
            price_policy=str(value.get("price_policy", _DEFAULT_PRICE_POLICY)),
            failure_policy=str(value.get("failure_policy", _DEFAULT_FAILURE_POLICY)),
        )


@dataclass(frozen=True, slots=True)
class CampaignCell:
    cell_id: str
    stage_id: str
    model_id: str
    task_id: str
    replicate: int
    seed: int
    state: CellState
    estimated_cost: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CampaignCell:
        return cls(
            cell_id=str(value["cell_id"]),
            stage_id=str(value["stage_id"]),
            model_id=str(value["model_id"]),
            task_id=str(value["task_id"]),
            replicate=int(value["replicate"]),
            seed=int(value["seed"]),
            state=_cell_state(value["state"], field="state"),
            estimated_cost=(
                None if value.get("estimated_cost") is None else float(value["estimated_cost"])
            ),
        )


@dataclass(frozen=True, slots=True)
class CampaignShard:
    shard_id: str
    stage_id: str
    model_id: str
    cell_ids: tuple[str, ...]
    estimated_cost: float
    content_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CampaignShard:
        return cls(
            shard_id=str(value["shard_id"]),
            stage_id=str(value["stage_id"]),
            model_id=str(value["model_id"]),
            cell_ids=tuple(str(item) for item in value["cell_ids"]),
            estimated_cost=float(value["estimated_cost"]),
            content_hash=str(value["content_hash"]),
        )


@dataclass(frozen=True, slots=True)
class CampaignManifest:
    schema_version: str
    generated_at: str
    campaign_id: str
    prospective_plan_hash: str
    task_identity_commitment: str
    currency: str
    hard_budget: float | None
    max_parallel_per_model: int
    policy_hash: str
    budget_gate: str
    estimated_cost: float
    estimated_cost_with_reserve: float
    unknown_cost_cells: int
    cells: tuple[CampaignCell, ...]
    shards: tuple[CampaignShard, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["cells"] = [item.as_dict() for item in self.cells]
        value["shards"] = [item.as_dict() for item in self.shards]
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CampaignManifest:
        return cls(
            schema_version=str(value["schema_version"]),
            generated_at=str(value["generated_at"]),
            campaign_id=str(value["campaign_id"]),
            prospective_plan_hash=str(value["prospective_plan_hash"]),
            task_identity_commitment=str(value["task_identity_commitment"]),
            currency=str(value["currency"]),
            hard_budget=(
                None if value.get("hard_budget") is None else float(value["hard_budget"])
            ),
            max_parallel_per_model=int(value["max_parallel_per_model"]),
            policy_hash=str(value["policy_hash"]),
            budget_gate=str(value["budget_gate"]),
            estimated_cost=float(value["estimated_cost"]),
            estimated_cost_with_reserve=float(value["estimated_cost_with_reserve"]),
            unknown_cost_cells=int(value["unknown_cost_cells"]),
            cells=tuple(CampaignCell.from_mapping(item) for item in value["cells"]),
            shards=tuple(CampaignShard.from_mapping(item) for item in value["shards"]),
        )

    def summary(self) -> dict[str, Any]:
        counts = Counter(cell.state for cell in self.cells)
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "campaign_id": self.campaign_id,
            "prospective_plan_hash": self.prospective_plan_hash,
            "task_identity_commitment": self.task_identity_commitment,
            "currency": self.currency,
            "hard_budget": self.hard_budget,
            "max_parallel_per_model": self.max_parallel_per_model,
            "policy_hash": self.policy_hash,
            "budget_gate": self.budget_gate,
            "estimated_cost": self.estimated_cost,
            "estimated_cost_with_reserve": self.estimated_cost_with_reserve,
            "unknown_cost_cells": self.unknown_cost_cells,
            "cell_count": len(self.cells),
            "state_counts": dict(sorted(counts.items())),
            "shard_count": len(self.shards),
        }


@dataclass(frozen=True, slots=True)
class CampaignEvent:
    schema_version: str
    sequence: int
    cell_id: str
    previous_state: CellState
    new_state: CellState
    reason: str
    cost: float
    artifact_id: str | None
    previous_event_hash: str | None
    event_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CampaignEvent:
        return cls(
            schema_version=str(value["schema_version"]),
            sequence=int(value["sequence"]),
            cell_id=str(value["cell_id"]),
            previous_state=_cell_state(value["previous_state"], field="previous_state"),
            new_state=_cell_state(value["new_state"], field="new_state"),
            reason=str(value["reason"]),
            cost=float(value["cost"]),
            artifact_id=(None if value.get("artifact_id") is None else str(value["artifact_id"])),
            previous_event_hash=(
                None
                if value.get("previous_event_hash") is None
                else str(value["previous_event_hash"])
            ),
            event_hash=str(value["event_hash"]),
        )


@dataclass(frozen=True, slots=True)
class CampaignStatus:
    campaign_id: str
    state_counts: dict[str, int]
    events: int
    total_cost: float
    remaining_ready: int
    terminal_cells: int
    budget_exceeded: bool
    complete: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prices_by_model(values: Iterable[PriceSchedule]) -> dict[str, PriceSchedule]:
    output: dict[str, PriceSchedule] = {}
    for item in values:
        if item.model_id in output:
            raise ValueError(f"duplicate price schedule for {item.model_id}")
        output[item.model_id] = item
    currencies = {item.currency for item in output.values()}
    if len(currencies) > 1:
        raise ValueError("a campaign requires one price currency")
    return output


def build_campaign_manifest(
    plan: ProspectivePilotPlan,
    *,
    qualified_models: Mapping[str, bool],
    prices: Iterable[PriceSchedule] = (),
    policy: CampaignPolicy | None = None,
) -> CampaignManifest:
    selected = policy or CampaignPolicy()
    price_map = _prices_by_model(prices)
    if price_map and {item.currency for item in price_map.values()} != {selected.currency}:
        raise ValueError("price schedule currency does not match campaign policy")

    cells: list[CampaignCell] = []
    for source in sorted(plan.cells, key=lambda item: (item.stage_id, item.model_id, item.task_id, item.replicate)):
        price = price_map.get(source.model_id)
        if not qualified_models.get(source.model_id, False):
            state: CellState = "blocked-qualification"
        elif selected.require_price_schedule and price is None:
            state = "blocked-price"
        else:
            state = "ready"
        estimate = (
            price.estimate(
                input_tokens=selected.default_input_tokens,
                output_tokens=selected.default_output_tokens,
            )
            if price is not None
            else None
        )
        cells.append(
            CampaignCell(
                cell_id=source.cell_id,
                stage_id=source.stage_id,
                model_id=source.model_id,
                task_id=source.task_id,
                replicate=source.replicate,
                seed=source.seed,
                state=state,
                estimated_cost=estimate,
            )
        )

    shards: list[CampaignShard] = []
    grouped: dict[tuple[str, str], list[CampaignCell]] = {}
    for cell in cells:
        if cell.state == "ready":
            grouped.setdefault((cell.stage_id, cell.model_id), []).append(cell)
    for (stage_id, model_id), group in sorted(grouped.items()):
        for offset in range(0, len(group), selected.shard_size):
            chunk = tuple(group[offset : offset + selected.shard_size])
            cell_ids = tuple(item.cell_id for item in chunk)
            shard_payload = {
                "stage_id": stage_id,
                "model_id": model_id,
                "cell_ids": cell_ids,
                "policy_hash": content_hash(asdict(selected)),
            }
            shard_hash = content_hash(shard_payload)
            shards.append(
                CampaignShard(
                    shard_id="CSHARD-" + shard_hash.split(":", 1)[1][:24],
                    stage_id=stage_id,
                    model_id=model_id,
                    cell_ids=cell_ids,
                    estimated_cost=sum(item.estimated_cost or 0.0 for item in chunk),
                    content_hash=shard_hash,
                )
            )

    known_cost = sum(item.estimated_cost or 0.0 for item in cells)
    unknown_cost_cells = sum(item.estimated_cost is None for item in cells if item.state == "ready")
    cost_with_reserve = known_cost * (1 + selected.reserve_fraction)
    if unknown_cost_cells:
        budget_gate = "blocked-unknown-prices"
    elif selected.hard_budget is not None and cost_with_reserve > selected.hard_budget:
        budget_gate = "blocked-budget-exceeded"
    elif selected.hard_budget is None and selected.require_hard_budget_before_execution:
        budget_gate = "blocked-no-hard-budget"
    elif selected.hard_budget is None:
        budget_gate = "advisory-no-hard-budget"
    else:
        budget_gate = "pass"

    policy_hash = content_hash(asdict(selected))
    plan_summary = plan.summary()
    # ``generated_at`` is descriptive provenance, not scientific identity. Excluding it
    # keeps a campaign stable when the same committed plan is reconstructed later.
    plan_summary.pop("generated_at", None)
    plan_payload = plan_summary | {"cells": [cell.as_dict() for cell in plan.cells]}
    plan_hash = content_hash(plan_payload)
    identity_payload = {
        "prospective_plan_hash": plan_hash,
        "task_identity_commitment": plan.task_identity_commitment,
        "policy_hash": policy_hash,
        "qualified_models": dict(sorted(qualified_models.items())),
        "prices": [asdict(item) for item in sorted(price_map.values(), key=lambda item: item.model_id)],
        "cells": [cell.as_dict() for cell in cells],
        "shards": [shard.as_dict() for shard in shards],
    }
    campaign_id = "PCAMP-" + content_hash(identity_payload).split(":", 1)[1][:24]
    return CampaignManifest(
        schema_version="1.0.0",
        generated_at=utc_now_iso(),
        campaign_id=campaign_id,
        prospective_plan_hash=plan_hash,
        task_identity_commitment=plan.task_identity_commitment,
        currency=selected.currency,
        hard_budget=selected.hard_budget,
        max_parallel_per_model=selected.max_parallel_per_model,
        policy_hash=policy_hash,
        budget_gate=budget_gate,
        estimated_cost=round(known_cost, 8),
        estimated_cost_with_reserve=round(cost_with_reserve, 8),
        unknown_cost_cells=unknown_cost_cells,
        cells=tuple(cells),
        shards=tuple(shards),
    )


def _initial_states(manifest: CampaignManifest) -> dict[str, CellState]:
    return {cell.cell_id: cell.state for cell in manifest.cells}


def replay_campaign_events(
    manifest: CampaignManifest,
    events: Iterable[CampaignEvent],
) -> tuple[dict[str, CellState], float]:
    states = _initial_states(manifest)
    previous_hash: str | None = None
    total_cost = 0.0
    for expected_sequence, event in enumerate(events):
        if event.sequence != expected_sequence:
            raise ValueError("campaign event sequence is not contiguous")
        if event.previous_event_hash != previous_hash:
            raise ValueError("campaign event hash chain is broken")
        if event.cell_id not in states:
            raise ValueError(f"campaign event references unknown cell: {event.cell_id}")
        current = states[event.cell_id]
        if current != event.previous_state:
            raise ValueError("campaign event previous_state does not match replay state")
        if event.new_state not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise ValueError(f"illegal campaign transition: {current} -> {event.new_state}")
        if event.cost < 0:
            raise ValueError("campaign event cost cannot be negative")
        payload = {
            "schema_version": event.schema_version,
            "sequence": event.sequence,
            "cell_id": event.cell_id,
            "previous_state": event.previous_state,
            "new_state": event.new_state,
            "reason": event.reason,
            "cost": event.cost,
            "artifact_id": event.artifact_id,
            "previous_event_hash": event.previous_event_hash,
        }
        expected_hash = content_hash(payload)
        if event.event_hash != expected_hash:
            raise ValueError("campaign event content hash does not match")
        states[event.cell_id] = event.new_state
        total_cost += event.cost
        previous_hash = event.event_hash
    return states, total_cost


def append_campaign_event(
    manifest: CampaignManifest,
    events: Iterable[CampaignEvent],
    *,
    cell_id: str,
    new_state: CellState,
    reason: str,
    cost: float = 0.0,
    artifact_id: str | None = None,
) -> tuple[CampaignEvent, ...]:
    values = tuple(events)
    states, _ = replay_campaign_events(manifest, values)
    if cell_id not in states:
        raise ValueError(f"unknown campaign cell: {cell_id}")
    previous_state = states[cell_id]
    if new_state not in _ALLOWED_TRANSITIONS.get(previous_state, frozenset()):
        raise ValueError(f"illegal campaign transition: {previous_state} -> {new_state}")
    if cost < 0:
        raise ValueError("campaign event cost cannot be negative")
    if not reason.strip():
        raise ValueError("campaign event reason is required")
    if new_state == "succeeded" and not artifact_id:
        raise ValueError("successful campaign events require an artifact_id")
    previous_hash = values[-1].event_hash if values else None
    payload = {
        "schema_version": "1.0.0",
        "sequence": len(values),
        "cell_id": cell_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "reason": reason,
        "cost": cost,
        "artifact_id": artifact_id,
        "previous_event_hash": previous_hash,
    }
    event = CampaignEvent(event_hash=content_hash(payload), **payload)
    return (*values, event)


def campaign_status(
    manifest: CampaignManifest,
    events: Iterable[CampaignEvent] = (),
    *,
    hard_budget: float | None = None,
) -> CampaignStatus:
    values = tuple(events)
    states, total_cost = replay_campaign_events(manifest, values)
    counts = Counter(states.values())
    terminal = sum(counts.get(state, 0) for state in TERMINAL_STATES)
    remaining = counts.get("ready", 0)
    selected_budget = manifest.hard_budget if hard_budget is None else hard_budget
    budget_exceeded = selected_budget is not None and total_cost > selected_budget
    blocked = counts.get("blocked-qualification", 0) + counts.get("blocked-price", 0)
    complete = (
        remaining == 0
        and counts.get("leased", 0) == 0
        and blocked == 0
        and terminal == len(states)
        and not budget_exceeded
    )
    return CampaignStatus(
        campaign_id=manifest.campaign_id,
        state_counts=dict(sorted(counts.items())),
        events=len(values),
        total_cost=round(total_cost, 8),
        remaining_ready=remaining,
        terminal_cells=terminal,
        budget_exceeded=budget_exceeded,
        complete=complete,
    )


def next_ready_cells(
    manifest: CampaignManifest,
    events: Iterable[CampaignEvent] = (),
    *,
    limit: int = 1,
    stage_id: str | None = None,
    model_id: str | None = None,
) -> tuple[CampaignCell, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")
    states, _ = replay_campaign_events(manifest, tuple(events))
    candidates = [
        cell
        for cell in manifest.cells
        if states[cell.cell_id] == "ready"
        and (stage_id is None or cell.stage_id == stage_id)
        and (model_id is None or cell.model_id == model_id)
    ]
    candidates.sort(key=lambda cell: (cell.stage_id, cell.model_id, cell.task_id, cell.replicate))
    return tuple(candidates[:limit])


def lease_ready_cells(
    manifest: CampaignManifest,
    events: Iterable[CampaignEvent] = (),
    *,
    worker_id: str,
    limit: int = 1,
    stage_id: str | None = None,
    model_id: str | None = None,
) -> tuple[tuple[CampaignEvent, ...], tuple[CampaignCell, ...]]:
    """Append deterministic lease events while enforcing concurrency and budget reserves.

    The ledger remains single-writer: callers must serialize updates to the event file or
    transactional store. The function prevents one scheduling decision from exceeding the
    declared per-model lease cap or hard-budget reservation.
    """

    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if manifest.hard_budget is None:
        raise ValueError("campaign is not executable: hard budget required")
    if manifest.budget_gate.startswith("blocked-"):
        raise ValueError(f"campaign is not executable: {manifest.budget_gate}")
    if limit < 1:
        raise ValueError("limit must be positive")
    values = tuple(events)
    states, total_cost = replay_campaign_events(manifest, values)
    by_id = {cell.cell_id: cell for cell in manifest.cells}
    active_by_model = Counter(
        by_id[cell_id].model_id for cell_id, state in states.items() if state == "leased"
    )
    reserved_cost = sum(
        by_id[cell_id].estimated_cost or 0.0
        for cell_id, state in states.items()
        if state == "leased"
    )
    candidates = next_ready_cells(
        manifest,
        values,
        limit=len(manifest.cells),
        stage_id=stage_id,
        model_id=model_id,
    )
    selected: list[CampaignCell] = []
    for cell in candidates:
        if len(selected) >= limit:
            break
        if active_by_model[cell.model_id] >= manifest.max_parallel_per_model:
            continue
        estimate = cell.estimated_cost
        if manifest.hard_budget is not None:
            if estimate is None:
                continue
            if total_cost + reserved_cost + estimate > manifest.hard_budget:
                continue
        selected.append(cell)
        active_by_model[cell.model_id] += 1
        reserved_cost += estimate or 0.0

    updated = values
    for cell in selected:
        updated = append_campaign_event(
            manifest,
            updated,
            cell_id=cell.cell_id,
            new_state="leased",
            reason=f"worker-lease:{worker_id}",
        )
    return updated, tuple(selected)


__all__ = [
    "CELL_STATES",
    "CampaignCell",
    "CampaignEvent",
    "CampaignManifest",
    "CampaignPolicy",
    "CampaignShard",
    "CampaignStatus",
    "PriceSchedule",
    "append_campaign_event",
    "build_campaign_manifest",
    "campaign_status",
    "lease_ready_cells",
    "next_ready_cells",
    "replay_campaign_events",
]
