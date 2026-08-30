# Implementation plan

## Decision and review protocol

T14 retains the benchmark steward (the user) as decision-maker, not as a required rater.
The user's later instruction removes personal ratings from the forward plan; historical
decisions and evidence remain intact. Role-separated agents prepare options and synthetic
advice, which is non-independent and non-normative. They cannot supply human ratings,
make final normative decisions or approve release. Repository PR and merge authority does
not authorize a new freeze, public interface exposure, participant collection, analysis,
unblinding, promotion, attestation or publication. Exact scientific and disclosure decisions
remain separately gated. Do not transfer historical sole-steward authority to participants.

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
- [~] Task: Calibrate edit locality and introduced-defect measures against human judgement. Decision packet: `docs/t14-human-calibration-decision-packet.md`; readiness snapshot: `benchmark/evidence/snapshots/t14-calibration-pilot-readiness.json`. Pilot authorized by D039. The steward's two-episode rehearsal is retained as E2, non-promotional evidence; response and analysis receipts are `benchmark/evidence/snapshots/t14-human-rating-response.json` and `benchmark/evidence/snapshots/t14-steward-analysis.json`. D042 reopened repository-owned preparation and approved redesign of the 96-episode package as 24 four-episode scene clusters with an 18/6 cluster split, crossed severity and visibly distinct geometry, plus a separate 40-case non-normative diagnostic suite. D044 subsequently froze the regenerated exact bytes as procedural, non-independent E2 preparation. No new ratings, promotion, independent validation, attestation, release, publication, or unblinding are authorized, so empirical calibration remains outstanding.
  Route the study design, sampling, analysis, and score-compatibility options through the
  T14 agent panel; return the panel packet to the benchmark steward for the final decision.
  Agent ratings and fixture evidence do not satisfy the human-calibration requirement.
  The exact-clean-commit local harness observation for `ca6882a` is retained at
  `benchmark/evidence/advisory/t14/exact-commit-local-harness-receipt.json`; it is E2 local
  evidence only and has no custody, freeze, hosted-CI, attestation, or release effect.
- [x] Task: Provide a fail-closed custodian handoff that generates secret-bound alias,
  duplicate-schedule, and receipt artifacts only after an accountable acknowledgement,
  outside the repository, without recording the secret or exercising any gate. Evidence:
  `src/pelicanbench/t14_custody.py`, `scripts/prepare_t14_custody_artifacts.py`,
  `tests/test_t14_custody.py`, `tests/e2e/test_t14_custody_cli.py`, and
  `docs/t14-custodian-handoff.md`. Commit: `caca4f5`.
- [x] Task: Bind D043 procedural self-custody inputs and obtain role-separated synthetic
  design, statistics, and governance advice. The panel is advisory, non-human,
  non-independent, and non-normative. Evidence:
  `benchmark/evidence/advisory/t14/procedural-panel-design.json`,
  `benchmark/evidence/advisory/t14/procedural-panel-statistics.json`, and
  `benchmark/evidence/advisory/t14/procedural-panel-governance.json`.
  At panel completion, freeze and every downstream gate remained pending. Commit: `88142cd`.
- [x] Task: Record D044 exact-hash freeze as procedural, non-independent E2 preparation.
  Evidence: `benchmark/evidence/advisory/t14/procedural-freeze-decision-receipt.json` and
  `benchmark/evidence/advisory/t14/pending-freeze-decision.json`. Ratings, promotion,
  attestation, release, publication, and unblinding remain unauthorized. Commit: `6ecd9e7`.
- [x] Task: Document the non-mutating freeze-integrity recheck and fail-closed amendment
  procedure. Evidence: `docs/t14-freeze-integrity-and-amendment.md`. The procedure cannot
  authorize ratings or any downstream gate. Commit: `a07d85b`.
- [x] Review Fixes: Resolve candidate asset paths and prove containment within the candidate
  root before inspection or rendering; add traversal regression coverage. Commit: `7150a75`.
- [x] Review Fixes: Prove target-specific geometry for both move-repair families without
  changing candidate assets or the proposed allocation. Displaced rear wheels must align
  with the front wheel after repair; foot endpoints must move closer to an unchanged pedal.
  Evidence: `scripts/validate_t14_candidate_episodes.py`,
  `tests/contract/test_t14_candidate_package.py`. Commit: `de9a13d`.
- [x] Review Fixes: Apply the repository formatter to the pending-freeze validator after the
  full harness rejected its initial layout. Focused validator, contract test, Ruff check,
  and Ruff format check pass. Commit: `ea5b6d4`.
- [x] Review Fixes: Reconcile public custody state, prove four held-out duplicates against
  the minimum of three, enforce exact custody and verification semantics, harden restricted
  directory permissions, and add negative anti-rebinding tests. Commits: `fddb76d`,
  `df4ea22`, `3cbe425`, `9f70877`.
- [x] Review Fixes: Scope the secret-scanner exception to the exact historical fingerprint of
  the public one-way custody commitment. The custody secret remains absent and no pattern-wide
  exception is permitted. Commit: `4699364`.
- [x] Review Fixes: Baseline four reviewed Bandit findings without changing provenance-bound
  source bytes, and make Vale enforcement independent of GitHub's 300-file pull-request diff
  API limit. New security findings remain fail-closed.
  Commit: `f942352`.
- [x] Review Fixes: Add malformed permission, authority-route, rating-field, unknown-assignment,
  and ledger-tamper coverage for the authorization-gated frozen rating workflow after the full
  harness exposed a 89.80 percent aggregate coverage regression. Commit: `6bcf57b`.
- [x] Task: Provide a local blinded steward-rating interface over the existing manifest and response schema. Evidence: `scripts/t14_steward_app.py`, `docs/t14-steward-interface.md`. The interface is a convenience layer only; it cannot create human ratings, reveal hidden labels, or establish independent/E3 evidence.
- [x] Task: Prepare the authorization-gated frozen rating interface, assignment-only response
  validator, hash-chained external ledger, and inactive post-freeze runbooks. Validation-only
  mode confirms 96 source episodes, 106 assignments, and 10 duplicates without exposing the
  restricted maps or starting ratings. Evidence: `src/pelicanbench/t14_rating.py`,
  `scripts/t14_frozen_steward_app.py`, `tests/test_t14_rating.py`,
  `docs/t14-post-freeze-runbooks.md`. Commit: `d3a12e1`.

**Current limitation:** Current repair metrics are E2 artifact-edit diagnostics, not a validated visual repair score.

## P3 Hardened

**Phase state:** `partial`

- [~] Deliver test-only synthetic storage and allocation contract experiments without
  exposing the separately retained interface or diagnostic results. Evidence:
  `docs/t14-synthetic-contract-tests.md`, `tests/contract/t14_storage_fixture.py`,
  `tests/contract/test_t14_storage_fixture.py`, `tests/contract/t14_allocation_fixture.py`,
  `tests/contract/test_t14_allocation_fixture.py`. Exact-head hosted validation is pending.

- [x] Task: Meet stable performance, fuzzing, security and supply-chain budgets. Evidence: `docs/t14-hardening.md`, `src/pelicanbench/render.py`, `src/pelicanbench/repair.py`, `src/pelicanbench/fuzzing.py`, `scripts/harness.sh`; full harness (`HARNESS_OK`). Commit: `00dd5ce`.
- [x] Task: Complete bridge, migration and deprecation policy. Evidence: `docs/t14-lifecycle.md`; `render-repair-v1` compatibility and bridge requirements. Commit: `dfc4b9c`.
- [x] Task: Validate operational ownership, incident response and archival. Evidence: `docs/t14-incident-runbook.md`, `benchmark/evidence/snapshots/t14-operations.json`; commit: `b959cb4`.
- [ ] Task: Phase verification and stable-release checkpoint. Gate intake: `docs/t14-p3-gate-intake.md`; remains blocked on additional eligible calibration episodes and a witnessed independent recovery rehearsal. The two-episode steward rehearsal is accepted as E2, non-promotional evidence only.

### Later roadmap

- [ ] Reopen the steward-rating and decision packet after the agent panel has prepared and
  validated the prespecified 72/24 sample. Only the benchmark steward may submit the
  hash-bound human ratings and make the normative/release decision; agent outputs cannot
  satisfy that gate.
