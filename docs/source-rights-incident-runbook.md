# Source-rights incident runbook

The benchmark steward owns the source registry, rights ledger, publication freeze and incident
closure. No backup steward or external rights reviewer is currently appointed; that resilience
gap remains explicit and prevents a claim of independently validated operational maturity.

## Trigger and containment

Treat suspected unauthorized redistribution, permission revocation, licence ambiguity, source
misattribution or ledger-to-artifact mismatch as a P0 incident. Freeze publication, quarantine
affected artifacts without deleting them, preserve release manifests and fixity, and open an
incident record. Restricted bytes must not be copied into a public issue.

The steward may contain repository distribution immediately. A disputed rights interpretation,
permission grant or legal conclusion requires accountable external review; an automated audit
or agent recommendation cannot supply that authority.

## Resolution and recovery

Record a new ledger decision rather than rewriting the historical one. Identify every affected
release and downstream location, prepare correction or withdrawal instructions, add a regression
fixture when it can be retained lawfully, and rerun `scripts/check_rights.py` plus the full
harness. The steward closes the incident only after the repository evidence and required
downstream actions agree.

## Archival continuity

Retain source identities, decision rationale, fixity, release-bound audit receipts and superseded
ledgers permanently in Git or a content-addressed release archive. Quarantine controls access; it
does not erase custody history. Public archives receive only rights-cleared metadata and bytes.
Any external takedown or correction remains a separately authorized action with its own receipt.

The machine-readable invariants are in `data/sources/operations-policy.json` and are exercised by
the source-rights contract tests.
