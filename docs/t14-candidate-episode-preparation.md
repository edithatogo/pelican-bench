# T14 candidate episode preparation

The repository contains a deterministic, project-original development package of 96 SVG
repair episodes at `benchmark/fixtures/repair/candidate/manifest.json`. The package crosses
12 scene groups with eight defect families. Whole scene groups are assigned by a predeclared
exhaustive allocation rule to 72 proposed-development and 24 proposed-held-out episodes.

This is candidate intake material only. The split is not frozen or normative, no agent output
is a human rating, and the package does not establish calibrated thresholds, E3 evidence,
independent validation, score compatibility, release readiness, or publication authority.

## Reproduction and validation

```bash
python scripts/build_t14_candidate_episodes.py --check
python scripts/validate_t14_candidate_episodes.py
```

The builder checks deterministic source bytes without repeating the validator's raster work.
The validator independently checks project-root confinement, symlinks, source commitments,
repository-native SVG safety inspection, canonical 512-pixel opaque-white render hashes,
operation-aware before/after predicates, preservation annotations, visible edits, group
isolation, and the proposed 72/24 balance.

The package deliberately records its 12 dependence clusters and shared repaired references.
Any later uncertainty analysis must use the scene group as the resampling unit. Candidate file
names, declared roles, defect identifiers, and requirements expose source labels and must not
be passed directly to a human-rating interface. A separate alias-only blinded manifest may be
created only after a fresh benchmark-steward freeze decision.

Three exact-commit advisory reviews are retained under `benchmark/evidence/advisory/t14/`.
They accept the package as local candidate preparation while recommending revisions before
any normative freeze. The later validator hardening in `de9a13d` addresses the
target-specific move concern without altering candidate assets: displaced rear wheels must
be vertically realigned, and repaired foot endpoints must move closer to an unchanged pedal.
The remaining recommendations are genuinely distinct vehicle/scene geometry or an explicit
waiver, independent severity manipulation, and predeclared under-repair, over-edit,
introduced-defect, boundary, and invalid cases.
