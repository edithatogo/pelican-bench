# Workflow

PelicanBench uses spec-driven, test-first development optimised for one developer working with multiple agents. Conductor phases organise work; evidence levels govern claims.

## Track lifecycle

1. **P0 Contract:** MoSCoW requirements, Mermaid design, intended inference, data/rights/security risks, acceptance tests and score-compatibility class.
2. **P1 Prototype:** smallest executable vertical slice with deterministic fixtures and explicit failure cases.
3. **P2 Validated:** progress from fixture verification toward empirical calibration, adversarial testing and reproducibility. P2 may remain `partial` while E3 or E4 evidence is outstanding.
4. **P3 Hardened:** performance and resource budgets, fuzzing, supply-chain controls, migration/bridge study, incident response and sustained operational ownership.

## Evidence levels

| Level | Meaning |
|---|---|
| E0 | Defined: claim and acceptance evidence specified |
| E1 | Implemented: code or protocol exists |
| E2 | Fixture-verified: deterministic local evidence passes |
| E3 | Empirically calibrated: external, human or prospective data support the claim |
| E4 | Independently reproduced: a second environment or team reproduces it |
| E5 | Operationally hardened: sustained releases, drift and incident controls are evidenced |

A phase may be complete at E2 while a release blocker correctly prevents a V1 claim requiring E3 or E4. The track metadata, assurance case and release blockers are authoritative.

## Task states

- `[ ]` pending
- `[~]` in progress or partially evidenced
- `[x]` completed with linked evidence
- `[!]` externally blocked

## Deterministic derived views

`conductor/tracks.md`, `conductor/status.md` and `.github/issues/manifest.json` are generated from track metadata and `conductor/release-blockers.json`. The harness rejects stale copies.

```bash
python scripts/generate_issue_manifest.py --check
python scripts/generate_conductor_docs.py --check
```

## Verification

Every phase ends with the relevant subset of unit, integration, metamorphic, schema, ontology, rights, security, repository-contract and reproducibility checks. Score-affecting changes require before/after evidence, exploit regression coverage and an explicit compatibility decision.

The full local gate is:

```bash
bash scripts/harness.sh
```

Remote CI execution, human calibration, prospective model runs and publication cannot be inferred from configured files. They close only when resulting evidence is attached to the relevant release-blocker criteria.

## Commit and provenance policy

Use conventional, reversible commits. Entire captures agent-session provenance on its checkpoint branch. Evaluation runs separately emit content-addressed manifests, W3C PROV, RO-Crate and reproduction commands. The active branch contains product commits rather than transient agent checkpoints.

## External writes

Automation is dry-run by default, idempotent and records remote identifiers locally. It must not silently create paid runs, expose secrets or publish rights-restricted material.

## Governed learning

Agents may propose and test heuristics but cannot silently mutate normative tasks, ontologies, rubrics or scorers. Promotion requires contamination review, held-out transfer evidence, a regression comparison, scope and expiry conditions, human approval and rollback criteria.
