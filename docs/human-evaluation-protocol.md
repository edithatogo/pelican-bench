# Human evaluation and calibration protocol

## Purpose

Human evaluation tests whether automatic scores correspond to immediate scene recognition, animal anatomy, mobile-object mechanics, interaction correctness and overall preference. It is calibration evidence, not a decorative popularity vote.

## Three-stage order

### Stage 1: blind open-set recognition

Raters see only the canonical render. They identify the animal, mobile object, interaction and facing direction in free text and record confidence. The prompt, model, source SVG and automatic scores remain hidden.

The response is locked before Stage 2. This is the direct test of whether the image itself communicates “pelican”, “bicycle” and “riding”, rather than whether a prompted rater can locate expected features.

### Stage 2: prompt-aware criterion assessment

After the blind response is immutable, the prompt is disclosed. Raters name concrete animal, object and interaction defects before assigning separate 1–5 ratings. Visibility and occlusion rules prevent absent-but-hidden parts from being counted as defects.

### Stage 3: blinded pairwise preference

Two artifacts generated for the same task are shown as A and B with randomised orientation. Model identities remain hidden. Criterion-specific comparisons are kept separate from overall preference.

## Prespecified sampling

Candidate artifacts are stratified by:

- interface class;
- model system;
- automatic-score band;
- judge-disagreement band; and
- valid versus invalid output status.

Selection is deterministic from a frozen seed. Invalid, boundary and high-disagreement cases are deliberately represented. Ten per cent of artifact assignments are repeated without warning to estimate within-rater consistency.

The planning target is 96 artifacts: four artifacts for each of six core models in each of four interface strata. This is not the final power calculation for every hierarchical effect. It gives approximately ±0.10 precision for a worst-case binary recognition proportion at 95% confidence before clustering and design effects, so the final protocol must reassess the effective sample size.

## Panels

The proposed V1 design uses:

- a general-public panel for blind recognisability, prompt-aware criteria and preference;
- a small illustration/design panel for prompt-aware execution quality;
- an ornithology or avian-anatomy panel restricted to avian tasks; and
- a mobile-object mechanics/engineering panel.

Panel size, eligibility, compensation, recruitment channel, subgroup feasibility and exclusion criteria are fixed before collection. Expert labels do not automatically supersede public recognition; they answer different questions.

The current 96-artifact planning fixture generates 1,987 assignments after duplicate tasks and 240 criterion-specific pairwise comparisons. The indicative workload is approximately 32.3 rater-hours: 18.1 public, 5.1 illustration, 3.9 ornithology and 5.3 mechanics. These are planning assumptions, not contracted panel costs.

## Privacy-minimised exchange

`pelicanbench plan-human-calibration-study` exports:

- `assignments.csv`;
- `study-spec.json` and `study-plan.json`;
- `data-dictionary.json`;
- `artifact-manifest.template.json`;
- `response.schema.json`;
- a participant-information and consent template;
- a production checklist; and
- a handling README.

The released table permits only stable assignment, artifact and task identifiers; criterion responses; panel; consent version; and a salted one-way rater hash. Names, emails, phone numbers, addresses, IP addresses, user agents and unnecessary free text are prohibited. Recruitment identifiers and artifact URL resolution remain outside the released research table.

A reference-only Gradio interface is provided under `hf/human-calibration/`. It demonstrates stage gating and schema validation but has no recruitment, consent, persistence, authentication or approved research store. It must not be used as the production study without those controls.

## Reliability and calibration outcomes

The implemented analysis surfaces include:

- open-set recognition accuracy after prespecified entity normalisation;
- confidence calibration, Brier score and expected calibration error;
- nominal Krippendorff alpha for categorical recognition;
- duplicate-assignment consistency;
- criterion-specific Bradley–Terry scores;
- observed agreement and kappa for replicated pairwise ratings; and
- explicit insufficient-evidence states.

The confirmatory model should account for task, prompt, model, replicate, rater, panel and judge family. Results include uncertainty intervals, probabilities of superiority, disagreement, exclusions, missingness and rank sensitivity.

## Automatic-judge calibration

At least two model families perform blind extraction and at least three perform prompt-aware atomic judging. Same-family and generator-family sensitivity are reported separately. Automatic probabilities are compared with human binary and ordinal outcomes rather than treated as ground truth. Disagreement and confidence-boundary cases are oversampled in the human study.

## Quality, governance and ethics

Before recruitment, the project records the applicable ethics or governance determination, responsible institution, lawful and ethical basis, participant information and consent, compensation, image content, data retention, withdrawal window, privacy, accessibility and adverse-event arrangements. Attention checks are transparent rather than deceptive. Exclusion and expert-adjudication rules are frozen before outcome analysis.

No human-calibration criterion is marked complete merely because sampling, exchange, interface or analysis software exists.

## Current status

The three-stage protocol, expert eligibility filters, deterministic sampler, blinded pair generator, duplicate assignments, privacy-minimised exchange, reference UI, workload estimator, pairwise model and calibration metrics are E2 fixture-verified. No participants have been recruited and no human ratings have been collected. Participant governance, empirical judge calibration and E3 validity evidence remain open under RB-01, RB-03 and RB-05.
