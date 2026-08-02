# PelicanBench

**PelicanBench** is a longitudinal, compositional and agentic visual-generation benchmark anchored by the deceptively difficult task of depicting a pelican riding a bicycle.

It turns a memorable model demonstration into a reproducible research programme. The benchmark evaluates not only the selected final picture, but also source integrity, anatomy, mechanics, interaction geometry, editability, repair, tool use, trajectories, calibration, cost, stability and learning. The public pelican-on-a-bike prompt remains the heritage anchor; the scientific benchmark uses dynamic animals, mobile non-living objects and interaction relations to resist prompt-specific optimisation.

> **Status:** `v0.4.0-alpha.1` is the prospective-pilot and quality-engineering alpha. It retains the measurement-validity repair and ecosystem contracts, then adds a committed 113-prompt candidate benchmark, an exact 48-prompt empirical replication bridge, deterministic 2,178-cell multi-model planning, staged human calibration, rights-aware corpus ingestion, eleven independent test classes, branch-aware coverage above 90%, mutation sentinels, Codecov, Renovate, Vale, and strict linting and typing gates. It is E2 fixture-verified, not yet prospectively executed, human-calibrated, remotely published or independently reproduced.

## Why this exists

Simon Willison has repeatedly used “a pelican riding a bicycle” as a compact test of LLM-generated SVG capability. Dylan Mordaunt subsequently explored the same problem through agentic drawing and argued that the attempts, feedback loops and contact sheets reveal more than a single selected image. PelicanBench preserves that history while expanding it into a dynamic benchmark that can ask whether systems:

- recognise and construct the right animal and mobile object;
- create a mechanically and anatomically coherent interaction;
- generate safe, editable artifacts rather than visual shortcuts;
- diagnose and repair defects without damaging correct regions;
- use drawing tools iteratively, recover from mistakes and learn within governed boundaries; and
- remain reproducible as models, judges and benchmarks change.

## V1 MVP

```mermaid
flowchart LR
    G[Typed task grammar] --> T[Versioned BenchmarkTask]
    O[Animal, object and interface ontologies] --> T
    T --> A[Model or archived-output adapter]
    A --> S[SVG security gate]
    S --> R[Canonical render]
    R --> J[Source-independent semantic assessment]
    S --> Q[Artifact-quality diagnostics]
    J --> C[Multidimensional scorecard]
    Q --> C
    C --> M[Content-addressed run manifest]
    C --> E[Explorer / HF dataset]
    T --> P[PelicanCanvas agentic environment]
    P --> X[Trajectory and repair metrics]
    H[Blinded human calibration] -.->|V1 gate| C
```

Run the deterministic fixture benchmark after installing the package and development dependencies:

```bash
python -m pip install -e '.[dev,analysis]'
pelicanbench validate-repo
pelicanbench validate-v1-candidate
pelicanbench release-readiness --profile v0.4-alpha
pelicanbench ecosystem-audit --output artifacts/ecosystem-audit.json
pelicanbench model-registry-status
pelicanbench plan-model-qualification --output artifacts/model-qualification-plan.json
pelicanbench plan-judge-qualification --output artifacts/judge-qualification-plan.json
pelicanbench plan-prospective-pilot --output artifacts/prospective-pilot-plan.json
pelicanbench scorer-challenges \
  --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
  --output artifacts/scorer-challenge-report.json
pelicanbench run-fixture --output runs/fixture
bash scripts/harness.sh
```

`uv` remains the intended environment manager. The alpha deliberately does not include a fabricated or incomplete lockfile; see [`docs/reproducible-environments.md`](docs/reproducible-environments.md).

The complete local and CI quality contract is documented in [`docs/quality-engineering.md`](docs/quality-engineering.md). Missing local analyzers are recorded as deferred evidence rather than treated as passing.


## Measurement validity

The original structural prototype could be gamed by placing semantic words in SVG IDs or invisible elements. `svg-multilayer/0.2.0` treats those labels as diagnostic only. Animal, object and interaction scores require a source-independent assessment of the canonical render. The exploit and its regression tests remain public under [`benchmark/scorer-challenges`](benchmark/scorer-challenges).

Release claims are evaluated against the machine-readable [`benchmark/assurance-case.json`](benchmark/assurance-case.json) and [`conductor/release-blockers.json`](conductor/release-blockers.json).

## Benchmark tracks

The scorecard separates the **Heritage SVG**, **Compositional SVG**, **Direct Image**, **Reference-Grounded**, **Repair**, **Agentic Drawing** and **Human-in-the-Loop** tracks. Direct generators, code-generating models and tool-using agents are not collapsed into one leaderboard.

V1 is deliberately narrow: a prospective, human-calibrated one-shot SVG benchmark. Repair, agentic drawing, accessibility and future media remain separate follow-on tracks. The current alpha establishes fixture-verified contracts but does not claim empirical model rankings. Evidence-backed progress is recorded in [`conductor/status.md`](conductor/status.md).

## Conductor and agent workflow

The repository vendors a workspace-local Conductor plugin at [`.agents/plugins/conductor`](.agents/plugins/conductor), mirrors its callable skills at [`.agents/skills`](.agents/skills), and stores the project context, specifications and plans under [`conductor/`](conductor/). Every programme track is specified as one parent GitHub issue and four phase issues, with five cross-track release blockers. The deterministic manifest therefore defines 115 work items; authenticated synchronization creates and updates that hierarchy idempotently.

The development contract is:

1. Context and decision record.
2. Specification with MoSCoW requirements and Mermaid design.
3. Test-first phased plan.
4. Small implementation commits with evidence.
5. Review, threat-model and reproducibility checks.
6. Governed learning proposals, never automatic benchmark mutation.

## Provenance

Entire is configured from the first repository revision through [`.entire/settings.json`](.entire/settings.json). Entire captures development-session provenance on its checkpoint branch; benchmark execution separately emits immutable run manifests, W3C PROV JSON-LD, RO-Crate metadata and reproduction commands. These are complementary, not interchangeable.

## Ecosystem

PelicanBench is designed to interoperate with Dylan Mordaunt’s repositories rather than duplicate them. The typed registry currently records 40 GitHub and Hugging Face assets, including direct contracts for repository standards, Conductor, Entire, SourceRight, Authentext, human-rating exchange, OSF, Substack, scholarly publication, local-model runtimes and Hugging Face publication. It also records formal ontology patterns from UOGTO, agent-engineering patterns from Codev and Ralph-Codex, archival patterns from FYI tooling, a planned w3id namespace and an approval-gated Postiz dissemination hand-off. Pattern-only, candidate, watch and excluded assets are explicit, so “not imported” is distinguishable from “not considered”.

Dylan’s two Qwen3 Hermes adapters are included as first-party **candidates**, not presumed eligible systems. The pilot planner retains their cells as `qualification-required` until immutable revisions, licence review, runtime conditions and valid-SVG canaries are recorded. See [`docs/ecosystem-integration.md`](docs/ecosystem-integration.md).

## Publication and release hand-offs

`pelicanbench publication-bundle` creates a deterministic, rights-aware hand-off for SourceRight, Authentext, scholarly review, Substack, Postiz, OSF and the arXiv template without performing an authenticated write. The Postiz payload is a placeholder-bearing template and cannot be executed without explicit account, time, link, media-rights and content approval. `scripts/package_release.py` produces source and full-history archives, a Git bundle, SBOM, release manifest, verification receipt, publication archive, QA receipt and top-level checksums after a clean tagged verification.

## Governance and citation

See [`GOVERNANCE.md`](GOVERNANCE.md), [`SECURITY.md`](SECURITY.md), the benchmark/data/scorer cards under [`docs/`](docs/), and [`CITATION.cff`](CITATION.cff). Historical text and images are not redistributed merely because they are publicly visible; the rights ledger determines what can be mirrored, transformed or linked.

Licensed under Apache-2.0. Third-party source materials retain their own rights.
