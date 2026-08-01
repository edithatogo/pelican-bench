# Conductor status

Status is generated from track metadata. `complete` means that the declared phase exit criteria are met at the stated evidence level; it does not convert fixture evidence into empirical, human or production validation.

| Track | Capability | P0 | P1 | P2 | P3 | Evidence | Current constraint |
|---|---|---:|---:|---:|---:|---:|---|
| T00 | Foundation, governance and Conductor | complete | complete | complete | partial | E2 | No declared cross-phase constraint. |
| T01 | History, prior art, source registry and rights | complete | complete | blocked | planned | E1 | Rights review and permission are required before mirroring third-party historical text or artifacts. |
| T02 | Benchmark constitution, schemas and provenance | complete | complete | complete | partial | E2 | No declared cross-phase constraint. |
| T03 | Animal, mobile-object and interface ontologies | complete | complete | partial | planned | E2 | JSON-LD export and competency fixtures exist, but SHACL validation and expert ontology review remain outstanding. |
| T04 | Simon corpus NLP, NER and idea coverage | complete | complete | blocked | planned | E1 | The full Simon Willison corpus is deliberately not mirrored until rights and ingestion decisions are settled. |
| T05 | Longitudinal image and SVG quantification | complete | complete | blocked | planned | E1 | Longitudinal methods run on synthetic fixtures; the rights-cleared historical artifact timeline remains outstanding. |
| T06 | Deterministic SVG integrity and structural scoring | complete | complete | partial | planned | E2 | The source-label exploit and renderer bridge are fixture-verified; empirical human calibration and an independent scorer challenge remain outstanding. |
| T07 | Semantic judges and human calibration | complete | complete | partial | planned | E2 | Source-independent assessment and deterministic calibration-sampling contracts are fixture-verified; participant governance, recruitment and empirical judge calibration remain outstanding. |
| T08 | Dynamic animal and mobile-object task grammar | complete | complete | partial | planned | E2 | The 33-task affordance-stratified pilot is committed, but empirical item difficulty and multi-model execution remain outstanding. |
| T09 | Statistics, uncertainty and Pelicanmaxxing | complete | complete | partial | planned | E2 | Cluster-aware estimators are fixture-tested; the prespecified prospective model and human data are not yet available. |
| T10 | Reproducible runner and model adapters | complete | complete | partial | planned | E2 | Failure retention, bounded retries, secret-minimised commands, checkpoint resumption and research-object outputs are fixture-verified; real provider behaviour and second-environment reproduction remain outstanding. |
| T11 | Hugging Face execution and publication | complete | complete | blocked | planned | E1 | Hub publication is prepared but the available HF Jobs write route is blocked by account credits and no local token is mounted. |
| T12 | CI/CD, supply chain and Entire provenance | complete | complete | partial | planned | E2 | The local harness, deterministic work graph, dependency-aware SBOM, release manifest and provenance contracts are fixture-verified; remote CI, attestations and Entire runtime evidence have not run. |
| T13 | Public explorer and result explanation | complete | complete | partial | planned | E1 | Explorer prototypes exist; deployment and usability validation remain outstanding. |
| T14 | Diagnosis, repair and edit locality | complete | complete | partial | planned | E2 | Declared edit-target scoring is fixture-tested; source-independent visual repair and preservation calibration remain outstanding. |
| T15 | Agentic drawing environments and application adapters | complete | complete | partial | planned | E2 | PelicanCanvas is implemented; Penpot and other real-application adapters remain unvalidated. |
| T16 | Trajectories, self-learning and skill acquisition | complete | complete | partial | planned | E2 | Learning governance and trajectory metrics exist; empirical agent transfer studies remain outstanding. |
| T17 | Security, adversarial testing and scorer challenge | complete | complete | partial | planned | E2 | The label-injection exploit, five normative metamorphic challenges and bounded mutation-fuzz smoke campaign are fixture-verified; coverage-guided fuzzing, rendered prompt-injection studies and independent submissions remain outstanding. |
| T18 | Accessibility and human-in-the-loop creation | complete | complete | blocked | planned | E1 | No participant accessibility claim will be made before co-design, approval, recruitment, and evaluation. |
| T19 | Substack, arXiv and scholarly publication | complete | complete | planned | planned | E1 | Drafts exist but results sections cannot be completed before prospective benchmark runs. |
| T20 | Maturity, drift, releases and maintenance | complete | complete | partial | planned | E2 | Drift and release contracts exist; multiple production releases are needed for operational validation. |
| T21 | Video, animation, 3D and cross-application transfer | complete | complete | planned | planned | E1 | Contracts exist; video, 3D, and cross-application empirical tracks are intentionally post-V1. |

## Programme totals

- Tracks: 22.
- Phases: 88.
- Phase states: blocked 5, complete 46, partial 15, planned 22.
- Track evidence: E1 8, E2 14.
- Planned GitHub work items: 22 parent tracks + 88 phase issues + 5 release blockers = 115.

## Release blockers

| Blocker | State | Evidence | Open criteria |
|---|---|---:|---:|
| RB-01: Measurement validity | partial | E2 | 2 |
| RB-02: Prospective V1 pilot | partial | E2 | 3 |
| RB-03: Human and judge calibration | partial | E2 | 4 |
| RB-04: Independent reproducibility and remote publication | partial | E2 | 4 |
| RB-05: Rights and research governance | partial | E1 | 2 |

## Verification contract

The local evidence gate is `scripts/harness.sh` (run with Bash). It verifies tests and coverage, schemas, issue-manifest freshness, rights controls, ontology competency cases, release assurance, pilot commitments, scorer metamorphism, the renderer bridge when available, deterministic replay and the SBOM.

Remote CI, attestations, GitHub publication, Hugging Face publication, human calibration and prospective model runs are not inferred from local files. They remain open until their release-blocker criteria contain the resulting evidence.
