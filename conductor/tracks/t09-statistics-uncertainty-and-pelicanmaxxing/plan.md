# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/statistics.py`, `tests/test_statistics_semantic_human.py`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/statistics.py`, `tests/test_statistics_semantic_human.py`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Implement relation-adjusted interaction estimates and stratified bootstrap uncertainty.
- [x] Task: Implement partial pooling, replicate reliability and superiority probabilities.
- [x] Task: Prespecify the V1 pilot analysis and sensitivity analyses.
- [ ] Task: Fit and validate the models on prospective multi-model and human data.

**Current limitation:** Statistical software is E2; substantive empirical estimates do not yet exist.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
