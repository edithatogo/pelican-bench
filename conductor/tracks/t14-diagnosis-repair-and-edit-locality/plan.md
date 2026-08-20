# Implementation plan

## Decision and review protocol

T14 has one human decision-maker: the benchmark steward (the user). Every
human-dependent choice is prepared as a redacted, hash-bound decision packet and sent to
a panel of separately run agents for independent analysis. The panel returns its findings,
options, risks, and recommendation to the benchmark steward, who makes the decision and
records the rationale. Agents may not make the final normative decision, approve a release,
or represent synthetic agent ratings as human-judgement evidence. A decision remains
pending until the steward's recorded response is attached to the packet.

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
  Route the study design, sampling, analysis, and score-compatibility options through the
  T14 agent panel; return the panel packet to the benchmark steward for the final decision.
  Agent ratings and fixture evidence do not satisfy the human-calibration requirement.

**Current limitation:** Current repair metrics are E2 artifact-edit diagnostics, not a validated visual repair score.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
