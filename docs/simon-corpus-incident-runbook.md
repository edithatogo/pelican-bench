# Simon corpus incident runbook

The benchmark steward owns corpus ingestion, rights-state enforcement, coverage claims and archive
custody. No backup custodian or independent source reviewer is currently appointed, so the
repository does not claim resilient multi-operator or independent operational validation.

## Incident response

Treat unauthorized content export, source-fixity mismatch, archive-coverage overclaim or lost
annotation provenance as P0. Freeze corpus publication, quarantine affected content without
destroying evidence, preserve metadata, hashes and receipts, and open an incident record.
Restricted text must not be copied into a public issue.

Resolution requires an accountable source or rights review where interpretation is disputed, a
new decision rather than silent history edits, targeted regression evidence, the corpus rights
gate and the full harness. Prepare correction or withdrawal instructions for affected downstream
artifacts. The steward closes the incident only when repository and downstream states agree.

## Archival continuity

Retain source metadata, content fixity, rights decisions, annotation versions and coverage reports
permanently in Git history or a content-addressed release archive. Quarantine controls byte access;
it does not erase custody history. Metadata-only records remain distinct from raw content and
derived analysis.

The executable invariants are recorded in
`benchmark/evidence/snapshots/simon-corpus-operations.json`. They validate the repository procedure,
not source-owner permission, complete archive coverage or independent operational rehearsal.
