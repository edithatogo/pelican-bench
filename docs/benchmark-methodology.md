# Benchmark methodology

## Tracks are not interchangeable

PelicanBench reports direct SVG generation, direct raster generation,
reference-grounded generation, repair/editing and agentic drawing separately.
A system that receives tools, references or iterative feedback is not ranked as
though it completed the same intervention as a one-shot generator.

## Evaluation layers

1. **Integrity:** valid allowed artifact; no scripts, external resources,
   embedded raster shortcut, hidden judge instructions or resource-limit breach.
2. **Constituents:** animal and object exist with required parts.
3. **Relations:** the requested role is depicted, such as riding, driving,
   piloting, towing or passenger occupancy.
4. **Instruction coverage:** atomic requested properties are satisfied.
5. **Visual quality:** composition, coherence and recognisability.
6. **Artifact quality:** editability, locality, grouping and renderer stability.
7. **Reliability and efficiency:** repeated samples, latency, tokens, cost and
   tool actions.
8. **Provenance:** immutable task, model, harness, scorer and environment identity.

## Score reporting

The primary result is a versioned scorecard with dimension estimates, failure
reasons and uncertainty. A composite is optional, secondary and cannot override
critical gates. Conjunctive success is the fraction of outputs exceeding all
critical thresholds.

## Automatic scoring

Deterministic checks analyse source, structure and geometry. Semantic assessment
uses atomic questions and blind descriptions, ideally from multiple judge
families. No judge evaluates its own family without disclosure and sensitivity
analysis. Learned scorers are frozen by revision and calibrated against people.

## Human calibration

Pairwise blinded comparison is the default because it is easier to interpret
than absolute ratings. A general panel assesses recognisability and preference;
smaller expert panels assess pelican anatomy, bicycle/tuk-tuk mechanics and
illustration/editability. Disagreements and automatic-judge boundary cases are
oversampled. Hierarchical models account for rater, task, prompt and system effects.

## Dynamic challenge design

The public anchor and public development set are stable. Primary challenge tasks
are sampled from typed ontologies, parameterised by role, view, scale, count,
occlusion, style, reference condition and interaction difficulty. Challenge
items may be delayed-release or remotely held, then retired into the public set.

## Longitudinal inference

Historical observations are analysed with their original prompts, dates,
harnesses and available settings. They are not retroactively treated as a
controlled model comparison. Prospective bridge runs quantify scorer drift and
changes in task difficulty.

## Reproducibility

Every run bundle contains task and scorer versions, git commit, dataset revision,
model revision, provider, prompt, settings, seeds, environment/container digest,
raw output, canonical render, measurements, judge revisions, cost and hashes.
Entire development sessions supplement but never replace this manifest.
