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

**Phase state:** `complete`

- [x] Task: Add independent, adversarial or property-oriented validation.
- [x] Task: Measure uncertainty, repeatability and known limitations.
- [x] Task: Reproduce through the project harness and update evidence.
- [x] Task: Phase verification and validated checkpoint. Evidence: `src/pelicanbench/simon_corpus.py`, `src/pelicanbench/empirical_nlp.py`, `tests/integration/test_simon_corpus.py`.


## P3 Hardened

**Phase state:** `partial`

- [x] Task: Meet stable performance, fuzzing, security and supply-chain budgets. Evidence: `docs/simon-corpus-hardening.md`, `tests/edge/test_simon_corpus_limits.py`; full `scripts/harness.sh` (`HARNESS_OK`). Commit: `0c89dcf`.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
