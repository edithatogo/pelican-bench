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

**Phase state:** `planned`

- [ ] Task: Add independent, adversarial or property-oriented validation.
- [ ] Task: Measure uncertainty, repeatability and known limitations.
- [ ] Task: Reproduce through the project harness and update evidence.
- [ ] Task: Phase verification and validated checkpoint.

**Current limitation:** Empirical human recruitment, ethics/consent review, and judge calibration remain future work.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
