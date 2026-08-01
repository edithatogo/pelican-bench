# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `publications/substack`, `publications/arxiv`, `CITATION.cff`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `publications/substack`, `publications/arxiv`, `CITATION.cff`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified publication hand-off

- [x] Task: Build a deterministic rights-aware hand-off bundle with manifest and checksums.
- [x] Task: Export an exact SourceRight CSL workspace and explicit Authentext/scholarly review briefs.
- [x] Task: Add front-matter-aware Substack and template-shaped arXiv/OSF inputs.
- [x] Task: Add a placeholder-bearing Postiz distribution template with an approval-gated manual-write contract.
- [x] Task: Reproduce the publication bundle byte-for-byte through the harness.
- [ ] Task: Execute the hand-offs against installed external tools and retain their reports.
- [ ] Task: Phase verification and validated checkpoint.

**Current limitation:** The hand-off is validated locally, but external preflights and publications have not executed and results sections cannot be completed before prospective benchmark runs.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
