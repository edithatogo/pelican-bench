# Simon corpus NLP and idea-coverage method

## Acquisition

The tag archive is the authoritative discovery surface and reported 129 posts during the 2 August 2026 audit. An Atom-feed importer is implemented, but feed completeness must be tested against the archive rather than assumed.

```bash
pelicanbench ingest-simon-atom \
  --output data/derived/simon-pelican-metadata.jsonl
```

Default mode exports URL, title, dates, categories, stable record ID and content fixity only. It does not export post text. Raw content and derived NLP require a compatible source-registry decision; `metadata-only` fails closed.

A complete acquisition pipeline must:

- enumerate archive pages as well as the feed;
- deduplicate by canonical entry ID and URL;
- detect content-hash conflicts and revisions;
- store source and retrieval timestamps;
- keep post text, quoted third-party text and linked artifacts in separate rights classes;
- record model, prompt and artifact links without silently downloading them; and
- report archive-versus-feed coverage.

## NLP layers

- Document segmentation and quotation/source boundaries.
- NER for models, providers, dates, prompts, tools, file formats, animals, mobile objects and named people.
- Domain entities for animal anatomy, object mechanics, support, control, propulsion, containment, composition and SVG structure.
- Relation extraction: model-produced-artifact, author-critiqued-feature, output-failed-relation, model-compared-with-model and prompt-varies-from-anchor.
- Claim/evidence classification: observation, interpretation, prediction, benchmark suggestion, methodological caveat and humorous aside.
- Commentary taxonomy: anatomy, mechanics, interaction, composition, SVG structure, prompt following, surprise, progress, regression and contamination.
- Temporal model/entity resolution so renamed endpoints are not silently merged.

The current extractor is deterministic and lexicon-based. It is used for source audits and provisional annotation, not presented as a validated statistical NER model.

## Gold set and validation

The first empirical release requires 100 double-annotated documents, stratified over time, model family, post length and commentary type. It reports span and relation precision, recall and F1; exact and relaxed span matching; per-class support; adjudication; inter-annotator agreement; and errors on held-out posts.

Model-assisted extraction may propose annotations, but the held-out evaluation and normative idea mappings must be human-reviewed.

## Coverage guarantee

Each extracted idea receives a stable `idea_id`, source span, confidence, review state and mapping to one or more requirement, ontology, rubric, test or roadmap record. The coverage report identifies unincorporated ideas rather than allowing a summary model to decide that they are unimportant.

The current empirical bridge already has a narrower executable guarantee: all 48 source-study prompts, eight animals, six mobile objects and both extracted relation classes are represented exactly. This does not substitute for the full Simon commentary study.

## Analysis

Topic prevalence, critique dimensions, model-family trajectories, prompt variants, artifact complexity and commentary sentiment are descriptive. Causal claims about model improvement require prospective bridge runs or explicit assumptions. Simon's commentary is one historically important annotation layer, not unquestionable ground truth.
