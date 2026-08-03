# V1 pilot amendment 004: immutable worker attempts and bounded lease renewal

**Timing:** Before data  
**Task-affecting:** No  
**Candidate commitment:** Unchanged

## Change

The prospective execution protocol now requires:

- lease heartbeats that renew to a bounded horizon rather than adding a full lease duration
  cumulatively on every heartbeat;
- automatic heartbeat renewal during blocking live-provider calls;
- an immutable, content-addressed execution record for every leased attempt, including
  failed attempts later approved for retry;
- content-addressed per-worker batch receipts instead of a shared read-modify-write output
  file;
- a deterministic export built from immutable attempt records; and
- reconciliation of every worker terminal event against exactly one matching attempt record
  using cell, lease token, attempt, state, cost and artifact identity.

## Rationale

The earlier worker output index could be overwritten by concurrent workers and collapsed
multiple attempts for the same cell. Rapid heartbeat calls could also extend a lease much
farther than the intended time-to-live. Both behaviours threatened audit completeness and
recovery. The revised implementation preserves every attempt and prevents unbounded lease
extension before any prospective model run occurs.

## Analysis action

No benchmark task, score or primary estimand changes. The final study report will publish
the reconciled attempt ledger, distinguish attempts from successful cells, and include all
provider and infrastructure failures in operational denominators.
