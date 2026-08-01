# Integration with the edithatogo ecosystem

| Repository or asset | Role in PelicanBench | Integration rule |
|---|---|---|
| `krita-cli` | Legacy agentic raster adapter, command history, replay and rollback | Depend through a versioned adapter; do not copy its implementation |
| `nlp-policy-nz` | Proven NER/relation/Parquet/HF publication patterns | Reuse interfaces or extract a shared generic core later; avoid domain leakage |
| `authentext` | Text/source authenticity and transformation provenance | Planned provenance adapter |
| `sourceright` | Rights and source-governance capability | Planned source-registry policy adapter |
| `fyi-cli` / `fyi-archive` | Acquisition and archival patterns | Use for lawful snapshots and manifests when interfaces stabilise |
| `human-phenotype-ontology` / HPO work | Ontology engineering and mapping lessons | Map patterns, not medical concepts, into evaluation ontology governance |
| `conductor-next` | Experimental Ralph loops, context hygiene, VCS/worktree ideas | Selectively adopt bounded features while pinning official Conductor protocol |
| `entireio-cli` | Development-session provenance | Integrate hooks; keep checkpoint data private where sensitive |
| `arxiv-paper-template` | Future scholarly manuscript | Import as publication tooling, not into runtime core |
| `academic-research-skills` and `citeweft` | Literature/research and citation quality | Use during paper track with frozen evidence bundles |
| Hugging Face user `edithatogo` | Dataset, Space, model-adapter and result publication | Namespace target after token-authenticated setup |

PelicanBench does not introduce external libraries that duplicate capabilities
Dylan is actively developing without an explicit temporary-adapter and migration
plan. The monorepo keeps the benchmark coherent while cross-repository interfaces
remain thin and versioned.
