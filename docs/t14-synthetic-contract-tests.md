# T14 synthetic contract tests

This repository change contains test-only code, not a participant service, public study
interface, benchmark result release or a new frozen sample. The benchmark steward is the
decision-maker, not a required rater. Synthetic advisory work is non-independent and cannot
replace human calibration or independent reproduction.

## Scope

The helpers live under `tests/contract`, outside the shipped Python package. They do not
read frozen assets, custody maps, human responses or real participant identities. There
is no network, deployment, enrollment interface or billing integration.

- `t14_storage_fixture.py` models a closed two-participant toy SQLite store. Tests exercise
  live toy authorization, participant separation, transactional idempotency, conflicting
  retries, caps, locks, simulated disk failure, lost acknowledgement and response snapshot
  recovery. Current control state remains separate from response snapshots.
- `t14_allocation_fixture.py` models twelve toy participants, 24 toy scenes and four toy
  variants. Nonzero GF(4) multipliers balance variants within participants and coverage
  across participant groups. Constructive insertion separates two repeats from their
  origins by at least eight intervening presentations. Dropout checks retain zero cells.

This is a code-only delivery slice. A separate local preparation branch retains interface
mock files, diagnostic receipts and prospective decision packets. They are not included
here because repository delivery authority does not waive their disclosure or scientific
approval gates. No hidden or restricted contents are needed to run these tests.

## Limits

Toy credentials are not authentication; fixed version labels are not exact-hash consent.
Withdrawal denies later access but does not erase data. Response-only snapshot recovery
does not prove whole-system disaster recovery or production backup/key handling. Injected
failures are not physical disk or process-crash experiments.

Balanced allocation proves combinatorial feasibility, not statistical power, independent
ratings or representative sampling. Constructive ordering is not uniform randomization or
proof that repeats remain concealed. Toy variants are not actual severity labels. No real
assignment schedule, production seed or new normative sample is selected.

## Verification

```bash
python -m pytest -q tests/contract/test_t14_storage_fixture.py tests/contract/test_t14_allocation_fixture.py
```

The complete repository gate remains `bash scripts/harness.sh`. Focused test success is
not a replacement for that gate. Hosted CI is separate evidence and must be read back at
the exact PR head before merge. Local and hosted failures must remain visible; do not
disable assertions, coverage, randomization or timeout limits to get a passing result.

Human participation, new freeze/custody, public interface exposure, collection, analysis,
unblinding, promotion, attestation and release/publication remain separately governed.
No new authority for those actions follows from merging these test helpers.
