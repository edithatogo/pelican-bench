# Decision log

## D001 — Pelican-on-a-bike is the heritage anchor, not the primary leaderboard

**Options:** exact prompt only; weighted anchor; dynamic suite with anchor reported separately.
**Decision:** dynamic suite, with the exact prompt retained as a prominent longitudinal tracer.
**Rationale:** the public prompt is culturally useful but highly exposed and increasingly optimisable.

## D002 — Report a score vector before a composite

**Options:** one scalar; several independent dimensions; conjunctive gates plus vector and secondary composite.
**Decision:** critical gates and a multidimensional scorecard, with any aggregate versioned and secondary.
**Rationale:** aesthetics must not compensate for absence of the animal, vehicle or interaction.

## D003 — Separate generation strata

Direct raster generation, SVG/code generation, reference-grounded editing and tool-using agents receive separate tracks. Cross-track summaries may compare cost or success thresholds, not claim a single capability ordering.

## D004 — Python reference, Rust hardening, Mojo experiment

Python provides the executable V1 reference and research integration. Rust is the target hardened parser/geometry/WASM core. Mojo receives conformance-tested experimental kernels but cannot become the only normative implementation while the language and toolchain remain unstable.

## D005 — Benchmark-owned PelicanCanvas with application adapters

**Options:** Krita-only; Penpot/Figma-only; benchmark-owned intermediate canvas plus adapters.
**Decision:** PelicanCanvas is the canonical deterministic environment. Penpot is the preferred open real-application target, Figma an optional commercial comparison, Inkscape a renderer/editor target and `krita-cli` a legacy continuity adapter.
**Rationale:** the benchmark must not be coupled to one unsupported plugin or proprietary application.

## D006 — Three related ontology layers

Maintain separate animal and mobile-object ontologies, plus an interface ontology for relations such as rides-on, drives, pilots and passenger-in. Integrated scene ontologies compose these layers. This prevents bicycle-specific assumptions from being imposed on a tuk-tuk or kayak.

## D007 — Rights-aware longitudinal archive

Public visibility does not imply redistribution permission. Until rights are resolved, store URLs, hashes, metadata, independently written annotations and permitted derivatives. Simon Willison’s commentary is a historically valuable annotation, not infallible ground truth.

## D008 — Entire provenance is distinct from run provenance

Entire records agent-development context on its checkpoint branch. Evaluation runs independently record exact tasks, prompts, model revisions, environment digests, artifacts, costs and hashes so scientific reproducibility does not depend on one development tool.

## D009 — V1 is an MVP

V1 releases typed tasks, ontologies, deterministic SVG scoring, fixture runs and a minimal agentic environment. Human calibration, rights-cleared full history, all-model automation and production application adapters are versioned follow-ons, not prerequisites for a useful first release.

## D010 — Self-learning is proposal-driven

Agents can infer and test heuristics but cannot silently mutate normative tasks, rubrics or scorers. Promotion requires human review, contamination assessment, a regression comparison and rollback criteria.

## D011 — Separate source, render and semantic evidence

**Options:** continue source-role scoring; hide source labels before scoring; create a strict
evidence firewall.
**Decision:** use source only for security and artifact diagnostics, derive visible features
from a canonical render, and require source-independent semantic assessment bound to the
render hash.
**Rationale:** the original scorer could be reward-hacked through IDs, classes and invisible
labelled elements. The benchmark must not reproduce the proxy-optimisation failure it aims
to study.

## D012 — Separate scenario, prompt, condition, trial and evaluation identities

**Options:** one task identifier including random seed; task plus run seed; a fully separated
experimental identity model.
**Decision:** use stable semantic, prompt and condition IDs, then record stochastic model
invocations and scorer applications separately.
**Rationale:** repeated generations must remain replicates of the same item so reliability,
prompt effects and model-by-item interactions are estimable.

## D013 — V1 is an affordance-stratified prospective SVG benchmark

**Options:** full multi-track V1; exact pelican prompt only; narrow one-shot SVG V1 with
representative mobility interfaces.
**Decision:** V1 uses one-shot SVG generation across four interface strata, while repair and
agentic tracks mature independently in V1.x.
**Rationale:** a narrow empirically valid benchmark is preferable to a broad suite whose
measurement properties are untested.

## D014 — Use interoperable research-object provenance

**Options:** Entire only; custom run manifests only; layered provenance.
**Decision:** retain Entire for development history and add content-addressed run manifests,
W3C PROV JSON-LD, RO-Crate metadata, SBOMs and release attestations.
**Rationale:** development provenance and scientific reproducibility answer different
questions and should not depend on one vendor or format.

## D015 — Replace generic validation claims with E0 to E5 evidence levels

**Options:** retain P0 to P3 as the only maturity signal; add informal notes; add explicit
evidence levels and release blockers.
**Decision:** keep Conductor phases for work organisation, add E0 Defined through E5
Operationally hardened for claim strength, and use five cross-track release blockers.
**Rationale:** completed repository tasks do not establish human alignment, empirical
validity, independent reproduction or operational maturity.

## D016 — Canonical renders use an opaque, aspect-preserving canvas

**Options:** preserve transparent pixels; hash alpha and undefined transparent RGB; composite onto a fixed background.
**Decision:** preserve SVG aspect ratio, centre the result on a square opaque white canvas and hash visible RGBA pixels. Inkscape bridge renders use the same contract.
**Rationale:** transparent RGB values and viewer backgrounds can vary without changing the intended picture, while forced square export can geometrically distort the scene.

## D017 — Generate the GitHub work graph and status views from source records

**Options:** manually maintain issue manifests and status Markdown; synchronize only remote issues; generate all derived views deterministically.
**Decision:** Conductor metadata and release blockers are authoritative. The 22 parent tracks, 88 phase issues, five release blockers, track registry and status table are generated and checked in the harness.
**Rationale:** evidence claims and issue state must not drift across duplicated documents.

## D018 — Freeze deterministic human-calibration sampling before ratings

**Options:** convenience sample; judge-disagreement-only sample; balanced deterministic stratification with prespecified pair generation.
**Decision:** stratify by interface, model, score band, disagreement and validity, then generate stable within-task cross-model pairs.
**Rationale:** calibration must cover ordinary performance, boundaries and likely failure modes without allowing post-outcome sample selection.

## D019 — Failed provider invocations remain benchmark trials

**Options:** abort the whole run; silently omit failures; retain failed invocations and optionally continue.
**Decision:** failed generations receive stable trial identities, bounded error records and `failures.jsonl`; the runner can continue under an explicit policy. Retrying and checkpointing are adapter layers, and child commands inherit only an environment allowlist.
**Rationale:** reliability and refusal/error rates are part of model-system performance, and dropping them biases the denominator. Resume capability must not expose unrelated secrets or create duplicate paid calls.

## D020: Do not fabricate a resolver lock in a restricted package environment

**Options considered:** commit an incomplete `uv.lock`; use only unconstrained dependency ranges; retain a labelled installed-environment snapshot and require a real registry resolution before V1.

**Decision:** retain `constraints/reference-environment.txt` as development evidence, document its limitations, and require a complete `uv.lock`, OCI digest and release SBOM before the stable benchmark release.

**Rationale:** an incomplete lockfile looks authoritative while omitting packages that the configured mirror could not resolve. Explicitly weaker evidence is safer and more reproducible than false precision.
