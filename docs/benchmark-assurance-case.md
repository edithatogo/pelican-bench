# Benchmark assurance case

PelicanBench uses an explicit claim, argument and evidence structure so repository activity
cannot be mistaken for benchmark validity. The normative machine-readable record is
[`benchmark/assurance-case.json`](../benchmark/assurance-case.json).

## Top-level claim

> PelicanBench can support reproducible and appropriately qualified comparisons of systems
> asked to create an animal interacting with a mobile non-living object.

This claim is decomposed into source-independent measurement, stable experimental
identities, affordance-aware task coverage, reproducible execution, appropriate statistics,
human alignment, rights-aware governance and bounded treatment of untrusted artifacts.

## Current assurance position

The v0.2 alpha profile targets **E2, fixture-verified** measurement evidence. The v0.3
profile adds auditable first-party ecosystem boundaries, ordinary qualification gates,
deterministic publication hand-offs, formal but bounded ontology interoperability and
privacy-minimised human-rating exchange. The current v0.4 profile additionally requires
the committed candidate task set, exact empirical prompt bridge, deterministic model and
judge qualification plans, staged human-calibration workflow and repository-native quality
gates. None of these alpha profiles claims that automatic scores are aligned with people
or that model rankings are empirically valid.

The v1.0 profile requires **E3, empirically calibrated** evidence for all primary claims,
plus closure of the five release blockers:

1. Measurement validity.
2. Prospective V1 pilot.
3. Human and judge calibration.
4. Independent reproducibility and remote publication.
5. Rights and research governance.

## Defeaters and reopening

Every claim lists plausible defeaters. Discovery of a credible defeater reopens the claim
and any linked Conductor phase. The source-label scoring exploit is retained as a permanent
regression case. It demonstrates why a high test count is not itself evidence of construct
validity.

## Release evaluation

Run:

```bash
pelicanbench release-readiness --profile v0.2-alpha
pelicanbench release-readiness --profile v0.4-alpha
pelicanbench release-readiness --profile v1.0
```

The command checks declared evidence levels, required claim status, evidence-path existence
and release-blocker state. It deliberately does not infer human validity from code.
