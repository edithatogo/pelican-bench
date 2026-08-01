# Human evaluation and calibration protocol

## Purpose

Human evaluation determines whether automatic scores correspond to immediate scene
recognition, animal anatomy, mobile-object mechanics, interaction correctness and overall
preference. It is calibration evidence, not a decorative popularity vote.

## Prespecified sampling

Candidate artifacts are stratified by:

- interface class;
- model system;
- automatic-score band;
- judge-disagreement band; and
- valid versus invalid output status.

Selection is deterministic from a frozen seed. Within each task, cross-model pairs are
created with stable identities and randomised left/right presentation. Invalid, boundary
and high-disagreement cases are deliberately represented.

## Panels

The proposed V1 design uses:

- a general-public panel for recognisability and overall preference;
- a small illustration/design panel;
- an ornithology or avian-anatomy panel; and
- a bicycle-mechanics/engineering panel.

Panel size, eligibility, compensation, recruitment channel, subgroup feasibility and
exclusion criteria are fixed before collection. Expert labels do not automatically
supersede public recognition; they answer different questions.

## Privacy-minimised exchange

`pelicanbench export-human-evaluation-batch` converts the frozen calibration design into:

- `assignments.csv`;
- `data-dictionary.json`;
- `manifest.json`; and
- a handling README.

The V1 table permits only artifact/task identifiers, criterion, A/B/tie response, panel,
consent version and a salted one-way rater hash. Names, emails, phone numbers, addresses,
IP addresses, user agents and unstructured participant notes are prohibited. Artifact IDs
are resolved to controlled presentation URLs outside the released rating table.

This exchange follows the documentation, tabular, provenance and rights-boundary patterns
used in `open_social_data`; it does not claim that repository supplies participant panels
or a human-preference collection service.

## Outcomes

`pelicanbench analyse-human-evaluation`:

- validates the privacy-minimised CSV contract;
- rejects direct-identifier columns;
- fits criterion-specific regularised Bradley-Terry scores;
- estimates observed agreement and kappa when replicate ratings exist; and
- records insufficient-replicate evidence rather than inventing reliability.

The confirmatory analysis should use a hierarchical extension accounting for task, prompt,
rater, model system and judge family. Results include uncertainty intervals, probabilities
of superiority, disagreement, exclusions and rank sensitivity.

## Quality, governance and ethics

Before recruitment, the project records whether formal review is required, the lawful and
ethical basis, participant information and consent, compensation, image content, data
retention, withdrawal, privacy, accessibility and adverse-event arrangements. Attention
checks are transparent rather than deceptive. Exclusion and expert-adjudication rules are
frozen before outcome analysis. Raw participant identities are never published.

No human-calibration criterion is marked complete merely because sampling, exchange or
analysis software exists.

## Current status

The atomic-question schema, deterministic sampler, blinded pair generator,
privacy-minimised exchange, pairwise model and agreement analysis are E2 fixture-verified.
Participant governance, recruitment, rating collection, empirical judge calibration and E3
validity evidence remain open under RB-01, RB-03 and RB-05.
