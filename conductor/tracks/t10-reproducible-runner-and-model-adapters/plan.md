# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/runner.py`, `src/pelicanbench/adapters.py`, `src/pelicanbench/manifest.py`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/runner.py`, `src/pelicanbench/adapters.py`, `src/pelicanbench/manifest.py`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Emit stable trial and evaluation records separate from benchmark task identity.
- [x] Task: Emit canonical renders, semantic assessments, W3C PROV, RO-Crate and reproduction script.
- [x] Task: Reproduce deterministic fixture runs through the local harness.
- [x] Task: Retain failed invocations as denominator trials and export `failures.jsonl`.
- [x] Task: Add bounded retry and checkpoint adapters, with child-process secret minimisation.
- [x] Task: Add a generic OpenAI-compatible adapter for Ollama, llama.cpp, MLX and compatible gateways.
- [x] Task: Version model-specific runtime prompts independently from model eligibility.
- [x] Task: Generate a deterministic 297-cell pilot plan while retaining qualification-required cells.
- [ ] Task: Validate the policies against real provider failures and a second-environment clean-clone rerun.

**Current limitation:** Retry, resume and failure-retention contracts are E2 fixture-verified; provider and independent reproduction evidence remain open.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
