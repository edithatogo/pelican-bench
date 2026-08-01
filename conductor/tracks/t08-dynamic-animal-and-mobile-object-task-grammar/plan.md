# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/taskgen.py`, `benchmark/tasks/grammar.json`, `benchmark/tasks/public-anchor.jsonl`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/taskgen.py`, `benchmark/tasks/grammar.json`, `benchmark/tasks/public-anchor.jsonl`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Separate scenario, prompt, condition, trial and evaluation identities.
- [x] Task: Implement affordance-aware compatibility and four interface strata.
- [x] Task: Commit the 33-task prospective V1 pilot and task-set hash.
- [ ] Task: Run the pilot and estimate empirical coverage, difficulty and prompt sensitivity.

**Current limitation:** The task system is E2 fixture-verified; prospective item calibration remains open.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
