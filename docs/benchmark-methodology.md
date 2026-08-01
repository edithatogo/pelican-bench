# Benchmark methodology

## Intended inference

PelicanBench estimates how reliably a specified model system, provider, harness and
configuration can produce a visible and editable depiction of an animal interacting with a
mobile non-living object under a recorded task condition. It does not estimate a model's
universal artistic ability.

## Experimental identities

The data model separates:

- **scenario:** semantic scene graph;
- **prompt:** exact verbalisation;
- **condition:** one-shot, reference-assisted, repair or agentic intervention;
- **trial:** model invocation, revision, seed and provider settings;
- **artifact:** content-addressed output;
- **evaluation:** scorer and judge application to an artifact; and
- **run:** immutable collection of tasks, trials, evaluations and provenance.

Trial randomness never changes scenario or prompt identity. This preserves replicate and
item effects.

## Tracks are not interchangeable

Direct SVG generation, direct raster generation, reference-grounded generation,
repair/editing and agentic drawing are reported separately. A system that receives tools,
references or iterative feedback is not ranked as though it completed a one-shot task.

## Affordance-aware task design

Tasks are stratified by the physical interface between animal and mobile object rather than
formed as an arbitrary cross-product. The V1 strata cover straddling and propulsion,
standing and balance, sitting inside and control, and occupancy with propulsion. Ontologies
record body plan, contact capabilities, support, control, containment and propulsion
requirements.

## Evidence layers

1. **Security:** source may be safely parsed and rendered.
2. **Artifact quality:** grouping, portability, editability and implementation diagnostics.
3. **Canonical render:** a fixed pixel-derived representation and low-level visible features.
4. **Constituents:** animal and object are visibly recognisable with relevant features.
5. **Relations:** riding, driving, operating, towing or passenger occupancy is depicted.
6. **Instruction coverage:** atomic requested properties are satisfied.
7. **Visual quality:** composition and coherence.
8. **Reliability and efficiency:** repeated samples, latency, tokens, cost and actions.
9. **Provenance:** immutable task, model, harness, scorer and environment identity.

The source, render and semantic channels are isolated. Submission-controlled SVG labels
cannot establish visual semantics.

## Score reporting

The primary output is a versioned score vector with critical gates and uncertainty. A
composite is optional and secondary. Conjunctive success is the fraction of outputs meeting
all critical thresholds. Invalid outputs and refusals remain in the denominator.

## Automatic semantic assessment

Atomic questions are answered from the canonical render by family-diverse judges. No judge
receives SVG source. Judge revision, prompt, calibration and confidence are recorded. High
disagreement cases are routed to human assessment. Source-independent assessment is bound
to the exact render hash and cannot be reused after an artifact changes.

## Human calibration

General raters assess recognisability, interaction and preference. Smaller expert panels
may assess animal anatomy, vehicle mechanics and editability. Raters are blinded to model
identity. Pairwise comparison is preferred for preference, while atomic criterion ratings
calibrate automatic questions. The analysis models rater, task, prompt and system effects.

## Statistical analysis

The prospective pilot uses repeated model-task trials. Analysis accounts for animal,
mobile object, interface relation, prompt variant, scenario and replicate structure.
Outputs include uncertainty, probability of superiority, rank intervals, replicate
reliability and sensitivity to judge composition and score weights.

The Pelicanmaxxing Index is the pelican-by-bicycle interaction after adjustment for general
animal, object and relation performance. It is not evidence that a model was intentionally
trained on the prompt.

## Historical analysis

The Simon Willison archive is an observational Pelican Chronicle, not a controlled model
comparison. Original prompts, dates, harnesses, selected examples and available settings
are preserved. Historical commentary is a source-derived annotation layer rather than
ground truth. Prospective bridge runs quantify scorer drift.

## Reproducibility

Every run bundle contains task and scorer versions, Git commit, model and provider revision,
settings, seeds, successful and failed trial records, raw output where available, canonical
render, semantic assessment, costs, environment identity, artifacts, hashes, W3C PROV
JSON-LD, RO-Crate metadata and reproduction commands. Bounded retry and checkpoint layers
record their attempts and prevent duplicate completed calls. Entire development sessions
supplement but do not replace run provenance.
