# V1 MVP contract

PelicanBench V1 is a minimum viable **empirical benchmark**, not the full long-term suite.
The software can mature through alpha releases before V1, but V1 itself must support the
inferences made in its benchmark card.

## Normative V1 scope

V1 covers one-shot SVG generation only:

- the exact Simon Willison heritage prompt, reported separately;
- 16 prospective semantic scenarios with two prompt formulations each;
- four mobility-interface strata;
- four to six prespecified model systems;
- at least three retained replicates per model-task condition;
- secure source inspection and canonical rendering;
- source-independent atomic semantic assessment;
- blinded human calibration on a stratified subset;
- multidimensional scores, conjunctive success and uncertainty; and
- immutable, reproducible run packages.

Repair, direct raster generation, agentic drawing, accessibility, video and 3D remain
separate experimental V1.x or later tracks. Their scaffolds may ship earlier, but they do
not enlarge the V1 claim.

## Required engineering contracts

- Stable scenario, prompt, condition, trial, artifact and evaluation identities.
- Typed schemas and an affordance-aware animal, object and interface grammar.
- Bounded SVG parsing with explicit failure reasons.
- Canonical pixel-derived render hashes.
- A source, render and semantic evidence firewall.
- Complete trial and failure retention.
- Content-addressed manifests, W3C PROV JSON-LD, RO-Crate metadata and reproduction script.
- Evidence-aware Conductor phases and cross-track release blockers.
- SHA-pinned CI, rights audit, repository validator and deterministic fixture demo.
- GitHub and Hugging Face publication with immutable revisions.

## V1 release gates

V1 requires:

1. No known critical scorer exploit.
2. Prespecified scorer invariance and metamorphic tests.
3. Completion of the prospective multi-model pilot.
4. Human calibration of principal automatic dimensions.
5. Uncertainty and sensitivity analyses.
6. Clean-clone reproduction in a second environment.
7. Successful remote CI, release and provenance attestations.
8. Rights-cleared publication boundaries and participant governance.
9. An immutable release with benchmark, data, scorer and limitations cards.
10. Closure of `RB-01` through `RB-05` in
    [`conductor/release-blockers.json`](../conductor/release-blockers.json).

## Explicit exclusions

V1 does not claim:

- evaluation of every model on Hugging Face;
- absence of training contamination;
- a definitive universal ranking of visual systems;
- redistribution rights over third-party historical artifacts;
- equivalence between one-shot generators and tool-using agents; or
- mature evidence for persistent learning, accessibility, video or 3D.

The `v0.3-alpha` profile is the current E2 fixture-verified precursor. It adds
ecosystem, model-qualification, publication and human-rating exchange evidence to the
`v0.2` measurement-validity foundation. Run
`pelicanbench release-readiness --profile v1.0` to inspect the current gap.
