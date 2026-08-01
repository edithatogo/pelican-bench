# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/semantic.py`, `src/pelicanbench/human_eval.py`, `docs/human-evaluation-protocol.md`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/semantic.py`, `src/pelicanbench/human_eval.py`, `docs/human-evaluation-protocol.md`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Define source-independent atomic visual questions and render-bound assessment records.
- [x] Task: Add fixture assessor, judge aggregation and calibration-error tests.
- [x] Task: Implement deterministic stratified calibration sampling and within-task blinded pair generation.
- [ ] Task: Complete participant governance, recruit and evaluate the prespecified sample.
- [ ] Task: Estimate judge-family, rater and task effects with uncertainty.

**Current limitation:** Calibration design is E2 fixture-verified; no empirical human-validity claim is made before governance, recruitment and analysis.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
