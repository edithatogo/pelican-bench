# Simon corpus NLP and idea-coverage method

## Acquisition

Discover posts from the canonical tag/archive and explicitly cited pages. Store
URL, title, publication and update dates, author, model/provider names, prompt,
artifact links, available settings and rights status. Preserve HTTP metadata and
content hashes for material that is lawfully acquired.

## NLP layers

- Document segmentation and quotation/source boundaries.
- NER for models, providers, dates, prompts, tools, file formats, animals,
  vehicles and named people.
- Relation extraction: model-produced-artifact, author-critiqued-feature,
  output-failed-relation, model-compared-with-model, prompt-varies-from-anchor.
- Claim/evidence classification: observation, interpretation, prediction,
  benchmark suggestion, methodological caveat and humorous aside.
- Commentary taxonomy: anatomy, mechanics, interaction, composition, SVG
  structure, prompt following, surprise, progress, regression and contamination.
- Temporal model/entity resolution so renamed endpoints are not silently merged.

## Coverage guarantee

Each extracted idea receives a stable `idea_id`, source span, confidence,
review state and mapping to one or more requirement, ontology, rubric, test or
roadmap records. The coverage report identifies unincorporated ideas rather than
allowing a summary model to decide that they are unimportant.

## Analysis

Topic prevalence, critique dimensions, model-family trajectories, prompt
variants, artifact complexity and commentary sentiment are descriptive. Causal
claims about model improvement require prospective bridge runs or explicit
assumptions.
