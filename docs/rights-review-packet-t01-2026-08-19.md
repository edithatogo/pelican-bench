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
status: "accepted"
source_registry_sha256: "2270abde106c3a5962f04947eb38f1d67472354456fb5e3a41d93ffd0024f793"
rights_ledger_sha256: "db3e940c1939947315baabb406804fc1cb915ba14f270254ab3466127d1bf73f"
inventory_sha256: "bf9f559ef4fe467044f12adb0052730fde79fa233cc5f381cc5b786ebc9090e5\n858683f52118db73da21eb4ca89edb80421c08463f6e81f9e419415090dc73b6\n58827ed65540e4bb828d5d72525fd2b2cae9a605c606f9a9224cd46036610d33"
review_receipt_sha256: "4fb0b1f66be75d3dca086718c187e9617b03515fa308141117234a3167389bef"
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
  - agent_id: "rights-review-panel-run-1-coverage"
    role: "rights-review-agent"
    focus: "coverage/adversarial completeness"
    evidence_revision: "a11748a79c79204b12338946046c51be89f1250b"
    independence_basis: "separate headless subagent run (isolated session store) with a fresh context and distinct evidence chain from the packet preparer and co-reviewer; findings derived from its own enumeration, hashing, greps and audit runs at both HEAD and the pinned revision tree"
    conflict_declaration: "none"
    completed_at: "2026-08-23T00:40:06Z"
    signature: "I performed this coverage/adversarial rights review independently on revision a11748a79c79204b12338946046c51be89f1250b, deriving every finding from my own enumeration, hashing, greps and audit runs against primary evidence."
  - agent_id: "rights-review-panel-run-2-compatibility"
    role: "rights-review-agent"
    focus: "decision-to-use compatibility"
    evidence_revision: "a11748a79c79204b12338946046c51be89f1250b"
    independence_basis: "separate headless subagent run (isolated session store) with a fresh context and distinct evidence chain from the packet preparer and co-reviewer; conclusions derived from direct file reads, shasum runs, greps and sampling in its own session"
    conflict_declaration: "none"
    completed_at: "2026-08-23T00:48:52Z"
    signature: "I independently read and hashed the registry, ledger, operations policy, spec, packet, fixtures and derived corpus at revision a11748a79c79204b12338946046c51be89f1250b and performed this decision-to-use compatibility review myself without reliance on the preparer's or co-reviewer's analysis."
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
- [x] Panel independence: each subagent run has a distinct evidence chain and no declared conflict — receipts recorded 2026-08-23 (`rights-review-panel-run-1-coverage`, `rights-review-panel-run-2-compatibility`; see Reviewer independence).
- [x] Deferred/rejected items are quarantined or link/metadata-only.
- [x] Packet, inventory and receipts content-addressed.
- [x] `scripts/check_rights.py` and the full harness pass on the exact revision.

Acceptance was partial until the panel receipts were recorded; the single human developer
then decided. The receipts are now recorded (2026-08-23) and the steward has accepted the
panel's recommendations with the corrections in the addendum applied — see the Decision and
Developer decision record sections. A later packet supersedes this one by reference;
historical packets and hashes remain retained.

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

**Packet status:** `accepted` (2026-08-23). The explicit V1 exclusion (C2) and backup-steward
record are complete. The T01 P3 checkpoint closed when both panel receipts were recorded and
the single human developer accepted the panel's recommendations with the addendum
corrections applied (decision D042).

## Addendum 2026-08-23 — panel receipts, corrections and acceptance

Both panel runs independently confirmed every artifact-level review decision (7/7 rows),
independently verified that no mirrored third-party bytes exist anywhere in the repository,
and re-ran `scripts/check_rights.py` to exit 0 at HEAD and against an extracted tree of the
pinned revision. Their findings were documentation-level only. Per packet procedure step 3,
no row required forced `defer-link-only` reconciliation. Corrections below were approved by
the benchmark steward before recording.

1. **Header binding annotation (C1).** The pinned `repository_revision` predates a later,
   decision-preserving amendment of `rights-ledger.json` rationale prose: at `b777049` the
   ledger hashed `9bfcb7d1…`; the header's `db3e940c…` binds the amended bytes at HEAD
   (`a11748a…`). Both panel runs verified the decisions themselves are unchanged between the
   two revisions, so the three input hashes bind the exact bytes under review at HEAD.
   Recorded here rather than silently rewritten; historical hashes remain retained.
2. **Coverage wording corrected (C2).** Sourced records resolve through three sanctioned
   paths: registry→ledger decisions (`simon-tag-archive`, `rareinsights-agentic`,
   `sergio-hf-post`, `krita-cli`), ledger-only decisions (`fixture-original`,
   `castillo-2026-pelicanmaxxing` — ledger-resolved without a registry entry), and the
   fail-closed record-level `project-original-*` self-declaration path (`fixture-001..003`
   in `data/fixtures/corpus.jsonl`). The earlier claim that "every committed byte artifact
   is covered by a ledger decision" overstated coverage for `fixture-001..003`, which is
   covered by its self-declaration instead. The checklist item "all source IDs resolve to
   the committed registry" is likewise narrowed: unknown IDs still fail closed, but
   resolution legitimately includes the ledger-only and self-declaration paths.
3. **Condition wording restored/clarified (C3).** The `src-rareinsights-agentic` row's
   conditions include the ledger's "retain publication separation". The `src-krita-cli`
   "version reference only" entry describes a permitted use boundary, not an expiry-style
   condition.
4. **Known limitations recorded (C4).** Byte artifacts under `benchmark/fixtures/` sit
   outside machine verification by `scripts/check_rights.py` (which audits
   `data/fixtures/*.jsonl` and `data/derived/*.jsonl`); their project-original status rests
   on the ledger decision plus manual inspection (both panel runs found only generic
   geometry and placeholder URLs). Under the single-developer model the recorded backup role
   collapses onto the same accountable human and provides procedural rather than independent
   continuity.

`review_receipt_sha256` = SHA-256 of the concatenation of run-1 receipt, run-1 continuation
and run-2 receipt transcripts in run order.

## Developer decision record

Under D037, the explicit **V1 exclusion** of restricted historical bytes
(`defer-link-only`, nothing mirrored) and the **backup-steward record**
(`benchmark-steward-backup`, author under the single-developer model) stand as repository
controls. They do not constitute independent legal/source-rights approval or authorize
redistribution. The panel receipts are preparation evidence only; RB-05-C1 remains planned
and T01/T04 P3 remain partial until every artifact has a redacted, hash-bound
permission/redistribution decision.

**Steward decision (D042, 2026-08-23):** the receipts are recorded and the steward accepts
the panel's recommendations with corrections C1–C4 applied above. Every registered source
and sourced artifact now carries an explicit, hash-bound disposition in this accepted
packet: third-party historical bytes are excluded from V1 distribution and remain
link/metadata-only (`defer-link-only`); project-original fixtures, synthetic records and the
derived prompt panel remain redistributable/derived as recorded. No restricted byte is
mirrored, and none is added by this decision. Any ambiguity remains non-distributable.
RB-05-C1 is satisfied for mirrored artifacts (none are mirrored) and is marked complete in
`conductor/release-blockers.json`; RB-05 itself remains partial on human-participant
governance (C3). T04/P3 promotion remains governed by its own plan and D037.

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
