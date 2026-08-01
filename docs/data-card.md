# Data card

## Data classes

1. Project-original task specifications, ontologies, SVG fixtures, repair fixtures, and synthetic commentary.
2. Metadata and links describing public historical posts and artifacts.
3. Rights-cleared historical text, images, SVGs, or annotations when separately approved.
4. Prospective model outputs, run manifests, scores, trajectories, and human ratings.

## Rights policy

Public availability does not establish redistribution rights. `data/sources/source-registry.json` records identity and intended use; `data/sources/rights-ledger.json` records the operative decision by artifact class. The repository currently redistributes only project-original fixtures and permitted metadata.

## Sensitive data

V1 contains no patient, employment, or other personal sensitive data. Human-evaluation releases use pseudonymous rater identifiers and publish only the minimum required metadata. Free text is screened before release.

## Provenance

Records include source IDs, dates, model and revision identifiers where available, prompt data, rights state, content hashes, and annotation versions. Missing historical fields remain null rather than inferred.

## Known biases

The archive over-represents systems selected for public demonstration, successful or noteworthy outputs, English prompts, SVG-capable systems, and one culturally prominent prompt. The dynamic suite and prospective repeated runs reduce but do not eliminate these biases.
