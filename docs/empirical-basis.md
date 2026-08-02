# Empirical basis of the candidate benchmark

## Current answer

A candidate benchmark now exists, but its evidence layers must be distinguished.

The original 33-task alpha was ontology-led and investigator-designed. It was informed by Simon Willison's posts and the pelican-on-a-bicycle tradition, but it was not generated from a completed empirical NLP study of Simon's full corpus. Describing that alpha as empirically NLP-derived would be inaccurate.

The revised `PB-2026.08-v1-candidate` has a stronger, auditable empirical bridge:

1. **Exact empirical replication panel.** Forty-eight prompts reproduce the 8-animal by 6-vehicle design used in Dylan Castillo's 1,008-generation study.
2. **Executable prompt NLP.** The source prompt matrix is parsed into animal, mobile-object, relation, count, style, viewpoint and intent features using a transparent rule and lexicon system.
3. **Measured design coverage.** `benchmark/evidence/snapshots/castillo-2026-design-coverage.json` demonstrates 48/48 exact prompt matches and complete coverage of the source animals, mobile objects and extracted relation classes.
4. **Observed benchmark failure modes.** The scoring and calibration protocol incorporates blind recognition, defect-first anatomy and mechanics review, interaction contact checks, failure retention and reward-hacking controls demonstrated in prior pelican experiments.
5. **Organic prompt-corpus contract.** An importer is implemented for the nested Yupp SVG corpus, allowing later descriptive NLP of organic SVG requests without treating generated outputs as freely reusable.
6. **Human-preference reference.** The calibration exchange is compatible with pairwise preference, coherence and alignment evidence used in large SVG human-evaluation datasets.
7. **Ontology and expert design.** The new affordance-balanced panel remains partly theory- and ontology-led. Those choices are labelled as such rather than being presented as empirical discoveries.

## What “based on empirical NLP” means here

The bridge panel is now **empirically source-derived and NLP-audited**. The confirmatory interface panel is **empirically informed but prospectively designed**. It uses body-plan and affordance abstractions to test generalisation beyond the externally observed matrix.

The benchmark is not yet the result of a validated NLP/NER analysis of Simon's complete longitudinal archive. The current NLP system is a transparent deterministic extractor, not a trained named-entity model. Its 48-prompt coverage result is E2 fixture/source verification, not evidence that it captures every idea in Simon's commentary.

## Simon corpus status

A rights-aware Atom importer is implemented at `pelicanbench ingest-simon-atom`. The default output contains bibliographic metadata and fixity hashes only. Raw text export and derived NLP are blocked unless the source registry records a compatible rights decision. The tag archive reported 129 posts on the 2 August 2026 audit, but the eventual corpus must also detect incomplete feed coverage, deduplicate archive pages and record source revisions.

The next NLP milestone is:

- rights-cleared source acquisition;
- a 100-document, double-annotated gold set;
- span-level animals, objects, models, anatomy, mechanics, tools and evaluation concepts;
- comparative praise, criticism, improvement, regression and contamination relations;
- measured precision, recall, F1 and inter-annotator agreement;
- a source-to-feature-to-task coverage matrix;
- held-out validation of any model-assisted extractor; and
- a documented residual “unincorporated idea” queue.

Until that milestone, features remain labelled `source-derived`, `external-empirical`, `ontology-derived` or `investigator-designed` rather than being collapsed into a single evidentiary category.
