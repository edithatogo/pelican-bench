# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `hf`, `scripts/setup_huggingface.py`, `.github/workflows/publish-hf.yml`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `hf`, `scripts/setup_huggingface.py`, `.github/workflows/publish-hf.yml`.

## P2 Validated

**Phase state:** `blocked`

- [x] Task: Add independent, adversarial or property-oriented validation.
- [ ] Task: Measure uncertainty, repeatability and known limitations.
- [ ] Task: Reproduce through the project harness and update evidence.
- [ ] Task: Phase verification and validated checkpoint.

**Current limitation:** Hub publication is prepared but the available HF Jobs write route is blocked by account credits and no local token is mounted.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
