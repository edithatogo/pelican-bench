# Human evaluation protocol

## Objectives

Calibrate automatic scores, estimate recognisability and preference, identify systematic judge failures, and quantify expert disagreement about anatomy, mechanics, interaction, and editability.

## Design

Participants receive blinded, randomised pairwise comparisons within the same task and intervention stratum. The general panel rates immediate recognisability and overall preference. Smaller expert panels include illustration/vector-art, relevant animal anatomy, and vehicle/mechanical expertise. A participant does not see provider or model identity.

## Sampling

The sample oversamples automatic-judge disagreement, threshold cases, rare interface types, apparent proxy gaming, and model-family self-evaluation. Anchor duplicates estimate within-rater reliability. Presentation side is randomised.

## Outcomes

Pairwise votes are fitted with a regularised Bradley–Terry model and, at scale, a hierarchical extension accounting for task, rater, prompt, system, and judge family. Estimates include intervals and probability of superiority. Raw identities are not published.

## Quality and ethics

Consent describes image content, data retention, compensation, and withdrawal. Attention checks are transparent rather than deceptive. Exclusion rules and expert adjudication are preregistered. Accessibility accommodations are built into the interface.

## V1 status

The schema, atomic-question generator, pairwise model, and calibration functions are implemented. Recruitment, ethics review where required, and empirical calibration remain P2 work.
