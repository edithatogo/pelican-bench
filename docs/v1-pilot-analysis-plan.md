# Prespecified V1 candidate pilot and analysis plan

## Status and version control

This plan governs `PB-2026.08-v1-candidate`. The task identity commitment is stored in
[`benchmark/tasks/v1-candidate-commitment.json`](../benchmark/tasks/v1-candidate-commitment.json).
The prior 33-task alpha and its analysis plan are retained through Git history and the
immutable grammar snapshot. Any score-affecting change after the candidate tag requires a
numbered amendment, rationale, updated commitment and paired sensitivity analysis.

No model endpoint has yet been qualified or run under this plan. The committed artifacts
are design and execution contracts, not empirical results.

The inferential inputs are frozen by `benchmark/protocol/v1-study-lock.json`. Changes use
the append-only amendment ledger under `benchmark/protocol/`; the original analysis remains
reportable after every amendment.

## Objectives

The study has three distinct objectives:

1. Preserve longitudinal continuity with the exact public pelican-on-a-bicycle prompt.
2. Replicate an externally observed 8-animal by 6-mobile-object SVG experiment under
   PelicanBench's failure-retaining and measurement-validity controls.
3. Estimate model, animal-body-plan, mobile-object, interface and prompt-formulation effects
   in a balanced primary confirmatory panel.

The three objectives are not combined into one undifferentiated leaderboard.

## Task panels

| Panel | Tasks | Role in inference |
|---|---:|---|
| Heritage anchor | 1 | Public longitudinal result; reported separately |
| Castillo empirical bridge | 48 | Exact replication and external comparability |
| PelicanBench interface-confirmatory panel | 64 | Primary prospective inference |
| **Total** | **113** | 81 semantic scenarios |

The empirical bridge preserves the source prompt wording, eight animals, six objects and
known ambiguity around the word `plane`. Its results are analysed under both the external
study's factorial estimands and PelicanBench's source-independent scorecard.

The confirmatory panel crosses pelican, heron, dog and octopus with eight mobile objects.
Two objects represent each prespecified interface stratum:

1. **Straddle and propel.** Bicycle and unicycle.
2. **Stand and balance.** Electric scooter and skateboard.
3. **Sit inside and control.** Tuk-tuk and go-kart.
4. **Occupy and propel.** Kayak and canoe.

Each semantic scenario has a minimal prompt and an artifact-explicit prompt. The panel is
balanced for animal and object effects within the chosen design; it is not presented as a
random sample of all possible animals, vehicles or user prompts.

## Model cohorts and execution stages

The primary prospective cohort contains six model families. The exact empirical-replication
cohort adds DeepSeek, yielding seven unique candidate endpoints. Each endpoint first
completes the same nine-task canary.

| Stage | Tasks | Models | Replicates | Planned cells |
|---|---:|---:|---:|---:|
| Heritage | 1 | 6 | 3 | 18 |
| Empirical replication | 48 | 7 | 3 | 1,008 |
| Primary confirmatory | 64 | 6 | 3 | 1,152 |
| **Total** | **113** | **7 unique** |  | **2,178** |

Qualification adds 63 model-canary cells. The qualified cohort, exclusions, provider routes,
immutable or best-available provider revisions, terms, prices and runtime deviations are
frozen before the full run.

All completed and failed attempts are retained. There is no best-of selection. Parse
failures, safety rejections, refusals, timeouts and exhausted retries remain denominator
outcomes. A provider retry cannot silently replace an earlier completed generation.

Three replicates are the initial wave, not an unquestioned final sample size. After the
initial confirmatory wave, pooled within-scenario variance and replicate correlation may be
estimated while model labels and comparative effects remain blinded. The project then uses
the prespecified three, five or seven-replicate rule in `benchmark/design/assumptions.json`.
No task, model or outcome can be selected through this reassessment, and the initial-wave
analysis remains mandatory.

Campaign execution uses the content-addressed manifest and append-only event ledger. Cells
remain blocked until model qualification and current price evidence exist. Leasing enforces
per-model concurrency and hard-budget reservations. Blocked and terminal-failure cells
remain visible in the planned denominator.

## Automatic assessment and judge qualification

Source security and artifact-quality diagnostics never supply semantic credit. Canonical
renders are evaluated through:

- at least two family-diverse blind open-set extractors;
- at least three family-diverse prompt-aware atomic judges;
- separate pairwise quality judgements where used; and
- blinded human calibration on a stratified subset.

Every automatic judge must pass technical schema, prompt-leakage, source-independence and
canary-order checks. E3 qualification additionally requires prespecified agreement with
human outcomes. Same-family, generator-family and leave-one-family-out sensitivity are
reported.

The judge-input firewall is a separate critical gate. V1 does not request visible text, so
text-bearing renders are retained but quarantined from automatic semantic judging. This
prevents direct rendered evaluator instructions from receiving semantic credit. Text
converted to vector outlines remains a declared residual risk and must be tested through
render-level judge canaries before E3 promotion.

## Primary outcomes

Primary outcomes are reported as separate dimensions:

- valid and safe artifact production;
- blind animal recognition;
- blind mobile-object recognition;
- blind interaction recognition;
- animal anatomy;
- mobile-object mechanics;
- support, control and propulsion contact correctness;
- instruction coverage;
- artifact quality and editability diagnostics; and
- conjunctive critical success.

The aggregate score is secondary. Invalid-output frequency and quality conditional on a
valid output are both reported; neither replaces the other.

## Human calibration

Human assessment occurs in a locked three-stage order:

1. Blind open-set recognition and confidence before the prompt is visible.
2. Prompt-aware defect naming followed by separate 1–5 animal, object and interaction
   ratings.
3. Blinded within-task pairwise preference.

The planning target is 96 artifacts, balanced over the six core models and four interface
strata, with deliberate representation of invalid, boundary and high-disagreement cases.
Ten per cent of assignments are repeated without warning to estimate within-rater
consistency. Public, illustration, avian-anatomy and vehicle-mechanics panels answer
separate questions and are not collapsed without panel effects.

Governance, consent, recruitment, compensation and data-retention decisions must be
approved before collection. The reference application is not an approved production study.

Original ratings are never overwritten by adjudication. A content-addressed queue identifies
low-agreement open-set labels, low-confidence recognition and wide criterion-rating ranges.
Collection may stop only when the prespecified workload, invalid-response, Brier-score,
inter-rater agreement and duplicate-consistency gates all pass.

## Statistical analysis

The principal confirmatory analysis is cross-classified by model system, animal,
mobile object, interface relation, prompt formulation, scenario and replicate. Human and
automatic-judge analyses additionally include rater, panel, judge and judge-family effects.

Reported outputs include:

- dimension estimates with uncertainty;
- conjunctive success rates;
- model-by-interface interactions;
- animal, object and prompt effects;
- replicate reliability;
- confidence calibration and Brier score;
- human-judge agreement and disagreement;
- probability of superiority and rank intervals;
- cost and latency distributions; and
- the Pelicanmaxxing interaction after adjustment for general animal, bicycle and
  interface performance.

The exact bridge additionally reports the source-study row, column and pelican-bicycle
interaction estimands. The confirmatory panel is the principal generalisation result.

## Sensitivity analyses

- Exclude the public heritage task.
- Analyse the exact replication panel separately from the confirmatory panel.
- Vary automatic-judge family composition and exclude same-family judges.
- Use human-only semantic outcomes on the calibration subset.
- Vary composite weights while retaining the full score vector.
- Treat invalid outputs as zero versus separate validity and conditional quality.
- Compare minimal and artifact-explicit prompts.
- Compare first-attempt success with eventual success after retained retries.
- Compare canonical and bridge renderers where materially different.
- Repeat the primary model after excluding tasks or judges with inadequate reliability.
- Report the initial three-replicate wave, the blinded reassessment inputs and the achieved
  replicate wave separately.
- Report automatic semantic results with quarantined judge-input artifacts treated as
  failures and as a separate outcome class.

## Missingness, deviations and interpretation

Generation failures are outcomes. Judge and human missingness are reported with explicit
denominators and reasons. No artifact is removed because it is unattractive or surprising.
All protocol deviations are timestamped before unblinding where possible and accompanied by
the originally prespecified analysis.

The campaign event chain is the operational record of leasing, success, failure,
quarantine, cancellation and cost. Protocol-lock verification, campaign identity and task
commitment must pass before the main comparative campaign begins.

The pilot estimates performance for the recorded prompts, providers, revisions and dates.
It does not prove absence of contamination, establish universal visual intelligence, or
justify combining direct generation with tool-using agent performance.

## Blinded replicate decision

The campaign begins with three replicates. Before model or provider identities are joined
to outcome data, opaque complete clusters are analysed under the locked reassessment
policy. The decision may retain three replicates or add a content-addressed wave to five or
seven. The input hash, ICC estimate and bounds, option table and wave commitment will be
reported. No aggregate model score or ranking may enter this decision.

### Attempt-level execution denominator

Operational reporting uses leased attempts as well as planned cells. Every worker terminal
event must reconcile to one immutable attempt record. Retries do not replace earlier
failures. The report will provide planned cells, leased attempts, successful artifacts,
quarantined artifacts, provider failures, infrastructure failures, retry counts, total
charged cost and reconciliation exceptions separately.
