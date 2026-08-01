# Publication roadmap

## Principle

Public writing is generated from frozen repository evidence. Publication tooling may
review, format and transport that material; it may not infer empirical results from plans,
fixtures or incomplete runs.

## Reproducible hand-off bundle

`pelicanbench publication-bundle` creates a content-addressed, rights-aware directory with:

- Substack drafts and series outline;
- an arXiv-template-shaped `paper/` directory;
- CSL JSON in a generic references directory and an exact `.sourceright` workspace;
- SourceRight, Authentext and scholarly-integrity action briefs;
- a placeholder-bearing Postiz social-distribution template;
- OSF project metadata and explicit manual-write gates;
- benchmark, data and scorer cards;
- pilot commitment and assurance evidence;
- ecosystem registry snapshot;
- optional verification, release, fuzzing and scorer artifacts;
- a manifest and `SHA256SUMS`.

Bundle creation never authenticates to or writes into Substack, OSF, arXiv, GitHub or
Hugging Face.

## Tool boundaries

| Tool | Use | Safety boundary |
|---|---|---|
| SourceRight | validate CSL and inspect citation-evidence coverage | may report degraded verification until provider sidecars exist |
| Authentext | review voice, clarity and unsupported certainty | no invented claims or hidden AI use |
| scholarly-publishing-agents | methods, integrity, disclosure and traceability review | evidence-only; no autonomous authorship or submission |
| substack-cli-ts | front-matter preflight and payload dry-run | no live draft or publish action without approval |
| osf-cli-go | validate project metadata and manually upload a frozen archive | authenticated write is separate and approval-gated |
| arxiv-paper-template | reproducible LaTeX quality and source packaging | no autonomous category, licence, endorsement or submission decision |
| postiz-agent | reviewed multi-platform draft or scheduling hand-off | template only; every account, timestamp, link, media upload and external write requires explicit approval |

The Postiz template is deliberately non-executable as generated. It contains placeholders,
declares `automatic_execution_permitted: false`, and is paired with a `manual-write`
publication action. It is a future distribution convenience, not part of benchmark scoring
or release readiness.

## Planned Substack sequence

1. **The joke that became a benchmark.** Origin, public anchor and why interaction matters.
2. **How the benchmark benchmarked itself badly.** The semantic-label exploit and
   measurement-validity repair.
3. **Anatomy, mechanics and interfaces.** Pelican, bicycle, tuk-tuk and abstract affordance
   ontologies.
4. **Watching an agent draw.** Contact sheets, actions, regressions, recovery and tool
   choice.
5. **Is the pelican being pelicanmaxxed?** Factorial inference, uncertainty and contamination.
6. **From mascot to research infrastructure.** Human calibration, rights, Hub publication
   and open governance.

Posts 1 to 3 can discuss methods and repository evidence before the prospective study.
Any model ranking, human-alignment result or longitudinal trend waits for the matching
validated release.

## Scholarly outputs

### Methods/software preprint

The first paper describes the benchmark rationale, evidence firewall, task identities,
ontology, pilot design, scorer challenge, provenance and limitations. It must be labelled
as a methods/software alpha if no prospective results are present.

### Empirical benchmark paper

A later revision adds the frozen multi-model pilot, human calibration, hierarchical
analysis, judge sensitivity, failure accounting and independent reproduction.

### Historical longitudinal paper or section

The Simon Chronicle is observational and rights-constrained. It is analysed separately
from the prospective benchmark and reports prompt/interface changes, selection limitations,
source coverage and commentary annotation uncertainty.

## OSF and archive plan

Create an OSF project only after metadata review. Proposed components are:

- protocol and analysis plan;
- benchmark and scorer releases;
- human-calibration governance;
- results and reproducibility; and
- publication materials.

Preregistration and registration are explicit human decisions. Final citable software and
data releases can additionally be archived to Zenodo once identifiers, licences and
rights have been reviewed.
