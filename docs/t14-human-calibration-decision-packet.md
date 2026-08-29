# T14 human-calibration decision packet

This packet prepares the remaining T14/P2 validation decision. It does not claim that
human ratings exist or that the render-bound repair metrics are calibrated. The benchmark
steward is the sole human decision-maker; a panel of separately run agents provides advice
before the decision.

## Decision requested

Choose whether to authorize the prespecified human-calibration study for T14, defer it while
revising the design, or reject the current metric promotion proposal. No option promotes
`score_repair_render` to a normative or release score without the resulting human evidence.

## Bound study design

- Study protocol: `docs/human-evaluation-protocol.md`.
- Existing sampling and workload contract: `benchmark/human-calibration/study-spec.json`.
- Repair fixtures: `benchmark/fixtures/repair/tasks.json` and referenced SVGs.
- Current readiness snapshot: `benchmark/evidence/snapshots/t14-calibration-pilot-readiness.json`.
- Development-only blind manifest: `benchmark/evidence/snapshots/t14-blinded-pilot-manifest.json`.
- Steward response template: `benchmark/evidence/snapshots/t14-human-rating-response-template.json`.
- Template validator: `scripts/validate_t14_rating_template.py`.
- Metrics under review: `foreground_retention_fraction`, `added_ink_fraction`,
  `edit_locality`, `introduced_components`, and `diff_pixel_fraction`.
- Required outcomes: blinded defect recognition, targeted-correction success,
  preservation of correct regions, introduced-defect detection, inter-rater agreement,
  uncertainty intervals, adjudication, and held-out metric/human alignment.
- Agent-panel recommendation: use up to 96 project-original repair episodes, stratified by
  defect family, severity, edit geometry, score band, and boundary/invalid cases; reserve a
  held-out set before rating (recommended 72 development / 24 held-out) and include 10%
  randomized duplicate episodes for within-rater consistency.
- The sole human rater sees blinded before/after canonical renders first, records target
  correction, preservation, introduced defect, confidence, and uncertainty, then receives
  only the predeclared task criteria after the first response is locked. Automatic scores,
  model identity, source labels, and agent recommendations remain hidden during primary
  ratings.
- With one human rater, report test–retest consistency only. Do not claim inter-rater
  agreement, independent adjudication, or independent human validation.

## Agent-panel submission

Each agent run must use the frozen packet revision, record its own evidence chain, and return
the following without credentials, participant data, or restricted source bytes:

```yaml
agent_id: "<stable run id>"
evidence_revision: "<40-character commit>"
role: "t14-calibration-adviser"
conflict_declaration: "none | declared"
methods: "<design, metric, governance, or statistical review performed>"
findings: []
risks: []
options:
  - id: "authorize | revise | defer | reject"
    rationale: "<bounded recommendation>"
recommendation: "<option id>"
limitations: []
receipt_sha256: "<64 lowercase hex characters>"
```

The packet preparer reconciles disagreements explicitly. Agent consensus is advice only and
cannot satisfy human-judgement evidence, independent approval, or release authorization.

## Sole human decision

```yaml
decision_maker: "benchmark-steward"
decision: "authorize"
decision_at: "2026-08-20T12:15:00Z"
rationale: "Approve a bounded, blinded T14 calibration pilot over project-original repair fixtures only. The agent panel recommends the sample, rubric, exclusions, analysis, and score-compatibility treatment; the benchmark steward is the sole human rater and decision-maker. Agent outputs are advisory and cannot be represented as human ratings, independent approval, or E3 evidence. Until the steward's ratings and hash-bound analysis are complete, T14 remains P2-partial and score compatibility remains none-until-normative-release."
conditions: []
signature_receipt_sha256: "13d48c64ec74b0a120f18fba1619037d90fc377968d2b83fb7868967cfeb84f9"
```

The steward has authorized the pilot. Authorization does not constitute calibration evidence
or promote T14/P2; the evidence gates below remain open until the rating and analysis receipts
are complete.

## Evidence and promotion gates

- [x] Panel packets cover design, metric validity, governance/privacy, and statistical power.
- [x] The steward records the D044 procedural E2 freeze decision and its conditions.
- [x] The protocol and exact 96-episode sample are frozen as procedural, non-independent E2
  preparation before collection.
- [ ] Human ratings are collected under the approved governance and blinded stages.
- [ ] Results include agreement, uncertainty, adjudication, missingness, and held-out
  alignment of automatic metrics with human outcomes.
- [ ] If the steward chooses the proposed thresholds, held-out target-correction/no-new-
  defect AUC is at least 0.80 (lower bootstrap bound at least 0.70), preservation/locality
  Spearman correlation is at least 0.70 (lower bound at least 0.50), duplicate consistency
  is at least 0.80, and invalid/omitted responses are at most 5%. Thresholds must be fixed
  by the steward before rating and must not be tuned on held-out results.
- [ ] Only after those results pass the stated thresholds may T14/P2 be promoted.

Current status is **procedurally frozen / E2 / ratings not authorized**. D044 binds 96
project-original episodes in 24 scene clusters, the 18/6 whole-cluster allocation, 10
duplicate assignments, the protocol, prospective analysis, renderer lock, custody receipts,
and advisory packets. No fixture, agent-panel, or synthetic result closes the human-
calibration gate.

The earlier two-episode blind manifest and response remain historical rehearsal evidence
only. The authorization-gated frozen interface consumes the restricted 106-assignment
schedule without exposing source identifiers, duplicate identity, allocation, or scores.
Collection cannot begin until the benchmark steward supplies a separate, exact-hash rating
authorization receipt.

## Panel recommendation returned to the steward

> Approve a bounded, blinded T14 calibration pilot over project-original repair fixtures only.
> The agent panel recommends the sample, rubric, exclusions, analysis, and score-compatibility
> treatment; the benchmark steward is the sole human rater and decision-maker. Agent outputs
> are advisory and cannot be represented as human ratings, independent approval, or E3
> evidence. Until the steward's ratings and hash-bound analysis are complete, T14 remains
> P2-partial and score compatibility remains `none-until-normative-release`.
