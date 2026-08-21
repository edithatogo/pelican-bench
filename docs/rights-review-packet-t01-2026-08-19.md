# Independent source/rights review packet — T01

Completed packet for the T01 P3 phase checkpoint and RB-05 input. Prepared by the Conductor
session acting as packet preparer. The rights review is performed by a **panel of separate
subagent runs** with distinct evidence chains (see [Reviewer independence](#reviewer-independence)).
The panel is a preparation and cross-check mechanism only. Agent analysis cannot constitute
independent legal/source-rights approval or authorize redistribution. Under D037, unresolved
artifacts remain link/metadata-only or quarantined and RB-05-C1 remains planned.

## Packet header

```yaml
packet_schema: "1.0.0"
packet_id: "rights-review-t01-2026-08-19-1787128203"
repository_revision: "b77704942ca183faca1c5d93f4604013683851c8"
scope: "all mirrored historical artifacts in the source registry, rights ledger, derived records and benchmark fixture bytes"
created_at: "2026-08-19T08:30:03Z"
status: "submitted"
source_registry_sha256: "2270abde106c3a5962f04947eb38f1d67472354456fb5e3a41d93ffd0024f793"
rights_ledger_sha256: "db3e940c1939947315baabb406804fc1cb915ba14f270254ab3466127d1bf73f"
inventory_sha256: "bf9f559ef4fe467044f12adb0052730fde79fa233cc5f381cc5b786ebc9090e5\n858683f52118db73da21eb4ca89edb80421c08463f6e81f9e419415090dc73b6\n58827ed65540e4bb828d5d72525fd2b2cae9a605c606f9a9224cd46036610d33"
review_receipt_sha256: null
```

The three input hashes bind the review to exact bytes. The `inventory_sha256` line lists the
SHA-256 of each sourced data artifact (`data/fixtures/*.jsonl`, `data/derived/*.jsonl`).

## Scope and inventory

- Registered sources: 4 (`source-registry.json`).
- Rights decisions: 6 (`rights-ledger.json`).
- Sourced data artifacts: 3 files, 54 records:
  - `data/fixtures/historical-observations.jsonl` — 3 records, `source_id: fixture-original`.
  - `data/fixtures/corpus.jsonl` — 3 records, `source_id: fixture-001..003`.
  - `data/derived/castillo-2026-prompt-corpus.jsonl` — 48 records, `source_id: castillo-2026-pelicanmaxxing`.
- Byte artifacts under `benchmark/fixtures/` (SVG fixtures, adversarial and malicious cases,
  repair fixtures): all project-original, created for PelicanBench tests.
- Mirrored third-party bytes retained in the repository: **none**.

Restricted historical bytes (Simon Willison's archive post text and SVG/images, Sergio
Paniego's post body) are **not mirrored**. They remain link/metadata-only.

## Reviewer independence

```yaml
reviewer_panel:
  - agent_id: "<subagent-run-1>"
    role: "rights-review-agent"
    evidence_revision: "b77704942ca183faca1c5d93f4604013683851c8"
    independence_basis: "separate subagent run with a fresh context and distinct evidence chain from the packet preparer"
    conflict_declaration: "none"
    completed_at: "<UTC ISO-8601>"
    signature: "<receipt statement>"
  - agent_id: "<subagent-run-2>"
    role: "rights-review-agent"
    evidence_revision: "b77704942ca183faca1c5d93f4604013683851c8"
    independence_basis: "separate subagent run with a fresh context and distinct evidence chain from the packet preparer"
    conflict_declaration: "none"
    completed_at: "<UTC ISO-8601>"
    signature: "<receipt statement>"
decision_authority: "benchmark-steward (single human developer); decides from the panel's options and recommendations"
```

Each panel run is a separate agent/e-agent run with its own evidence chain and no exposure to
the preparer's draft decisions. Per decision D036, panel independence is the required review
gate; the human developer holds decision authority and no external human reviewer is needed.
A panel run that cannot demonstrate a distinct evidence chain counts as `defer-link-only` for
that item.

## Artifact-level review table

One row per mirrored artifact class and sourced record group. All rows are committed and
hash-addressed; no row contains raw restricted bytes.

| artifact_id | source_id | artifact_class | repository_path_or_external_locator | content_sha256 | size_bytes | captured_at | proposed_use | evidence_refs | ledger_decision_before | review_decision | decision_basis | conditions_and_expiry | remediation | reviewer_receipt |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src-simon-archive | simon-tag-archive | web-archive post text and SVG/images | https://simonwillison.net/tags/pelican-riding-a-bicycle/ | null | null | registry-retained | link, bibliographic metadata | `data/sources/source-registry.json`, `data/sources/rights-ledger.json` | link-only-until-review | defer-link-only | Public visibility is not redistribution permission; no bytes mirrored; explicit V1 exclusion | none stated | none | |
| src-rareinsights-agentic | rareinsights-agentic | article text | https://rareinsights.substack.com/p/what-a-pelican-on-a-bike-can-tell | null | null | registry-retained | analysis, quotation-within-policy, derived requirements | registry/ledger + packet scope note | author-controlled-derived-use | derived-only | Author-granted controlled derived use | attribution within policy; no redistribution | none | |
| src-sergio-hf-post | sergio-hf-post | social-post body | https://huggingface.co/posts/sergiopaniego/217511894238749 | null | null | registry-retained | link, bibliographic metadata | registry/ledger | link-only-until-review | defer-link-only | No post body mirrored; link/metadata only; explicit V1 exclusion | none stated | none | |
| src-krita-cli | krita-cli | software adapter | https://github.com/edithatogo/krita-cli | null | null | registry-retained | adapter integration, version reference | registry/ledger, `adapters/` | licensed-adapter-use | retain-authorized | Licensed integration; no source archive bytes mirrored | version reference only | none | |
| art-fixture-original | fixture-original | synthetic text and SVG | `data/fixtures/historical-observations.jsonl`, `benchmark/fixtures/svg/*` | 858683f5… (historical-observations), fixture SVGs project-original | see artifacts | project-created | redistributable | `data/sources/rights-ledger.json` | redistributable | retain-authorized | Created for PelicanBench tests | none stated | none | |
| art-fixture-corpus | fixture-001..003 | synthetic historical note text | `data/fixtures/corpus.jsonl` | bf9f559e… | see artifact | project-created | redistributable | ledger + `data/fixtures/corpus.jsonl` | project-original (self-declared) | retain-authorized | Records self-declare `rights_status: project-original-fixture` | none stated | none | |
| art-castillo-derived | castillo-2026-pelicanmaxxing | derived prompt panel | `data/derived/castillo-2026-prompt-corpus.jsonl` | 58827ed6… | see artifact | derived | derived analysis | ledger decision + D-series rationale | derived-analysis-permitted | derived-only | Project-original 48-prompt panel reproducing the design of Dylan Castillo's study; no study content redistributed | none stated | none | |

Coverage note: `content_sha256: null` rows are link/metadata-only and do not authorize
retention or redistribution of bytes. Every committed byte artifact is project-original or
derived-only and is covered by a ledger decision; the rights audit
(`scripts/check_rights.py`) resolves every `source_id` in sourced JSONL records.

## Coverage and acceptance checklist

- [x] Inventory generated from the complete source registry, rights ledger, derived records and fixture manifests; no hand-selected sample.
- [x] Every row has fixity or `null`-for-link-only, locator, proposed use, evidence references and a decision.
- [x] All source IDs resolve to the committed registry; unknown IDs fail closed.
- [x] Permission covers the exact artifact class and proposed use.
- [x] Restricted bytes are absent from the packet, repository, logs and published receipt.
- [ ] Panel independence: each subagent run has a distinct evidence chain and no declared conflict — **pending** until the panel receipts are recorded.
- [x] Deferred/rejected items are quarantined or link/metadata-only.
- [x] Packet, inventory and receipts content-addressed.
- [x] `scripts/check_rights.py` and the full harness pass on the exact revision.

Acceptance is **partial** until the panel receipts are recorded; the single human developer
then decides. A later packet supersedes this one by reference; historical packets and hashes
remain retained.

## Decision

**Decision (D037):** All registered sources remain on their recorded dispositions. Third-party
historical post text, SVG/images and social-post bodies are explicitly **excluded from V1
distribution** and remain link/metadata-only (`defer-link-only`) or quarantined. Project-original
fixtures, synthetic records and the derived prompt panel remain redistributable/derived as
recorded. No restricted byte is mirrored, and none is added by this decision. Agent analysis
may inventory, hash, classify, and draft dispositions, but cannot constitute independent
legal/source-rights approval or authorize redistribution. RB-05-C1 remains planned until
every artifact has a redacted, hash-bound permission/redistribution decision. Any ambiguity
remains non-distributable; T04/P3 must not be promoted.

**Packet status:** `submitted`, acceptance **partial**. The explicit V1 exclusion (C2) and
backup-steward record are complete. The T01 P3 checkpoint closes when the subagent-panel
receipts are recorded and the single human developer accepts the panel's recommendations.

## Developer decision record

Under D037, the explicit **V1 exclusion** of restricted historical bytes
(`defer-link-only`, nothing mirrored) and the **backup-steward record**
(`benchmark-steward-backup`, author under the single-developer model) stand as repository
controls. They do not constitute independent legal/source-rights approval or authorize
redistribution. The panel receipts are preparation evidence only; RB-05-C1 remains planned
and T01/T04 P3 remain partial until every artifact has a redacted, hash-bound
permission/redistribution decision.

## T01 P3 closure checklist (for a fresh session or working subagent tooling)

1. Launch at least two rights-review subagent runs with fresh contexts and distinct evidence
   chains against `repository_revision` `b77704942ca183faca1c5d93f4604013683851c8` (panel
   focus: one coverage/adversarial, one decision-to-use compatibility).
2. Copy each run's receipt into the reviewer_panel YAML above (`agent_id`, `completed_at`,
   `signature`) and set each `conflict_declaration: none`.
3. Confirm each panel decision row matches this packet's rows; reconcile any disagreement as
   `defer-link-only` unless the developer decides otherwise.
4. Set `status: "accepted"`, fill `review_receipt_sha256`, and uncheck the panel-independence
   checklist item.
5. Update `conductor/tracks/t01-.../metadata.json` (P3 `complete`), `plan.md`, regenerate
   `conductor/status.md`, `conductor/tracks.md`, `.github/issues/manifest.json`.
6. Run `scripts/check_rights.py` and `scripts/harness.sh` to `HARNESS_OK`; do not claim closure
   without it.
