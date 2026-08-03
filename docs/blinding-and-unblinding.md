# Model blinding and controlled unblinding

## Purpose

PelicanBench separates generator identity from the evidence shown to automatic judges and human raters. The objective is to reduce brand, laboratory and prior-reputation effects. Blinding does not make a one-person project organisationally independent, so the release records that limitation rather than overstating it.

## Threat addressed

A public model panel is small. A plain hash of the complete model-to-alias mapping would not be a safe commitment because an observer could enumerate every possible assignment of seven public models to seven aliases. PelicanBench therefore uses a keyed HMAC commitment. The public package contains aliases, a key commitment and an opaque mapping commitment, but cannot verify or enumerate the assignment without the secret key.

Aliases are study-specific. Reusing a key across projects would still produce different aliases because the study identifier is included in the HMAC domain. Operational policy nevertheless requires an independent key for every study.

## Public and restricted artifacts

The public manifest contains:

- the study and task-set commitments;
- stable aliases;
- the number of systems;
- a SHA-256 commitment to the key; and
- an HMAC commitment to the mapping.

It contains no raw model identifiers. The restricted map contains model identifiers and aliases, but never the key. The operational key is supplied through `PELICANBENCH_BLINDING_KEY` or an equivalent secret manager and is never committed.

The publication bundler rejects artifacts marked `restricted-unblinding-map`, `restricted-unblinding-authorization` or `secret-key-material`.

## Workflow

```bash
export PELICANBENCH_BLINDING_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

pelicanbench build-model-blinding \
  --root . \
  --public-output artifacts/blinding/public.json \
  --private-output .secrets/pelicanbench/private-model-map.json

pelicanbench blind-model-records \
  --source runs/results-with-model-ids.jsonl \
  --destination artifacts/blinded-results.jsonl \
  --private .secrets/pelicanbench/private-model-map.json
```

The private map and operational key must not be placed in a publication bundle, issue, log or agent checkpoint.

## Controlled unblinding

Unblinding is blocked until two verified research-object commitments exist:

1. the frozen confirmatory analysis plan; and
2. the frozen blinded data, exclusions and campaign-ledger head.

The preferred authorization command verifies both manifests and derives their commitments. It does not trust caller-supplied placeholder digests. See [Study freezes and controlled unblinding](study-freeze-and-unblinding.md).

```bash
pelicanbench authorize-model-unblinding-from-freezes \
  --root . \
  --private .secrets/pelicanbench/private-model-map.json \
  --analysis-lock artifacts/study-freezes/analysis-lock.json \
  --data-freeze artifacts/study-freezes/data-freeze.json \
  --output .secrets/pelicanbench/unblinding-authorization.json \
  --authorized-by <CUSTODIAN> \
  --reason "The prespecified analysis and complete blinded-data freeze both verify."

pelicanbench unblind-model-records \
  --source artifacts/blinded-results.jsonl \
  --destination .secrets/pelicanbench/unblinded-results.jsonl \
  --private .secrets/pelicanbench/private-model-map.json \
  --authorization .secrets/pelicanbench/unblinding-authorization.json
```

## Role separation

The preferred operational arrangement is:

- a custodian generates and retains the key and private map;
- generation workers use raw provider identifiers but emit blinded research records;
- automatic judges and human-rating systems receive only aliases and canonical renders;
- the primary analysis is frozen while aliases remain blinded; and
- the custodian authorises unblinding only after the data-freeze and analysis commitments are recorded.

A single developer can run the same workflow, but the resulting evidence must be described as procedural blinding rather than independent third-party blinding.

## Current maturity

The cryptographic aliases, keyed commitments, verified study-freeze manifests, campaign-ledger binding, restricted file permissions, publication guard, staged CLI workflow and controlled-unblinding receipt are fixture-verified. No operational key has been generated, no live model results have been blinded and no independent custodian has been appointed.
