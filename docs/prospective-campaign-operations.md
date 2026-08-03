# Prospective campaign operations

## Scope

The campaign layer converts the committed prospective plan into qualification-gated, price-gated and budget-gated execution cells. It is orchestration evidence, not a claim that any provider endpoint has run.

## Campaign identity

Campaign identity includes the task commitment, model panel, stable trial cells, qualification decisions, run-date price schedules, policy and deterministic shards. Descriptive generation timestamps are excluded from identity so reconstructing the same plan later does not create a different campaign.

## Qualification and price gates

A cell can be:

- `blocked-qualification` when its model has not passed the canary;
- `blocked-price` when the policy requires a current price schedule and none is recorded;
- `ready` when both gates pass;
- `leased`, `succeeded`, `failed`, `quarantined` or `cancelled` through the append-only ledger.

Blocked cells do not disappear and do not make a campaign complete. They remain in the planned denominator and status report. A current price schedule is insufficient on its own: leasing is also blocked until an explicit hard budget is recorded.

## Sharding and leasing

Ready cells are sorted deterministically by stage, model, task and replicate. Shards never mix models or stages. Leasing enforces:

- the declared per-model concurrency limit;
- an explicit hard budget before any lease can be issued;
- hard-budget reservations using estimated cost for already leased cells;
- a single append-only, content-addressed event chain; and
- legal state transitions.

The hard-budget invariant is checked independently of the descriptive `budget_gate` field, so relabelling a manifest cannot enable leasing without a numeric limit. The event ledger is a single-writer contract. A distributed deployment must place it behind transactional storage or another serialisable coordinator; local JSONL alone is not a multi-writer lock.

## Failure retention

Every terminal failure retains its cell identity, attempts, reason and cost. A failed cell can be deliberately returned to `ready`, but the earlier failure event remains in the chain. Successful events require a result artifact digest.

## Commands

```bash
pelicanbench build-campaign-manifest --root . --output artifacts/campaign-manifest.json
pelicanbench campaign-status --manifest artifacts/campaign-manifest.json
pelicanbench lease-campaign-cells \
  --manifest artifacts/campaign-manifest.json \
  --ledger artifacts/campaign-events.jsonl \
  --worker-id worker-01 --limit 4
pelicanbench append-campaign-event \
  --manifest artifacts/campaign-manifest.json \
  --ledger artifacts/campaign-events.jsonl \
  --cell-id PCEL-example --new-state failed --reason provider-timeout
```

External execution remains blocked until model qualification, provider terms, current prices, an explicit hard budget and credentials are available. Ambiguous boolean strings in qualification or policy inputs are rejected rather than interpreted using Python truthiness.

## Transactional v0.6 reference store

The content-addressed campaign manifest can now be materialised into the SQLite reference
store described in [`transactional-campaign-store.md`](transactional-campaign-store.md).
The store is the normative single-host implementation for atomic allocation, expiry,
recovery and cost reconciliation. JSONL remains the portable event interchange.

## Immutable worker execution

The transactional worker automatically renews a live lease during a blocking model call,
retains infrastructure exceptions as charged failed attempts, and writes one immutable
record per attempt. Concurrent workers never update a shared result index. A portable
execution ledger and its reconciliation report are generated explicitly:

```bash
pelicanbench export-campaign-executions \
  --campaign-output artifacts/campaign-runs \
  --output artifacts/campaign-executions.jsonl
pelicanbench reconcile-campaign-executions \
  --manifest artifacts/campaign-manifest.json \
  --database artifacts/campaign.sqlite \
  --campaign-output artifacts/campaign-runs \
  --output artifacts/campaign-execution-reconciliation.json
```

A failed cell may be requeued, but its earlier execution record and terminal event remain
immutable and continue to count in operational failure and cost summaries.
