# Implementation plan

## P0 Contract

**Phase state:** `complete`

- [x] Task: Define scope, MoSCoW requirements and acceptance criteria.
- [x] Task: Record architecture, dependencies, risks and score-compatibility class.
- [x] Task: Create remote-ready parent and phase issue definitions.
- [x] Task: Phase verification and checkpoint. Evidence: `benchmark/ontologies`, `src/pelicanbench/ontology.py`.

## P1 Prototype

**Phase state:** `complete`

- [x] Task: Implement the smallest end-to-end vertical slice.
- [x] Task: Add deterministic fixtures and documented failure cases.
- [x] Task: Integrate schemas, provenance and a CLI or adapter boundary.
- [x] Task: Phase verification and checkpoint. Evidence: `benchmark/ontologies`, `src/pelicanbench/ontology.py`.

## P2 Validated

**Phase state:** `complete`
**Evidence level:** `E2` fixture-verified

- [x] Task: Export stable JSON-LD identifiers and feature requirement tiers.
- [x] Task: Add SHACL shape definitions and executable competency-case fixtures.
- [x] Task: Add an explicit UOGTO/HPO/w3id interoperability profile with no automatic semantic imports or false resolver claim.
- [x] Task: Execute unchanged SHACL shapes with a genuine optional engine and non-vacuous positive/negative fixtures. Implementation: `08a8402`; hosted validation at `359fee7`; evidence: `docs/code-only-delivery-20260831.md`.
- [!] Task: Complete expert review of necessary, diagnostic and optional feature tiers.
- [!] Task: Register and independently verify the persistent w3id namespace after its target, licence and version policy are reviewed.
- [!] Task: Complete empirical inter-annotator validation of ontology-driven questions using actual human annotations.

**Current limitation:** JSON-LD, genuine execution of existing SHACL shapes, competency fixtures and namespace-governance checks are E2; w3id registration, expert review and empirical human validation remain open. Engine execution does not qualify additional shape semantics or a normative release.

## P3 Hardened

**Phase state:** `planned`

- [ ] Task: Meet stable performance, fuzzing, security and supply-chain budgets.
- [ ] Task: Complete bridge, migration and deprecation policy.
- [ ] Task: Validate operational ownership, incident response and archival.
- [ ] Task: Phase verification and stable-release checkpoint.
