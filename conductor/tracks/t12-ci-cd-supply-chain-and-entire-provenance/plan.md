# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `.github/workflows`, `.entire`, `scripts/harness.sh`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `.github/workflows`, `.entire`, `scripts/harness.sh`.

## P2 Validated

**Phase state:** `partial`
**Evidence level:** `E2` fixture-verified

- [x] Task: Run the local unit, coverage, rights, reproducibility and deterministic SBOM harness.
- [x] Task: Add evidence-aware release-readiness and assurance-case checks.
- [x] Task: Generate and verify the 115-issue Conductor/GitHub work graph deterministically.
- [x] Task: Generate a dependency-aware SPDX SBOM and content-addressed release manifest.
- [ ] Task: Run remote GitHub CI, release attestations and Entire CLI provenance.
- [ ] Task: Verify the published release from an independent clean clone.

**Current limitation:** Configured remote workflows are not counted as executed evidence.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
