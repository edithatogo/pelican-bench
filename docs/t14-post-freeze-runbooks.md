# T14 post-freeze runbooks

**State:** inactive preparation only. These runbooks do not authorize or execute ratings,
unblinding, promotion, attestation, merge, release, or publication.

## 1. Sole-steward blinded qualification wave

Recommended first collection, if separately authorized: 8 to 12 assignments selected by the
restricted assignment order, without exposing duplicate identity or allocation.

1. Record a rating-only authorization bound to the D044 freeze receipt.
2. Start the frozen interface with restricted inputs and external mode-0600 ledger/output
   paths. Never place either path inside Git.
3. Stop after the authorized assignment count. Preserve the ledger without analysis or
   unblinding.
4. Review interface failures, completion time, missingness, and accessibility. Do not compute
   duplicate consistency unless the authorized wave happens to complete the required blinded
   duplicate pairs without disclosing their identity.
5. Obtain a new decision before continuing to the complete 106-assignment session.

Contingencies: any source-label exposure, duplicate recognition, automatic-score exposure,
write failure, hash-chain failure, or more than 5% invalid/omitted responses stops collection.

The authorization receipt must use this exact authority scope:

```yaml
receipt_kind: t14-rating-authorization
study_id: t14-human-calibration-v1
freeze_receipt_sha256: 115b8a96303b6f0173080ffc9a38da1cde39c6ef2d7248dad0b838cd7dfec658
decision_maker: benchmark-steward
decision: authorize-blinded-rating
rating_route: qualification
assignment_limit: 12
authority_effect:
  ratings: true
  score_promotion: false
  attestation: false
  release: false
  publication: false
  unblinding: false
```

## 2. Multi-rater and adjudication route

For promotion-grade inter-rater claims, recruit at least two governed human raters and a
separate adjudicator. Complete participant governance, consent, accessibility review,
compensation, production-store review, withdrawal handling, and custodian separation before
assignment. Original ledgers are append-only; adjudication creates a new receipt and never
overwrites a rating. Synthetic agents do not qualify as raters or adjudicators.

## 3. Prespecified blinded analysis

The analyst receives assignment-level responses and frozen public commitments, not the
restricted identity/allocation map. Before analysis, validate response cardinality, hash
chain, missingness, authorization scope, and absence of prohibited fields. Compute only the
prespecified aggregate diagnostics available while blinded. Held-out alignment, duplicate
consistency, and source-group inference wait for a separately authorized custody-mediated
join. Failed or degenerate outcomes are retained and fail closed.

## 4. External scorer challenge

Use `docs/t14-external-scorer-challenge-template.md` to create a content-addressed archive.
The external challenger must be distinct from the preparation agents and return identity,
independence, command-log, result, failure, and finding-disposition commitments. Retain every
attempt. Critical findings block promotion; score-affecting repairs require a new version,
bridge evidence, and steward decision.

## 5. Witnessed recovery rehearsal

Use `docs/t14-witnessed-recovery-rehearsal-template.md` in a genuinely separate environment.
The witness restores an exact tag or archive, runs the full harness, compares output hashes,
and signs or hash-binds the receipt. A same-machine clone is E2 evidence only and does not
close independence.

## 6. Unblinding checkpoint

Unblinding requires a separate receipt after response collection, blinded validation, and
challenge/recovery disposition. The receipt must enumerate exactly which restricted joins
are authorized, who performs them, the inputs and hashes, and the downstream claims still
prohibited. No generic continuation or rating authorization implies unblinding.

## 7. Promotion and release decisions

Only after the prespecified human results, uncertainty, duplicate consistency, missingness,
external challenge, contamination review, and recovery evidence are available may the
benchmark steward consider score promotion. Promotion, attestation, merge, release, and
publication remain distinct decisions. A green repository or hosted check closes none of
them automatically.
