# T14 freeze integrity and amendment procedure

## Scope

D044 binds the exact T14 candidate, diagnostic, protocol, analysis, blinding, allocation,
renderer, custody, verification, and advisory-panel commitments recorded in
`benchmark/evidence/advisory/t14/procedural-freeze-decision-receipt.json`. The freeze is
procedural, non-independent E2 preparation. It does not authorize ratings, score promotion,
attestation, release, publication, or unblinding.

## Non-mutating integrity recheck

From the repository root, run:

```bash
PATH="$PWD/.venv/bin:$PATH" python scripts/validate_t14_pending_freeze_packet.py
git diff --check
git status --short
```

The validator recomputes the repository-held commitments and rejects byte drift,
cross-packet rebinding, authority escalation, or an independence/human-evidence overclaim.
Success must end with:

```text
T14 exact-hash packet frozen as procedural non-independent E2 preparation; ratings and downstream gates remain unauthorized
```

The external exact-commit harness receipt remains restricted and is checked by its recorded
SHA-256 commitment; the recheck does not disclose its contents or custody secrets. A clean
`git status --short` is useful review evidence but is not itself part of the frozen sample.

## Fail-closed amendment procedure

Never edit a frozen task, asset, manifest, allocation, protocol, analysis plan, renderer lock,
custody artifact, or bound panel packet in place.

1. Stop rating and analysis activity. Preserve every prior byte and receipt.
2. Create a new candidate version outside the frozen paths, with new identifiers and hashes.
3. Record the reason, affected commitments, contamination assessment, and whether any outcome
   or hidden allocation information had been exposed.
4. Regenerate and validate the complete candidate, diagnostic, custody, and panel packet.
5. Obtain a new explicit benchmark-steward freeze decision for the replacement hashes.
6. If outcomes or hidden allocation information were exposed, require a prespecified
   sensitivity analysis or a fresh validation wave; do not reuse the original held-out claim.

A failed recheck leaves D044 as the historical frozen record and blocks further activity. It
does not implicitly amend, revoke, rate, promote, attest, release, publish, or unblind anything.
