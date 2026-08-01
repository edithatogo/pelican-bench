# Workflow

PelicanBench uses spec-driven, test-first development optimised for one developer and multiple agents.

## Track lifecycle

1. **P0 Contract:** MoSCoW requirements, Mermaid design, data/rights/security risks, acceptance tests and score-compatibility class.
2. **P1 Prototype:** smallest executable vertical slice with fixtures and failure cases.
3. **P2 Validated:** independent or human evidence, uncertainty, adversarial tests, reproducibility rerun and documentation.
4. **P3 Hardened:** performance budgets, fuzzing, supply-chain controls, migration/bridge study and stable operational ownership.

## Task states

- `[ ]` pending
- `[~]` in progress or partially evidenced
- `[x]` completed with evidence
- `[!]` externally blocked

## Verification

Every phase ends with a checkpoint that runs relevant unit/integration tests, schema validation, rights checks, repository-contract validation and reproducibility checks. Benchmark score changes require before/after reports and a compatibility decision.

## Commit policy

Use conventional commits and keep commits reversible. Entire captures agent-session provenance on its checkpoint branch. The active branch contains clean product commits only.

## External writes

Automation must be dry-run by default, idempotent, and record remote identifiers locally. Never silently create large paid runs or publicise rights-restricted material.
