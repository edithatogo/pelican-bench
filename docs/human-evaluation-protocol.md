# Human evaluation protocol

## Objectives

Human evaluation calibrates automatic scores, estimates recognisability and preference, identifies systematic judge failures, and quantifies disagreement about anatomy, mechanics, interaction and editability. It does not merely provide a second aesthetic leaderboard.

## Design

Participants receive blinded, randomised comparisons within the same task and condition. Model, provider, price and automatic score are hidden. The general panel assesses immediate animal/object recognition, relation correctness and overall preference. Smaller expert panels may assess illustration/vector quality, relevant animal anatomy and vehicle mechanics.

Atomic criterion ratings and pairwise preference answer different questions and are retained separately.

## Deterministic calibration sampling

`pelicanbench design-human-calibration` implements the prespecified sampling contract. Candidate artifacts are stratified across:

- interface class;
- model system;
- low, boundary and high automatic-score bands;
- low and high judge-disagreement bands; and
- invalid or failed artifacts.

The sampler first seeks balanced stratum coverage, then fills the target deterministically. Within-task cross-model pairs are generated with stable identifiers and a bounded number of pairs. The selected sample and pair file are versioned before ratings are collected.

The design deliberately oversamples threshold cases, automatic-judge disagreement, rare interface types, apparent proxy gaming and generator–judge family overlap. Anchor duplicates estimate within-rater reliability. Left/right presentation order is randomised at delivery without changing pair identity.

## Outcomes

Pairwise votes are fitted with a regularised Bradley–Terry model and, at scale, a hierarchical extension accounting for task, rater, prompt, model system and judge family. Atomic criterion ratings estimate question-level calibration and error. Results include intervals, probability of superiority, disagreement, sensitivity to exclusions and rank uncertainty.

## Quality, governance and ethics

Before recruitment, the project records whether formal review is required, the lawful and ethical basis for the work, consent language, compensation, image content, data retention, withdrawal, privacy and accessibility arrangements. Attention checks are transparent rather than deceptive. Exclusion and expert-adjudication rules are frozen before outcome analysis. Raw participant identities are not published.

No human-calibration criterion is marked complete merely because the software for sampling or analysis exists.

## V1 status

The atomic-question schema, deterministic stratified sampler, blinded pair generator, pairwise model and calibration utilities are E2 fixture-verified. Participant governance, recruitment, rating collection, empirical judge calibration and E3 validity evidence remain open under RB-01, RB-03 and RB-05.
