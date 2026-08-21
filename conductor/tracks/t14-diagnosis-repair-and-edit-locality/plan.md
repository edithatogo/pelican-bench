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
- [~] Task: Calibrate edit locality and introduced-defect measures against human judgement. Decision packet: `docs/t14-human-calibration-decision-packet.md`; readiness snapshot: `benchmark/evidence/snapshots/t14-calibration-pilot-readiness.json`. Pilot authorized by D039. The steward completed the two-episode rehearsal; response and non-promotional analysis receipts are `benchmark/evidence/snapshots/t14-human-rating-response.json` and `benchmark/evidence/snapshots/t14-steward-analysis.json`. Only two eligible project-original episodes are currently available, so normative calibration remains outstanding.
  Route the study design, sampling, analysis, and score-compatibility options through the
  T14 agent panel; return the panel packet to the benchmark steward for the final decision.
  Agent ratings and fixture evidence do not satisfy the human-calibration requirement.
- [x] Task: Provide a local blinded steward-rating interface over the existing manifest and response schema. Evidence: `scripts/t14_steward_app.py`, `docs/t14-steward-interface.md`. The interface is a convenience layer only; it cannot create human ratings, reveal hidden labels, or establish independent/E3 evidence.

**Current limitation:** Current repair metrics are E2 artifact-edit diagnostics, not a validated visual repair score.

## P3 Hardened

**Phase state:** `partial`

- [x] Task: Meet stable performance, fuzzing, security and supply-chain budgets. Evidence: `docs/t14-hardening.md`, `src/pelicanbench/render.py`, `src/pelicanbench/repair.py`, `src/pelicanbench/fuzzing.py`, `scripts/harness.sh`; full harness (`HARNESS_OK`). Commit: `00dd5ce`.
- [x] Task: Complete bridge, migration and deprecation policy. Evidence: `docs/t14-lifecycle.md`; `render-repair-v1` compatibility and bridge requirements. Commit: `dfc4b9c`.
- [x] Task: Validate operational ownership, incident response and archival. Evidence: `docs/t14-incident-runbook.md`, `benchmark/evidence/snapshots/t14-operations.json`; commit: `b959cb4`.
- [ ] Task: Phase verification and stable-release checkpoint. Gate intake: `docs/t14-p3-gate-intake.md`; remains blocked on additional eligible calibration episodes and a witnessed independent recovery rehearsal. The two-episode steward rehearsal is accepted as E2, non-promotional evidence only.
