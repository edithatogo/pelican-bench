# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `docs/history-and-prior-art.md`, `data/sources/source-registry.json`, `data/sources/rights-ledger.json`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `docs/history-and-prior-art.md`, `data/sources/source-registry.json`, `data/sources/rights-ledger.json`.

## P2 Validated

**Phase state:** `complete`

- [x] Task: Add independent, adversarial or property-oriented validation.
- [x] Task: Measure uncertainty, repeatability and known limitations.
- [x] Task: Reproduce through the project harness and update evidence.
- [x] Task: Phase verification and validated checkpoint. Evidence: `docs/history-and-prior-art.md`, `data/sources/source-registry.json`, `data/sources/rights-ledger.json`, `tests/integration/test_simon_corpus.py`, `src/pelicanbench/source_rights.py`, `tests/test_source_rights.py`, `scripts/check_rights.py`.


## P3 Hardened

**Phase state:** `partial`

- [x] Task: Meet stable performance, fuzzing, security and supply-chain budgets. Evidence: `docs/rights-audit-hardening.md`, `tests/edge/test_source_rights_limits.py`, `tests/property/test_source_rights_properties.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `b6fdc4a`.
- [x] Task: Complete bridge, migration and deprecation policy. Evidence: `docs/source-rights-lifecycle.md`, exact ledger schema enforcement in `src/pelicanbench/source_rights.py`, and migration fixtures in `tests/test_source_rights.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `6703bcd`.
- [x] Task: Validate operational ownership, incident response and archival. Evidence: `data/sources/operations-policy.json`, `docs/source-rights-incident-runbook.md`, `tests/contract/test_source_rights_operations.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `20507f4`.
- [x] Task: Review fixes. Reject symlinked parent directories as well as symlinked artifact files, with an edge regression test and full `scripts/harness.sh` (`HARNESS_OK`). Commit: `8043502`.
- [ ] Task: Phase verification and stable-release checkpoint. Partial progress recorded: explicit V1 exclusion of restricted historical bytes committed in `data/sources/rights-ledger.json` and `docs/rights-review-packet-t01-2026-08-19.md`; backup steward recorded in `data/sources/operations-policy.json`. Under D037, agent-panel analysis is preparation only and cannot close the rights gate. RB-05-C1 remains planned until every artifact has a redacted, hash-bound permission/redistribution decision; unresolved artifacts remain link-/metadata-only or quarantined.
