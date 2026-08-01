# Threat model

## Assets

Hidden/rotating tasks, rights-controlled source material, provider credentials,
model outputs, human annotations, scorer integrity, release manifests and public
trust.

## Threats

- Malicious SVG scripts, external loads, XML entities, oversized paths and
  renderer denial of service.
- Hidden text, metadata or visual prompt injection targeting learned judges.
- Public-scorer overfitting, task leakage, exact-prompt memorisation and
  benchmark-specific fine-tuning.
- Judge family self-preference, correlated ensemble errors and human rater bias.
- Supply-chain compromise, unpinned actions, arbitrary model code and mutable
  model endpoints.
- Rights violations, attribution loss and private Entire checkpoint leakage.
- Metric drift, silent scorer changes, cherry-picked samples and false precision.

## Controls

Bounded parsing, deny-by-default artifact policy, offline rendering, isolated
containers, rotating challenge tasks, family-diverse judges, bridge sets, manual
rights gates, content hashes, immutable revisions, dry-run remote writes,
attestations and public threats-to-validity reports.
