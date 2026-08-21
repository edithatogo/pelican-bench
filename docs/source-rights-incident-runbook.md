# Source-rights incident runbook

The benchmark steward owns the source registry, rights ledger, publication freeze and incident
closure. Rights review is performed by a panel of separate subagent runs with distinct
evidence chains; the steward (the single human developer) makes the final decision from the
panel's options and recommendations. No independent human review or external legal authority
is required to close an incident or a phase checkpoint.

## Trigger and containment

Treat suspected unauthorized redistribution, permission revocation, licence ambiguity, source
misattribution or ledger-to-artifact mismatch as a P0 incident. Freeze publication, quarantine
affected artifacts without deleting them, preserve release manifests and fixity, and open an
incident record. Restricted bytes must not be copied into a public issue.

The steward may contain repository distribution immediately. A disputed rights interpretation,
permission grant or legal conclusion is resolved by the steward after a subagent-panel rights
review; an automated audit or agent recommendation cannot substitute for the steward's
decision, but no external reviewer is required.

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
