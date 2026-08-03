# Study freezes and controlled unblinding

## Purpose

PelicanBench keeps generator identities blinded while confirmatory analysis choices are frozen. Controlled unblinding requires two independently verifiable research-object commitments:

1. an **analysis lock** containing the prespecified analysis inputs; and
2. a **data freeze** containing the final blinded data and the exact campaign-ledger head.

A caller-supplied digest is not sufficient. The authorization command reads both manifests, verifies every frozen file against the repository tree, verifies the protocol-lock bytes, checks that the study and task identities agree, and only then issues a keyed authorization receipt.

## Scientific identity

A study-freeze commitment covers:

- freeze type and study identifier;
- candidate task-set commitment;
- exact study-protocol lock and its hash;
- repository-relative frozen files, byte sizes and SHA-256 hashes;
- non-secret structured metadata; and
- for a data freeze, the event count, final event hash, ledger hash and byte size of the campaign ledger.

`generated_at` is descriptive provenance and is deliberately excluded from the freeze identity. Rebuilding the same freeze from identical bytes therefore produces the same commitment even when the receipt is generated later.

## Analysis lock

The analysis lock should contain the confirmatory analysis plan and every file that can alter the principal inference. For the candidate study this ordinarily includes:

```text
docs/v1-pilot-analysis-plan.md
benchmark/design/assumptions.json
benchmark/human-calibration/study-spec.json
```

Build and verify it while generator identities remain blinded:

```bash
pelicanbench build-study-freeze \
  --root . \
  --freeze-type analysis-lock \
  --study-id PB-2026.08-v1-candidate \
  --input docs/v1-pilot-analysis-plan.md \
  --input benchmark/design/assumptions.json \
  --input benchmark/human-calibration/study-spec.json \
  --output artifacts/study-freezes/analysis-lock.json

pelicanbench verify-study-freeze \
  --root . \
  --manifest artifacts/study-freezes/analysis-lock.json
```

Analysis locks cannot contain a campaign-ledger head. This prevents an analysis manifest from being reused as though it were evidence that data collection is complete.

## Data freeze

The data freeze should contain all blinded primary data, exclusions, failed trials, calibration records and analysis-ready tables. It also requires a verified campaign-ledger head. The ledger commitment makes silent deletion, replacement or late addition of trial events detectable.

```bash
pelicanbench build-study-freeze \
  --root . \
  --freeze-type data-freeze \
  --study-id PB-2026.08-v1-candidate \
  --input runs/blinded/results.jsonl \
  --input runs/blinded/failures.jsonl \
  --input human-calibration/blinded-responses.jsonl \
  --ledger-head runs/campaign/ledger-verification.json \
  --output artifacts/study-freezes/data-freeze.json
```

Data freezes fail closed when the ledger head is absent, malformed, empty or not content-addressed.

## Controlled authorization

The preferred command derives the authorization commitments from the verified manifests rather than accepting raw commitment strings:

```bash
pelicanbench authorize-model-unblinding-from-freezes \
  --root . \
  --private .secrets/pelicanbench/private-model-map.json \
  --analysis-lock artifacts/study-freezes/analysis-lock.json \
  --data-freeze artifacts/study-freezes/data-freeze.json \
  --output .secrets/pelicanbench/unblinding-authorization.json \
  --authorized-by <CUSTODIAN> \
  --reason "The prespecified analysis and complete blinded-data freeze both verify."
```

The resulting authorization is bound by HMAC to:

- the study;
- the private model mapping;
- the verified analysis-lock commitment;
- the verified data-freeze commitment;
- the custodian and reason; and
- the authorization timestamp.

The authorization and every unblinded output remain restricted artifacts. Publication packaging rejects them.

## Safety properties

The implementation rejects:

- absolute paths and repository-root escapes;
- symbolic-link inputs;
- duplicate or noncanonical file lists;
- private blinding maps, secret directories and unblinded outputs;
- malformed or non-lowercase SHA-256 commitments;
- naïve timestamps;
- data freezes without a nonempty ledger head;
- analysis locks that claim a ledger head;
- mismatched study, task or protocol identities; and
- modified, missing or substituted frozen files.

The local file system and Git history do not establish independent custody. A single developer can use the mechanism as a procedural safeguard, but E3 or E4 evidence requires operational role separation or an independently witnessed equivalent.

## Current maturity

The freeze builder, verifier, CLI workflow, campaign-ledger binding, keyed authorization integration, path controls and tamper tests are fixture-verified. No live model data, participant data, operational secret or real unblinding decision is represented by the committed fixtures.
