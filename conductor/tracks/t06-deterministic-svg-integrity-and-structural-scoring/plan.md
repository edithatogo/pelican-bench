# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/svg.py`, `src/pelicanbench/scoring.py`, `benchmark/fixtures/svg`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `src/pelicanbench/svg.py`, `src/pelicanbench/scoring.py`, `benchmark/fixtures/svg`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Remove IDs, classes, comments and hidden elements from normative semantic evidence.
- [x] Task: Bind semantic assessments to a canonical pixel-derived render hash.
- [x] Task: Add regression tests for label injection, invisible elements and metadata renaming.
- [x] Task: Verify canonical CairoSVG and Inkscape renders on an opaque, aspect-preserving canvas.
- [x] Task: Run the five normative metamorphic scorer challenges in the harness.
- [ ] Task: Complete rendered prompt-injection, human-calibration and independent challenge studies.

**Current limitation:** The critical label-injection exploit and renderer bridge are fixed at E2. E3 construct validation and an independent scorer challenge remain open.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
