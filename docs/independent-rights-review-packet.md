# Independent source/rights review packet

This packet is the repository-owned template for the T04/RB-05 review of mirrored
historical artifacts. It is a request for an independent decision, not evidence that
permission exists. Until a completed packet is accepted and its digest is recorded in the
release evidence, every unresolved artifact remains link/metadata-only and publication is
blocked.

## Recommended decision wording

> **Decision:** Retain the artifact only for the disposition stated below. Public
> visibility is not treated as redistribution permission. Any artifact without a recorded
> permission basis, fixity receipt, and independent decision remains link/metadata-only.
> This review does not expand the rights ledger, authorize new acquisition, or permit
> redistribution of source bytes.

For an unresolved item, use:

> **Decision:** `defer-link-only`. The available evidence does not establish permission
> for the proposed use. Do not copy, publish, quote beyond the existing policy, or derive
> retained source bytes until a new decision is recorded.

For a rejected item, use:

> **Decision:** `reject-remove-or-quarantine`. Retained source bytes are not authorized
> for the proposed use. Quarantine or remove them through the incident/archive procedure;
> preserve only redacted metadata, hashes, and the decision receipt.

Agents may prepare and cross-check this packet. An agent-generated assessment is still
repository evidence (E1/E2), not source-owner permission, legal advice, independent
reproduction, or an authority to close RB-05/T04.

## Packet header

Complete every field; use `null` or `unassigned` rather than guessing.

```yaml
packet_schema: "1.0.0"
packet_id: "rights-review-t04-<date>-<nonce>"
repository_revision: "<40-character commit>"
scope: "all mirrored historical artifacts in the source registry and derived records"
created_at: "<UTC ISO-8601>"
status: "draft | submitted | accepted | rejected | superseded"
source_registry_sha256: "<64 lowercase hex characters>"
rights_ledger_sha256: "<64 lowercase hex characters>"
inventory_sha256: "<64 lowercase hex characters>"
review_receipt_sha256: null
```

The three input hashes bind the review to exact bytes. Recompute them after any source
registry, ledger, or inventory change; never edit a completed receipt in place.

## Reviewer independence and conflict record

The reviewer must be a separately identified agent or agent run with a distinct evidence
chain from the packet preparer. Agents must record provenance sufficient to reproduce the
review, while omitting credentials, private request data, and restricted source bytes.

```yaml
reviewer:
  agent_id: "<stable agent/run identifier>"
  role: "independent-rights-review-agent"
  evidence_revision: "<reviewer checkout commit>"
  started_at: "<UTC ISO-8601>"
  completed_at: "<UTC ISO-8601>"
  independence_basis: "<separate run, workspace, or evidence chain>"
  conflict_declaration: "none | declared"
  conflict_details: null
  methods_and_limits: "<sources checked, policies applied, and limits>"
  signature: "<content-addressed receipt statement>"
```

`conflict_declaration: declared`, a missing identity, or an unverifiable evidence chain
forces the packet to `rejected`/`defer-link-only`; it cannot be treated as independent.

## Artifact-level review table

There must be one row for every mirrored byte artifact, quoted excerpt, SVG/image, archived
post body, and derived record that could carry source content. Rows may point to a redacted
inventory outside Git, but the row itself must remain committed and hash-addressed.

| Field | Required value |
| --- | --- |
| `artifact_id` | Stable identifier; never recycle an identifier |
| `source_id` | Exact `source-registry.json` identifier |
| `artifact_class` | E.g. post text, SVG/image, article excerpt, derived record |
| `repository_path_or_external_locator` | Repository-relative path or URL; no raw restricted bytes |
| `content_sha256` | SHA-256 of the reviewed bytes, or `null` when bytes were not retained |
| `size_bytes` | Exact size, or `null` for link/metadata-only |
| `captured_at` / `retrieved_at` | UTC timestamps and receipt reference |
| `proposed_use` | Link, metadata, quote, analysis, derived, or redistribution |
| `evidence_refs` | Terms, permission, provenance, and retrieval receipt identifiers |
| `ledger_decision_before` | Decision currently recorded in `rights-ledger.json` |
| `review_decision` | `retain-authorized`, `quote-limited`, `derived-only`, `defer-link-only`, or `reject-remove-or-quarantine` |
| `decision_basis` | Concise permission/terms basis; “public” alone is invalid |
| `conditions_and_expiry` | Attribution, scope, territory, duration, or `none stated` |
| `remediation` | Required quarantine/removal/ledger update, or `none` |
| `reviewer_receipt` | Hash-addressed signed decision and timestamp |

An absent row is a coverage failure. A row with `content_sha256: null` cannot authorize
retention or redistribution of bytes. A mismatch with the current ledger is a release
blocker until a new ledger decision is reviewed and recorded.

## Coverage and acceptance checklist

- [ ] Inventory was generated from the complete source registry, rights ledger, derived
  records, and archive manifests; no hand-selected sample was used.
- [ ] Every row has fixity, locator, proposed use, evidence references, and a decision.
- [ ] All source IDs resolve to the committed registry; unknown IDs fail closed.
- [ ] Permission covers the exact artifact class and proposed use, not merely the source's
  public availability.
- [ ] Restricted bytes are absent from the packet, repository, logs, and published receipt.
- [ ] Reviewer independence and conflict declaration are complete and verifiable.
- [ ] Deferred/rejected items are quarantined or link/metadata-only.
- [ ] The packet, inventory, receipts, and any ledger change are content-addressed.
- [ ] `scripts/check_rights.py` and the full harness pass on the exact revision.

Acceptance is **partial** if any checklist item is unchecked. The packet must not be used to
mark RB-05 or T04/P3 complete, and no generated Conductor view may claim otherwise. A later
packet supersedes this one by reference; historical packets and their hashes remain retained.

## Agent execution recipe

1. Copy this template into a restricted review workspace and generate the complete inventory.
2. Have a separate agent run the review from the exact `repository_revision`, checking each
   artifact against the source registry, ledger, terms, and receipts.
3. Exchange only the redacted packet, hashes, and decision receipts between agents.
4. Apply only decisions that are explicit, artifact-scoped, and consistent with the ledger;
   unresolved or ambiguous results stay `defer-link-only`.
5. Commit the redacted packet and receipt references, regenerate derived views, and rerun the
   rights audit and harness. Do not claim independent clearance from green automation alone.
