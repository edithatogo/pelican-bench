# Scorer card

## Version

The current implementation is `svg-multilayer/0.2.0`. It replaces the original
`svg-structural/0.1.0`, which is retained only as historical context because its semantic
dimensions could be manipulated through SVG identifiers and invisible labelled elements.

## Evidence architecture

The scorer has three independent channels:

1. **Source security and artifact diagnostics:** bounded XML parsing, active-content and
   external-resource rejection, complexity limits, grouping and editability descriptors.
2. **Canonical render diagnostics:** pixel-derived render identity, non-blankness, visible
   bounds, connected components and low-level composition features.
3. **Source-independent semantics:** atomic visual questions answered from the canonical
   render and bound to its hash.

SVG IDs, classes, comments, metadata, element order and declared roles cannot contribute to
animal anatomy, object mechanics, interaction or instruction-coverage scores. They may be
reported as non-normative artifact diagnostics.

## Critical gates

- source is safe to parse and render;
- canonical render is non-blank;
- semantic assessment is source-independent and matches the task and render hash;
- critical animal, object and interaction questions are supplied; and
- their probabilities exceed the versioned thresholds.

A high composition or vector-quality score cannot compensate for a missing animal, object
or relation.

## Semantic and human layers

A semantic judge answers versioned atomic questions against an image only. Judge identity,
revision, method, uncertainty and calibration version are recorded. The static assessor in
tests is explicitly `fixture-only` and cannot establish empirical validity.

Blinded human judgements remain the calibration reference. The V1 pilot oversamples
boundary cases and judge disagreement so calibration effort is concentrated where it is
most informative.

## Known failure modes

- rendered text can influence a multimodal judge even when source metadata is removed;
- canonical renderers can disagree on filters, fonts and unsupported SVG features;
- coarse geometry cannot by itself establish species or interaction semantics;
- multimodal judges can show family, presentation and confidence biases; and
- human raters can disagree or infer intent from style.

These limitations are managed through metamorphic tests, bridge renderers, family-diverse
judges, blinded human calibration, sensitivity analysis and the scorer challenge programme.

## Compatibility

Changes to security rules, canonical rendering, atomic questions, thresholds, ontology
requirements, dimension definitions or aggregate weights are score-affecting. A breaking
change requires a new scorer version, release note, retained regression fixture and bridge
analysis before historical scores are compared.
