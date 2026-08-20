# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/repair.py`, `benchmark/fixtures/repair`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/repair.py`, `benchmark/fixtures/repair`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Separate declared edit-target and preservation metrics from visual benchmark semantics.
- [x] Task: Retain deterministic repair fixtures and regression tests.
- [x] Task: Add render-based defect and preservation assessments. Evidence: `src/pelicanbench/repair.py` (`score_repair_render`, `RenderRepairScore`), regression coverage in `tests/test_longitudinal_repair_trajectory.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `c1ab131`.
- [ ] Task: Calibrate edit locality and introduced-defect measures against human judgement.

**Current limitation:** Current repair metrics are E2 artifact-edit diagnostics, not a validated visual repair score.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
