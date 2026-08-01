# Prespecified V1 pilot and analysis plan

## Status

This plan is frozen for the first prospective pilot once a release commit and task-set
commitment are published. Changes after that point require an amendment with a timestamp,
rationale and sensitivity analysis.

## Objective

Estimate how representative model systems perform on one-shot SVG generation across four
mobility-interface strata while preserving repeated samples, prompt variants and
multidimensional outcomes.

## Task set

The committed design contains 16 prospective scenarios with two prompt formulations each,
plus the exact heritage prompt, for 33 tasks in total. The task commitment is stored in
[`benchmark/tasks/v1-pilot-commitment.json`](../benchmark/tasks/v1-pilot-commitment.json).

The four strata are:

1. **Straddle and propel:** bicycle, unicycle, cargo bicycle and tricycle.
2. **Stand and balance:** electric scooter and skateboard.
3. **Sit inside and control:** tuk-tuk and go-kart.
4. **Occupy and propel:** kayak.

Animals are pelican, flamingo, dog and octopus. This deliberately varies body plan,
control capability and the amount of anthropomorphic adaptation required.

## Systems and replication

- Four to six representative systems selected before the principal run.
- Exact model revision, provider, endpoint, harness, sampling configuration and date
  recorded.
- At least three retained generations per model-task condition.
- No best-of selection. Parse failures and refusals remain in the denominator.
- Provider retries are recorded and do not silently replace a completed generation.

## Primary outcomes

The primary result is the multidimensional scorecard:

- artifact integrity;
- animal recognisability and anatomy;
- mobile-object recognisability and mechanics;
- interaction correctness;
- instruction coverage;
- composition;
- artifact quality; and
- conjunctive critical success.

The aggregate score is secondary. The public heritage prompt is reported separately and is
excluded from the primary generalisation estimate.

## Human calibration

At least 64 artifacts will be sampled, stratified by interface class, model, automatic-score
boundary and judge disagreement. General raters assess recognisability, interaction and
overall preference. Smaller expert panels may assess pelican anatomy, vehicle mechanics and
vector editability.

Pairwise comparisons are preferred for preference. Atomic criterion ratings are used for
calibration of semantic questions. Raters are blinded to model and provider.

## Statistical analysis

The primary model is cross-classified by model system, animal, mobile object, interface
relation, prompt variant, scenario and replicate. Human analyses additionally model rater
and panel effects. Outputs include:

- dimension estimates with uncertainty;
- conjunctive success rates;
- model-by-interface interactions;
- replicate reliability;
- prompt sensitivity;
- probability of superiority;
- rank intervals rather than point ranks alone; and
- the Pelicanmaxxing interaction after adjustment for animal, object and relation effects.

The implementation provides stratified bootstrap estimates and empirical-Bayes partial
pooling for the pilot. A later preregistered analysis may use a Bayesian multilevel model,
provided both the originally specified and amended analyses are published.

## Sensitivity analyses

- Exclude the public heritage task.
- Vary automatic-judge family composition.
- Use human-only semantic outcomes on the calibration subset.
- Vary composite weights and report the full score vector.
- Treat invalid outputs as zero versus report validity and conditional quality separately.
- Compare prompt formulations.
- Compare CairoSVG and Inkscape bridge renders where they materially differ.

## Missing data and failures

Refusals, timeouts, malformed SVG and unsafe SVG are outcome states, not missing data.
Missing human ratings are modelled or reported with denominators. No artifact is removed
because it is unattractive or because the evaluator expected a better model result.

## Interpretation

The pilot estimates performance under the recorded providers, prompts and revisions. It
does not prove absence of benchmark contamination, establish general image-generation
ability or justify ranking direct generators against tool-using agents.
