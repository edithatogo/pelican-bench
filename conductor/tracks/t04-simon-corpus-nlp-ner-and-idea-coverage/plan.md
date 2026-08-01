# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/corpus.py`, `data/fixtures/corpus.jsonl`, `docs/source-to-requirement-map.md`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/corpus.py`, `data/fixtures/corpus.jsonl`, `docs/source-to-requirement-map.md`.

## P2 Validated

**Phase state:** `blocked`

- [x] Task: Add independent, adversarial or property-oriented validation.
- [ ] Task: Measure uncertainty, repeatability and known limitations.
- [ ] Task: Reproduce through the project harness and update evidence.
- [ ] Task: Phase verification and validated checkpoint.

**Current limitation:** The full Simon Willison corpus is deliberately not mirrored until rights and ingestion decisions are settled.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
