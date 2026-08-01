# Hugging Face architecture

## Surfaces

PelicanBench prepares three independently versioned Hub repositories:

1. `edithatogo/pelican-bench`, a dataset containing public tasks, schemas, cards,
   rights-cleared artifacts, results, retired holdouts, human annotations and evaluation
   records.
2. `edithatogo/pelican-bench-explorer`, a read-only Gradio Space for scorecards,
   uncertainty, pairwise comparisons, longitudinal views and trajectory replay.
3. `edithatogo/pelican-bench-openenv`, a separately deployed environment boundary for
   PelicanCanvas and later real-application adapters.

The dataset is authoritative. Spaces consume pinned dataset revisions and must not contain
sealed tasks, credentials or unversioned normative scores.

## Storage and jobs

Large mutable traces, temporary renders and checkpoints belong in short-lived job storage
or a mutable Bucket. A release workflow promotes validated artifacts into the versioned
dataset after rights, schema, scorer and manifest checks. The release record retains the
source job/run identity and content hashes.

## Model discovery and first-party assets

Discovery produces candidates, not automatic entries on a leaderboard. Capability,
revision, licence, remote-code, duplicate-family, runtime-profile, canary, budget and
publication gates determine eligibility. “Every model” means every eligible model, with
failures and exclusions retained.

The current first-party lane records Dylan's MLX and PEFT Qwen3 Hermes adapters and their
runtime prompt profile. Neither is yet eligible for the prospective SVG pilot. Their
strict-tool-call training dataset is recorded as provenance only and is firewalled from
PelicanBench task generation, scorer calibration and human evaluation.

The remaining first-party Hub datasets and existing Spaces were reviewed by family. Domain
archives and unrelated applications are intentionally not PelicanBench dependencies.

## Publication status

All local dataset, Space, OpenEnv, model-registry, runtime-profile and publication scripts
are present. The connected Hugging Face account is identifiable as `edithatogo`, but the
three PelicanBench Hub targets have not been created in this execution environment. The
available connector does not expose a direct repository-upload action, and the prior Jobs
write route was blocked by account credit. Local readiness must therefore not be reported
as remote publication.

## Release gates

A Hub release requires:

- immutable GitHub source commit and benchmark tag;
- successful remote CI and artifact attestations;
- rights-cleared artifact allowlist;
- dataset/benchmark/scorer cards;
- model and runtime registry snapshot;
- run, failure and evaluation manifests;
- repository-standards verification receipt;
- content-addressed publication manifest and checksums; and
- post-upload validation against the exact Hub revision.
