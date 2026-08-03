# Contract operations runbook

The benchmark steward owns task, output, score, run, verification and release-package contracts.
The same role authorizes releases and retains their immutable records. No backup contract steward
is currently appointed, so independent operational resilience remains unproven.

## Contract incidents

Treat acceptance of an invalid contract, rejection of a valid released contract, provenance
mismatch or silent score reinterpretation as P0. Freeze the release, preserve affected bytes and
receipts, classify score compatibility and restore the last known good contract. Resolution
requires a regression fixture, an explicit migration or bridge decision, the full harness and a
correction notice when downstream users may be affected.

Do not repair historical results in place. A corrected interpretation creates a new version and
retains the original receipt. Security containment may disable a reader immediately, but removal
of a supported contract still follows the release-policy compatibility and deprecation rules.

## Archive and recovery

Released schemas, content-addressed manifests, verification receipts and migration evidence are
retained permanently in Git history and release archives. Recovery starts from a tagged schema
and its matching receipt, verifies hashes before parsing, and replays the bridge against retained
fixtures. A current generator is not evidence for an earlier release unless its output matches
the archived hash.

The executable operational invariants live in
`benchmark/evidence/snapshots/contract-operations.json` and are checked by the contract test
suite. This repository evidence validates the procedure, not sustained multi-operator use.
