# T14 remaining-gate decision packet (2026-08-29)

**Status:** recommended preparation slate approved by the benchmark steward;
implementation preparation only. No normative freeze, human rating, score promotion,
attestation, release, publication, or unblinding is authorized by this packet.

**Repository basis:** `988281cd88abff929371bd58138f97c1da4acc99`
(`origin/main` after PR #174).

## Why a decision is required

The prepared package contains 96 project-original episodes and a proposed
72/24 development/held-out split. It is deterministic and locally validated,
but it is not ready to freeze as a normative calibration sample:

- the 96 episodes contain only 12 scene clusters;
- the held-out partition contains only three independent scene clusters;
- vehicle-family labels do not currently represent distinct topology;
- severity is completely confounded with defect family; and
- invalid, boundary, under-repair, over-edit, and introduced-defect cases are
  not represented as a separately governed diagnostic suite.

Episode-level inference would therefore be pseudoreplication. The current
candidate can support a narrow descriptive pilot, but not strong calibration
or score-promotion claims.

## Panel recommendation

The separately run design, statistics, and governance agent reviews agree that the
candidate should be revised before freeze, remain exactly 96 normative
episodes, retain a whole-cluster 72/24 split, cross severity within defect
family, and gain a separate non-normative diagnostic package. The panel
disagrees only on whether to keep 12 complete eight-defect scene blocks or use
24 four-defect scene blocks. The statistics recommendation is preferred here
because it doubles independent clusters and held-out support without increasing
the human-rating workload.

## Decisions

### D-T14-01: normative episode architecture

**A. 24 scene clusters x 4 episodes; 18/6 cluster split (recommended).**

- Trade-off: strongest generalisation and uncertainty design available within
  96 ratings; six held-out clusters remain modest, but are materially better
  than three. Each scene does not contain all eight defect families.
- Controls: each defect family appears 12 times overall and 9/3 across the
  development/held-out partitions; allocation is deterministic and frozen
  before ratings.
- Contingency: if a balanced allocation or semantically valid repair cannot be
  constructed, stop and return a revised allocation rather than omit cells.

**B. 12 scene clusters x 8 episodes; 9/3 cluster split.**

- Trade-off: preserves a complete eight-family block in every scene and makes
  within-scene comparisons simple, but leaves only three held-out clusters and
  unstable cluster-level uncertainty.
- Contingency: restrict all eventual claims to a descriptive pilot; do not use
  lower-bound promotion gates as if 96 episodes were independent.

**C. expand beyond 96.**

- Trade-off: potentially best precision and factorial coverage, but increases
  human workload and invalidates the prepared workload and allocation plan.
- Contingency: require a prospective simulation over plausible prevalence,
  intracluster correlation, and effect sizes before selecting the new size.

**Recommendation and rationale:** choose A. Calibration depends on independent
scene generalisation, and four defects per scene still permits exact aggregate
family balance.

### D-T14-02: geometry and severity revision

**A. visibly distinct topology/layout and crossed severity (recommended).**

- Use at least four structurally different vehicle templates and multiple
  layouts. Validate inspected geometry and render commitments, not metadata.
- Give every defect family prespecified moderate and severe manipulations, with
  six instances of each severity overall and a deterministic rotating
  allocation across partitions.
- Trade-off: invalidates current candidate byte/render commitments and requires
  regeneration, tests, a fresh panel review, and a later exact-hash freeze.
- Contingency: if a family cannot support two meaningful severity levels on a
  topology, revise the template or family; do not manufacture severity labels.

**B. retain current geometry and waive the limitations.**

- Trade-off: fastest and preserves current bytes, but vehicle and severity
  effects are not identifiable and claims must be narrowly descriptive.

**C. remove severity and vehicle comparisons from the confirmatory estimand.**

- Trade-off: statistically honest and cheaper than redesign, but materially
  narrows what the calibration can validate.

**Recommendation and rationale:** choose A. The present labels imply construct
variation that the rendered assets do not provide.

### D-T14-03: diagnostic suite

**A. separate 40-case non-normative suite (recommended).**

- One case for each of five diagnostic classes across eight defect families:
  under-repair, over-edit, introduced defect, decision boundary, and
  invalid/unsafe artifact.
- Trade-off: comprehensive family/class coverage and no additional normative
  rating burden; diagnostics cannot enter confirmatory estimates or repair
  missing positive/negative outcome support in the normative core.
- Contingency: if 40 cases are infeasible, use a prespecified 24-case rotating
  suite and disclose the missing family/class interactions.

**B. replace normative episodes with diagnostics.**

- Trade-off: diagnostics affect the calibrated estimand, but continuity,
  allocation, and power must be redesigned.

**C. omit diagnostics.**

- Trade-off: least work, but important scorer failure modes remain untested.

**Recommendation and rationale:** choose A and enforce distinct paths,
identifiers, manifests, and `normative_eligible: false`.

### D-T14-04: split and inference

**A. retain 72/24 as 18/6 whole scene clusters (recommended).**

- Primary resampling unit is the scene cluster. Use cluster bootstrap or exact
  permutation where valid, plus leave-one-scene-out sensitivity.
- Human duplicate ratings are repeated measures, not new episode clusters.
- Never tune on held-out data or reallocate after viewing outcomes.
- Trade-off: continuity with the prepared workload; six held-out clusters still
  produce wide or degenerate intervals in some outcomes.
- Contingency: sparse or one-class held-out outcomes make AUC non-evaluable and
  promotion fails closed; use a new prospectively frozen validation wave.

**B. use 64/32, for example 16/8 clusters.**

- Trade-off: improves held-out support while reducing development estimation.
  Prefer only if held-out threshold validation dominates model development.

**Recommendation and rationale:** choose A, with honest cluster-level
uncertainty and no claim that n=96 independent observations exist.

### D-T14-05: freeze timing

**A. freeze only after regeneration, validation, and panel re-review
(recommended).**

- Hash-bind the exact manifest, assets, renderer/toolchain, protocol, aliases,
  duplicate insertion, sampling rule, and group allocation.
- Trade-off: delays rating but avoids freezing a known-confounded design.
- Contingency: any task-affecting post-freeze change creates a new version and
  amendment; after outcome exposure, it also requires sensitivity analysis or
  a fresh validation wave.

**B. freeze the current 96 with explicit waivers.**

- Trade-off: immediate readiness, but permanently restricts claims and does not
  close the construct or cluster-support limitations.

**C. defer calibration indefinitely.**

- Trade-off: no governance risk and no progress beyond E2 diagnostics.

**Recommendation and rationale:** choose A. This packet does not itself freeze
anything; the later freeze packet must identify exact hashes.

### D-T14-06: human-rating route

**A. staged steward rehearsal followed by at least two governed raters and an
adjudicator (recommended for E3 claims).**

- Trade-off: supports inter-rater evidence and generalisability, but requires
  recruitment, consent, compensation decisions, privacy controls, an audited
  production store, and accountable human operations.
- Contingency: if those resources are unavailable, retain the result as a
  sole-steward pilot and do not claim independent validation.

**B. sole-steward blind-first rating.**

- Trade-off: lowest coordination cost; only test-retest consistency can be
  reported, never inter-rater agreement or independent validation.

**C. defer ratings.**

- Trade-off: preserves the candidate boundary but leaves calibration open.

**Recommendation and rationale:** choose A for promotion-grade evidence; B is
acceptable only for an explicitly limited pilot. Agent or synthetic ratings do
not qualify under any option.

### D-T14-07: stopping and promotion policy

**A. conjunctive, fail-closed gates (recommended).**

- held-out correction and no-new-defect AUC at least 0.80, lower cluster-level
  bound at least 0.70;
- preservation and locality Spearman correlation at least 0.70, lower
  cluster-level bound at least 0.50;
- hidden-duplicate consistency at least 0.80;
- invalid or omitted responses no more than 5%; and
- sufficient held-out positive and negative class support for every binary
  endpoint.

Every gate must pass. No early efficacy stop, held-out retuning, silent row
drops, or threshold rescue is permitted.

**B. retain all results as diagnostic regardless of thresholds.**

- Trade-off: enables learning without a normative claim; safest contingency
  for mixed, sparse, or uncertain results.

**C. revise the scorer after failure.**

- Trade-off: potentially improves alignment but requires a new score version,
  bridge set, paired old/new evidence, migration note, fresh held-out wave, and
  explicit promotion decision.

**Recommendation and rationale:** approve A as the prospective policy and B as
the mandatory failure contingency. Do not promote a score now.

### D-T14-08: independent challenge and recovery

**A. external scorer challenger plus independently operated second-environment
recovery (recommended and required for the corresponding gates).**

- Trade-off: genuine independence and stronger failure discovery, but requires
  external coordination and a witness/custodian who is not an agent substitute.
- Recovery must bind the immutable commit/archive, hashes, toolchain,
  manifests, rights metadata, bridge replay, full harness, timestamps, and all
  failures.
- Contingency: critical challenge findings block promotion; failed recovery is
  retained and the gate remains open until a new witnessed attempt succeeds.

**B. internal agent challenge and same-machine clone.**

- Trade-off: useful E2 preparation and debugging, but cannot establish
  independence or close the witnessed-recovery gate.

**Recommendation and rationale:** agents should prepare and mechanically
validate the packets using B, then an independent actor must execute A.

### D-T14-09: attestation, release, publication, and unblinding

**A. keep T14 non-normative and unreleased until calibration, challenge, and
recovery pass (recommended).**

- Agents may prepare zero-cost local dry runs and allowlisted bundle checks.
- Operational attestations require the authorized remote workflow against an
  exact immutable commit/tag.
- Release, repository/Hub upload, publication, and unblinding each require a
  later explicit steward authorization.
- Trade-off: slowest public path but preserves evidence meaning and sealed-set
  boundaries.

**B. later alpha/prerelease with explicit non-normative blockers.**

- Trade-off: enables limited integration feedback but raises misinterpretation
  risk and still cannot claim calibrated T14 performance.

**C. stable/normative release now.**

- Rejected: the required calibration, independent challenge, and recovery
  evidence do not exist.

**Recommendation and rationale:** choose A. An independent custodian is the
preferred unblinding route after verified analysis lock; steward self-custody
is procedural blinding only.

## What agents can complete after the design decisions

Without freezing, rating, promoting, attesting, releasing, publishing, or
unblinding, agents can:

1. regenerate the recommended normative candidate and separate diagnostics;
2. add geometry, severity, allocation, separation, malformed-input, and
   determinism validators and tests;
3. prepare alias-only blinding, duplicate insertion, missingness, and rating
   schemas;
4. prepare a prospective cluster-level analysis plan, simulation, synthetic
   end-to-end tests, and fail-closed stopping report;
5. prepare scorer-challenge and witnessed-recovery packets and validate their
   mechanics locally;
6. run the full local harness with zero paid spend, retaining all outputs and
   failures; and
7. rerun the three-agent advisory panel and return the exact hash-bound freeze
   packet for the steward's later decision.

## Steward response template

Record one selection per line. A short response such as the following is
sufficient to authorize the recommended preparation while preserving all later
human gates:

```text
D-T14-01 A
D-T14-02 A
D-T14-03 A
D-T14-04 A
D-T14-05 A
D-T14-06 A
D-T14-07 A+B contingency
D-T14-08 A (agents prepare; independent actors execute)
D-T14-09 A
```

The response must not be interpreted as ratings, a completed freeze, score
promotion, independent evidence, attestation, release, publication, or
unblinding.

## Steward decision recorded

On 2026-08-29 the benchmark steward approved the recommendations in this packet and
authorized agents to address all repository-owned preparation. The approved slate is:

```text
D-T14-01 A
D-T14-02 A
D-T14-03 A
D-T14-04 A
D-T14-05 A
D-T14-06 A
D-T14-07 A+B contingency
D-T14-08 A (agents prepare; independent actors execute)
D-T14-09 A
```

The canonical UTF-8 bytes between the code fences, including the final newline, have
SHA-256 `6cd05bf97eed4d1e286be462c589e8fa6af79b77606a82f86044a5ea65de764b`.
Approval authorizes redesign and packet
preparation, not execution of the later accountable gates. In particular, D-T14-05 A
requires a new exact-hash freeze decision after regeneration, validation, and panel
re-review; D-T14-08 reserves challenge and recovery execution to independent actors; and
D-T14-09 keeps T14 non-normative and unreleased.
