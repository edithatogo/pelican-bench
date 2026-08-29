# T14 accountable-gate preparation templates

These templates implement D042 preparation without crossing an accountable gate:

- `docs/t14-freeze-decision-template.md`: later exact-hash sample freeze decision;
- `docs/t14-rating-custody-template.md`: governed ratings and operational custody;
- `docs/t14-external-scorer-challenge-template.md`: independent adversarial submission;
- `docs/t14-witnessed-recovery-rehearsal-template.md`: independent environment and witness;
- `docs/t14-release-attestation-dry-run-template.md`: local packaging and remote-action
  boundaries.

All are fail-closed. Placeholder, unsigned, self-contradictory, agent-invented, or
same-environment evidence has no promotion effect. Controlled unblinding additionally
requires verified analysis-lock and blinded-data-freeze commitments under
`docs/study-freeze-and-unblinding.md`; its authorization and outputs remain restricted and
must never enter a publication bundle.
