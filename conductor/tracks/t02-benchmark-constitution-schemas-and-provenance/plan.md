# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/models.py`, `benchmark/schemas`, `src/pelicanbench/manifest.py`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/models.py`, `benchmark/schemas`, `src/pelicanbench/manifest.py`.

## P2 Validated

**Phase state:** `complete`

- [x] Task: Add independent, adversarial or property-oriented validation.
- [x] Task: Measure uncertainty, repeatability and known limitations.
- [x] Task: Reproduce through the project harness and update evidence.
- [x] Task: Emit a `repository-standards` v1 verification receipt and validate it against the pinned external schema.
- [x] Task: Define a portable complete-release QA receipt and generated JSON Schema.
- [x] Task: Phase verification and validated checkpoint. Evidence: `src/pelicanbench/models.py`, `benchmark/schemas`, `src/pelicanbench/manifest.py`.

## P3 Hardened

**Phase state:** `partial`

- [x] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [x] Task: Complete bridge, migration and deprecation policy.
- [x] Task: Validate operational ownership, incident response and archival. Evidence: `benchmark/evidence/snapshots/contract-operations.json`, `docs/contract-operations-runbook.md`, `tests/contract/test_contract_operations.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `3782500`.
- [ ] Task: Phase verification and stable-release checkpoint. Blocked on appointment of a backup contract steward and an independently executed archive-recovery rehearsal against a tagged release.
