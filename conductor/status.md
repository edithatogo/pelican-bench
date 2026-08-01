# Conductor status

Status is evidence-based. `complete` means the phase exit criteria are met in the repository; `partial`, `blocked`, and `planned` remain open GitHub phase issues. Local software validation does not imply empirical human or production validation.

| Track | Capability | P0 | P1 | P2 | P3 | Evidence / next constraint |
|---|---|---:|---:|---:|---:|---|
| T00 | Foundation, governance and Conductor | complete | complete | complete | partial | `conductor/index.md`; `.agents/plugins/conductor`; `GOVERNANCE.md`. Hardening and independent use remain outstanding. |
| T01 | History, prior art, source registry and rights | complete | complete | blocked | planned | `docs/history-and-prior-art.md`; `data/sources/source-registry.json`; `data/sources/rights-ledger.json`. Rights review and permission are required before mirroring third-party historical text or artifacts. |
| T02 | Benchmark constitution, schemas and provenance | complete | complete | complete | partial | `src/pelicanbench/models.py`; `benchmark/schemas`; `src/pelicanbench/manifest.py`. Hardening and independent use remain outstanding. |
| T03 | Animal, mobile-object and interface ontologies | complete | complete | complete | planned | `benchmark/ontologies`; `src/pelicanbench/ontology.py`. Hardening and independent use remain outstanding. |
| T04 | Simon corpus NLP, NER and idea coverage | complete | complete | blocked | planned | `src/pelicanbench/corpus.py`; `data/fixtures/corpus.jsonl`; `docs/source-to-requirement-map.md`. The full Simon Willison corpus is deliberately not mirrored until rights and ingestion decisions are settled. |
| T05 | Longitudinal image and SVG quantification | complete | complete | blocked | planned | `src/pelicanbench/image_analysis.py`; `src/pelicanbench/longitudinal.py`; `data/fixtures/historical-observations.jsonl`. Longitudinal methods run on synthetic fixtures; the rights-cleared historical artifact timeline remains outstanding. |
| T06 | Deterministic SVG integrity and structural scoring | complete | complete | complete | partial | `src/pelicanbench/svg.py`; `src/pelicanbench/scoring.py`; `benchmark/fixtures/svg`. Hardening and independent use remain outstanding. |
| T07 | Semantic judges and human calibration | complete | complete | planned | planned | `src/pelicanbench/semantic.py`; `src/pelicanbench/human_eval.py`; `docs/human-evaluation-protocol.md`. Empirical human recruitment, ethics/consent review, and judge calibration remain future work. |
| T08 | Dynamic animal and mobile-object task grammar | complete | complete | complete | partial | `src/pelicanbench/taskgen.py`; `benchmark/tasks/grammar.json`; `benchmark/tasks/public-anchor.jsonl`. Hardening and independent use remain outstanding. |
| T09 | Statistics, uncertainty and Pelicanmaxxing | complete | complete | partial | planned | `src/pelicanbench/statistics.py`; `tests/test_statistics_semantic_human.py`. The estimator is tested on factorial fixtures; real multi-model repeated runs are not yet available. |
| T10 | Reproducible runner and model adapters | complete | complete | complete | partial | `src/pelicanbench/runner.py`; `src/pelicanbench/adapters.py`; `src/pelicanbench/manifest.py`. Hardening and independent use remain outstanding. |
| T11 | Hugging Face execution and publication | complete | complete | blocked | planned | `hf`; `scripts/setup_huggingface.py`; `.github/workflows/publish-hf.yml`. Hub publication is prepared but the available HF Jobs write route is blocked by account credits and no local token is mounted. |
| T12 | CI/CD, supply chain and Entire provenance | complete | complete | complete | partial | `.github/workflows`; `.entire`; `scripts/harness.sh`. Local harness is complete; remote attestations and Entire CLI runtime evidence require the published repository/runtime. |
| T13 | Public explorer and result explanation | complete | complete | partial | planned | `hf/space/app.py`; `web/pelican-canvas`. Explorer prototypes exist; deployment and usability validation remain outstanding. |
| T14 | Diagnosis, repair and edit locality | complete | complete | complete | planned | `src/pelicanbench/repair.py`; `benchmark/fixtures/repair`. Hardening and independent use remain outstanding. |
| T15 | Agentic drawing environments and application adapters | complete | complete | partial | planned | `src/pelicanbench/canvas.py`; `src/pelicanbench/environments.py`; `adapters`. PelicanCanvas is implemented; Penpot and other real-application adapters remain unvalidated. |
| T16 | Trajectories, self-learning and skill acquisition | complete | complete | partial | planned | `src/pelicanbench/trajectory.py`; `src/pelicanbench/self_learning.py`; `conductor/learning-ledger.jsonl`. Learning governance and trajectory metrics exist; empirical agent transfer studies remain outstanding. |
| T17 | Security, adversarial testing and scorer challenge | complete | complete | complete | partial | `src/pelicanbench/svg.py`; `benchmark/fixtures/malicious`; `docs/threat-model.md`. Hardening and independent use remain outstanding. |
| T18 | Accessibility and human-in-the-loop creation | complete | complete | blocked | planned | `docs/accessibility-protocol.md`; `src/pelicanbench/human_eval.py`. No participant accessibility claim will be made before co-design, approval, recruitment, and evaluation. |
| T19 | Substack, arXiv and scholarly publication | complete | complete | planned | planned | `publications/substack`; `publications/arxiv`; `CITATION.cff`. Drafts exist but results sections cannot be completed before prospective benchmark runs. |
| T20 | Maturity, drift, releases and maintenance | complete | complete | partial | planned | `src/pelicanbench/drift.py`; `docs/maturity-model.md`; `docs/release-policy.md`. Drift and release contracts exist; multiple production releases are needed for operational validation. |
| T21 | Video, animation, 3D and cross-application transfer | complete | complete | planned | planned | `docs/future-media-protocol.md`; `src/pelicanbench/media_contracts.py`. Contracts exist; video, 3D, and cross-application empirical tracks are intentionally post-V1. |

## Verification snapshot

- Repository contract: valid.
- Python tests: 66 passing.
- Combined statement and branch coverage: 92.98%.
- Malicious SVG fixtures: rejected.
- Deterministic fixture run and SBOM replay: passing.
- Conductor direct skills and workspace-plugin mirrors: synchronized.
- Rust and Mojo lanes are configured but were skipped locally because their compilers are not installed in the execution container.
- GitHub and Hugging Face publication status is recorded separately in remote issue state and release notes.
