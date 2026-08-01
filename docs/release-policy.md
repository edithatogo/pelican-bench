# Release and score-compatibility policy

Packages and APIs use semantic versioning. Benchmark datasets use calendar-labelled releases such as `PB-2026.08` and immutable Hub and Git tags.

## Change classes

- **Editorial:** documentation only; scores unaffected.
- **Compatible:** a bug fix demonstrably preserving score distributions within a declared tolerance.
- **Bridge-required:** a scorer, ontology, rendering, judge or task change that may alter ranks or thresholds.
- **Breaking:** a changed construct, critical gate, protected task distribution or result schema.

Bridge-required and breaking changes publish old and new paired results on a frozen bridge set, distribution-drift analysis, human-alignment evidence where relevant, migration notes and an explicit decision record. Historical results are never silently recalculated under a new scorer.

## Evidence profiles

- `v0.2-alpha` requires E2 fixture-verified evidence for the measurement-validity claims listed in `benchmark/assurance-case.json`.
- `v1.0` requires E3 empirical calibration, closure of all five release blockers and an independent reproduction.
- E4 and E5 are reserved for independent reproduction and sustained operational hardening. They are not inferred from CI configuration alone.

## Release artifacts

A release contains:

- source, task, ontology and schema bundles;
- the public task-set commitment and scorer version;
- fixture and bridge-test outputs;
- the benchmark assurance result and release-blocker state;
- a dependency-aware SPDX SBOM;
- a content-addressed release manifest;
- W3C PROV and RO-Crate research-object metadata where applicable;
- exact container and build metadata;
- clean-clone verification evidence;
- benchmark, data and scorer cards;
- citation metadata and SHA-256 checksums;
- signed GitHub attestations when the remote release workflow is available.

Sealed task bytes remain outside public artifacts until retirement. A release workflow or attestation file is only implementation evidence. It becomes operational evidence after the workflow has run successfully against the published commit and tag.
