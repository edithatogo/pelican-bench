# Integration with Dylan Mordaunt's GitHub and Hugging Face ecosystem

## Position

PelicanBench does not treat every repository or Hub artifact owned by
`edithatogo` as a dependency. It uses an explicit selection and firewall policy:

1. **Direct integrations** implement a versioned exchange contract that is useful to
   the benchmark now.
2. **Pattern sources** contribute repository, statistical, ontology, or publication
   design without becoming runtime dependencies.
3. **Candidates** are recorded but remain qualification-gated.
4. **Watch items** are monitored where an adjacent capability may later become useful.
5. **Excluded assets and families** are documented so absence is a decision rather
   than an accidental omission.

The authoritative inventory is
[`benchmark/integrations/ecosystem-registry.json`](../benchmark/integrations/ecosystem-registry.json).
`pelicanbench ecosystem-audit` checks its schema, evidence paths, local sibling clones,
and optional command availability. A missing optional clone or executable is recorded;
a missing declared evidence artifact fails the audit.

## Implemented direct boundaries

| Asset | PelicanBench boundary | Current evidence |
|---|---|---|
| `repository-standards` | v1 repository verification receipt and evidence-gated solo-maintainer controls | external schema snapshot, receipt generator and validation tests |
| `conductor-upstream-canonical` | pinned repository-local Conductor skill with drift checks | lock record, plugin installation and mirror checker |
| `entireio-cli` | development-session provenance configuration | `.entire/settings.json`, bootstrap and runtime-status check |
| `sourceright` | canonical CSL and SourceRight workspace in publication bundles | CSL exporter, `.sourceright` hand-off and review plan |
| `authentext` | agent-skill review of frozen public writing | publication review brief and no-runtime-import contract |
| `nlp-policy-nz` | generic NER, relation, Parquet and ontology patterns | Simon-corpus records and ontology design; no policy-domain dependency |
| `open_social_data` | tabular/data-dictionary/provenance conventions for human ratings | privacy-minimised CSV exchange and data dictionary |
| `osf-cli-go` | OSF validation and explicit manual upload plan | project metadata and machine-readable publication action |
| `substack-cli-ts` | front-matter-aware preflight and dry-run publication plan | Substack draft and action contract |
| `arxiv-paper-template` | reproducible scholarly-paper hand-off | `paper/`-shaped source, metadata and references |
| `scholarly-publishing-agents` | integrity and publication-lifecycle review | explicit review brief and evidence-only claim rule |
| `academic-research-skills` | human-in-loop research and manuscript integrity patterns | publication and assurance workflow contract |
| `krita-cli` | legacy drawing trajectory and compatibility adapter | documented adapter boundary; not the future normative environment |
| `hermes-training` | first-party model qualification and runtime-prompt provenance | model registry, runtime profiles and pilot qualification gates |
| PelicanBench Hugging Face dataset and Spaces | publication targets | complete local dataset/Space scaffolds; remote creation remains blocked |
| `postiz-agent` | future multi-platform dissemination hand-off | template-only payload and approval-gated manual-write action |

## Pattern-only integrations

`template-solo-data`, the owner `.github` repository, `conductor-next`, `voiage`,
`human-phenotype-ontology`, `UOGTO`, `codev`, `ralph-codex`, `fyi-cli`, `fyi-archive`,
`ollama`, and `llama.cpp` inform repository quality, self-improvement governance,
uncertainty, ontology engineering, faithful capture, multi-mirror publication and local
inference. They are intentionally not imported wholesale. The generic OpenAI-compatible
adapter is the runtime boundary for Ollama, llama.cpp, MLX servers, and similar gateways.

UOGTO contributes the formal JSON-LD, SHACL, competency-question and modelling-decision
pattern. Its game-theory classes are not semantic imports. Codev and Ralph-Codex contribute
review-to-learning, immutable-specification, rollback and test-governed completion patterns,
while Conductor remains the sole authoritative programme graph. FYI tooling contributes
WARC/WACZ, content-addressed capture, mirror-verification and publication patterns without
bringing FOI-domain logic into the benchmark.

## First-party Hugging Face assets

The 1 August 2026 owner-profile inventory showed four model repositories, seventeen
datasets and two Spaces. PelicanBench records the assets relevant to V1 as follows:

| Asset | Disposition |
|---|---|
| `qwen3-4b-hermes-lora` | candidate model; not eligible until immutable revision and SVG canary evidence are recorded |
| `qwen3-4b-hermes-lora-peft-converted` | candidate PEFT lane with the same qualification gate |
| `qwen3-hermes-strict-toolcall-synthetic-v4` | training-provenance reference only; never benchmark training or scoring data |
| `lfm2.5-1.2b-intel-lora` | considered and excluded from V1 pending evidence of text-to-SVG generative capability |
| `ollama-colbert-local-artifacts` | considered and excluded from V1 because it is retrieval/runtime documentation rather than a visual generator |
| remaining domain datasets and existing application Spaces | excluded by family because they do not contribute to visual-composition measurement |

The two Qwen adapters are deliberately represented as **qualification-required** in the
prospective execution plan. First-party ownership does not bypass licence, revision,
canary, runtime, cost, or output-validity rules.

## Candidate future boundaries

- `citeweft`: neutral scholarly extraction may later feed SourceRight-compatible source
  records for the Simon archive, but it is still a technical preview.
- `mcp-libre`: potential real-application accessibility bridge after its capability and
  security contracts are sufficiently stable.
- `w3id.org`: intended persistent namespace publication target. The current namespace is
  reserved locally and marked `registration-planned`; no resolver publication is claimed.
- `postiz-agent`: candidate dissemination surface. The bundle exports only a reviewed-template
  contract and never supplies account IDs, live media URLs or an approved schedule.
- `mcp-registry`: watch item for a future stable agentic-environment MCP service; not required
  for the V1 benchmark.
- `osf-mcp-server`: monitored, but `osf-cli-go` remains the preferred deterministic
  publication boundary.
- Penpot and tldraw adapters: external projects rather than first-party libraries;
  implementation remains a later agentic-drawing milestone.

## Deliberate exclusions

Clinical applications, health-policy repositories, legislation and Hansard corpora,
medicines/reimbursement projects, and unrelated first-party Hub datasets remain outside
PelicanBench. They are valuable assets, but coupling them to this benchmark would add
irrelevant dependencies, rights surfaces, and domain assumptions.

## Audit commands

```bash
pelicanbench ecosystem-audit \
  --registry benchmark/integrations/ecosystem-registry.json \
  --output artifacts/ecosystem-audit.json

pelicanbench model-registry-status
pelicanbench plan-pilot --output artifacts/v1-pilot-execution-plan.json
pelicanbench ontology-interoperability-status
```

The audit establishes integration coverage at E2 fixture level. It does not establish
that optional commands are installed, remote repositories are published, model candidates
are qualified, or external services have executed successfully.
