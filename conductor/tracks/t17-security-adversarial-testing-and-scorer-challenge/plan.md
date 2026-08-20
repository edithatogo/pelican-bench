# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/svg.py`, `benchmark/fixtures/malicious`, `docs/threat-model.md`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/svg.py`, `benchmark/fixtures/malicious`, `docs/threat-model.md`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Register the source-label injection exploit and retain a malicious fixture.
- [x] Task: Add metamorphic regression tests and render/source disagreement checks.
- [x] Task: Execute five normative scorer challenges against metadata and invisible-element attacks.
- [x] Task: Add a bounded deterministic parser/renderer mutation-fuzz campaign to local and security CI.
- [x] Task: Add continuous coverage-guided parser and transform fuzzing with sustained resource budgets. Evidence: `src/pelicanbench/fuzzing.py` (`run_coverage_guided_svg_fuzz_campaign`, stdlib `trace`-guided), regression coverage in `tests/test_fuzzing.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `2d22469`.
- [ ] Task: Run rendered prompt-injection studies and an independent scorer challenge.

**Current limitation:** Known exploit protection and bounded fuzz smoke are E2; coverage-guided and independent adversarial validation remain open.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
