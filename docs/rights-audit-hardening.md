# Rights-audit hardening

The source-rights audit is a local, dependency-free gate over committed JSONL records. It
does not fetch remote content or grant redistribution permission.

## Resource budgets

The default `RightsAuditPolicy` rejects inputs before unbounded processing when they exceed:

- 1 MB for the rights ledger;
- 10 MB for any sourced JSONL artifact;
- 1 MB for an individual JSONL record; or
- 100,000 non-blank records across the audit.

Callers may select smaller positive budgets for constrained environments and tests. Zero and
negative budgets are invalid. These are operational safety ceilings rather than maturity or
rights claims.

## Security and fuzzing

The audit rejects symbolic links for both the ledger and sourced artifacts, preventing a
committed path from redirecting validation outside the repository. Malformed JSON, non-object
records, missing source identifiers, unknown sources, oversized inputs and record-count
exhaustion all fail closed. Edge tests exercise each resource boundary; deterministic
Hypothesis cases exercise arbitrary source identifiers and rights-status strings.

## Supply-chain boundary

The audit implementation uses the Python standard library and is included in the repository's
source SBOM. The full harness also verifies dependency locks, immutable GitHub Action pins and
deterministic SPDX generation. Those controls establish repository provenance; they do not
replace permission records or an independent rights review.

## Harness timing budget

The independently collected unit taxonomy has a 120-second ceiling; narrower taxonomy lanes
retain a 60-second ceiling. The unit ceiling covers the same broad repository suite that takes
roughly 70–80 seconds in the primary harness on the reference macOS checkout, avoiding a gate
that expires after tests complete while still bounding stalled subprocesses.
