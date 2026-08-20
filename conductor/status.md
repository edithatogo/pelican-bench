# Conductor status

Status is generated from track metadata. `complete` means that the declared phase exit criteria are met at the stated evidence level; it does not convert fixture evidence into empirical, human or production validation.

| Track | Capability | P0 | P1 | P2 | P3 | Evidence | Current constraint |
|---|---|---:|---:|---:|---:|---:|---|
| T00 | Foundation, governance and Conductor | complete | complete | complete | complete | E2 | Local Conductor, evidence governance, first-party ecosystem contracts, and operational procedures are E2 fixture-verified; authenticated remote issue/project synchronization and independent operational use remain outstanding. |
| T01 | History, prior art, source registry and rights | complete | complete | complete | partial | E1 | Repository-owned rights controls are harness-verified; historical artifacts remain link-/metadata-only or quarantined under D037. Agent analysis cannot constitute independent legal/source-rights approval; RB-05-C1 remains planned and T01/T04 P3 cannot be promoted until every artifact has a redacted, hash-bound permission/redistribution decision. |
| T02 | Benchmark constitution, schemas and provenance | complete | complete | complete | partial | E2 | Contract operations and recovery invariants are fixture-verified; a backup contract steward and an independent archive-recovery rehearsal against a tagged release remain outstanding. |
| T03 | Animal, mobile-object and interface ontologies | complete | complete | complete | planned | E2 | Formal JSON-LD/SHACL/competency and namespace-governance contracts are E2, but normative SHACL execution, w3id registration, expert ontology review, and empirical annotation validation remain outstanding. |
| T04 | Simon corpus NLP, NER and idea coverage | complete | complete | complete | partial | E2 | Corpus hardening, lifecycle and incident controls are fixture-verified; independent source/rights review, a backup corpus custodian and validated coverage against the complete source archive remain outstanding. |
| T05 | Longitudinal image and SVG quantification | complete | complete | complete | planned | E1 | Longitudinal methods run on synthetic fixtures; the rights-cleared historical artifact timeline remains outstanding. |
| T06 | Deterministic SVG integrity and structural scoring | complete | complete | partial | planned | E2 | The source-label exploit and renderer bridge are fixture-verified; empirical human calibration and an independent scorer challenge remain outstanding. |
| T07 | Semantic judges and human calibration | complete | complete | partial | planned | E2 | Source-independent assessment, staged blind-first human calibration, deterministic sampling, privacy-minimised exchange and judge qualification planning are E2 fixture-verified; participant governance, recruitment and empirical judge calibration remain outstanding. |
| T08 | Dynamic animal and mobile-object task grammar | complete | complete | partial | planned | E2 | The 113-prompt, 81-scenario candidate and nine-task qualification canary are content-committed and E2 fixture-verified; empirical item difficulty and prospective multi-model execution remain outstanding. |
| T09 | Statistics, uncertainty and Pelicanmaxxing | complete | complete | partial | planned | E2 | Cluster-aware estimators are fixture-tested; the prespecified prospective model and human data are not yet available. |
| T10 | Reproducible runner and model adapters | complete | complete | partial | planned | E2 | Failure retention, model and judge qualification, deterministic 2,178-cell prospective planning, bounded retries, secret minimisation and research-object outputs are E2 fixture-verified; real provider behaviour and second-environment reproduction remain outstanding. |
| T11 | Hugging Face execution and publication | complete | complete | complete | planned | E2 | Hub dataset/Space publication and first-party model execution are locally specified and fixture-verified, but remote repositories remain absent and the candidate Qwen adapters have not completed an SVG canary. |
| T12 | CI/CD, supply chain and Entire provenance | complete | complete | partial | planned | E2 | The dependency-resilient local harness, eleven-lane test taxonomy, greater-than-90-percent branch-aware coverage, mutation sentinels, Codecov, Renovate, Vale configuration, SBOM, release manifest and provenance contracts are E2 fixture-verified; remote CI, full third-party analyzers, attestations and Entire runtime evidence have not run. |
| T13 | Public explorer and result explanation | complete | complete | partial | planned | E1 | Explorer prototypes exist; deployment and usability validation remain outstanding. |
| T14 | Diagnosis, repair and edit locality | complete | complete | partial | partial | E2 | T14 P3 hardening budgets, lifecycle policy, incident response, and archive controls are fixture-verified; source-independent visual repair calibration, a witnessed recovery rehearsal, and the stable-release checkpoint remain outstanding. Human-dependent decisions route through a panel of agents for advice and return to the benchmark steward as the sole human decision-maker. |
| T15 | Agentic drawing environments and application adapters | complete | complete | partial | planned | E2 | PelicanCanvas, deterministic simulation, consumer contracts and a bounded autonomous reference agent are E2 fixture-verified; Penpot and other real-application adapters remain unvalidated. |
| T16 | Trajectories, self-learning and skill acquisition | complete | complete | partial | planned | E2 | Learning governance, trajectory metrics, deterministic fault injection and bounded autonomous recovery are E2 fixture-verified; empirical cross-task agent transfer studies remain outstanding. |
| T17 | Security, adversarial testing and scorer challenge | complete | complete | partial | planned | E2 | The label-injection exploit, normative metamorphic challenges, bounded SVG fuzzing and mandatory mutation sentinels are E2 fixture-verified; coverage-guided fuzzing, rendered prompt-injection studies, full mutmut execution and independent submissions remain outstanding. |
| T18 | Accessibility and human-in-the-loop creation | complete | complete | complete | planned | E1 | Privacy-minimised human-rating exchange is E2 fixture-verified; accessibility co-design, participant governance and real human-in-the-loop studies remain outstanding. |
| T19 | Substack, arXiv and scholarly publication | complete | complete | partial | planned | E2 | Content-addressed publication and approval-gated social-distribution hand-offs are E2 fixture-verified; external tool execution, empirical results sections, authorship review and actual publication remain outstanding. |
| T20 | Maturity, drift, releases and maintenance | complete | complete | partial | planned | E2 | Drift, release and complete local packaging contracts are E2 fixture-verified; multiple remote production releases, attestations and independent reproductions are needed for operational validation. |
| T21 | Video, animation, 3D and cross-application transfer | complete | complete | planned | planned | E1 | Contracts exist; video, 3D, and cross-application empirical tracks are intentionally post-V1. |

## Programme totals

- Tracks: 22.
- Phases: 88.
- Phase states: complete 53, partial 17, planned 18.
- Track evidence: E1 5, E2 17.
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
