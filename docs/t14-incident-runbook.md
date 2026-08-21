# T14 incident and archive runbook

The benchmark steward owns T14 scoring, calibration packets, release freezes, and incident
closure. Agent panels advise on incidents; they do not authorize release or erase evidence.

## Trigger and containment

Treat a malformed-input bypass, unsafe render, budget breach, score-manifest mismatch,
calibration privacy issue, or accidental normative promotion as a P0 T14 incident. Freeze
publication, quarantine affected outputs, preserve hashes and manifests, and record a redacted
incident entry. Never copy restricted source bytes into an issue or receipt.

## Recovery

1. Identify the affected method version, commit, fixture set, and release manifests.
2. Preserve the original outputs and fixity; do not rewrite history.
3. Have the agent panel analyze containment, scope, and remediation options.
4. The benchmark steward records the decision and any rollback or migration conditions.
5. Add a regression fixture when lawful, rerun focused tests and the full harness, and publish
   only a redacted correction or withdrawal receipt.

## Archival continuity

Retain method versions, fixture hashes, calibration packets, decision receipts, incident
records, and superseded manifests permanently in Git or a content-addressed release archive.
Quarantine preserves custody; it does not authorize redistribution or delete the audit trail.

The current clean-clone rehearsal is recorded in
`benchmark/evidence/snapshots/t14-operations.json` as E2 evidence. It passed the full
harness, but remains unwitnessed and same-environment; it does not close the independent
recovery or E4 release gate.
