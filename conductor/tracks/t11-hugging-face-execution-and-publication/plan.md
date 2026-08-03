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

**Phase state:** `complete`
**Evidence level:** `E2` fixture-verified for local contracts

- [x] Task: Add independent, adversarial or property-oriented validation.
- [x] Task: Inventory the current first-party model namespace and record explicit inclusion or exclusion decisions.
- [x] Task: Add qualification-gated MLX and PEFT Qwen3 Hermes entries plus a versioned runtime prompt profile.
- [x] Task: Keep the strict-tool-call dataset as provenance only and firewall it from benchmark task/scorer data.
- [x] Task: Measure uncertainty, repeatability and known limitations.
- [x] Task: Reproduce through the project harness and update evidence.
- [x] Task: Phase verification and validated checkpoint.

**Current limitation:** Hub publication is prepared but the target dataset and Spaces are not remotely created through this environment. The first-party candidate adapters also require immutable revisions and valid-SVG canaries before pilot eligibility.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
