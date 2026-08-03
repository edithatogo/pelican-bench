# Source-rights lifecycle

The source registry, rights ledger and per-record source declarations form one fail-closed
interface. A bridge may translate data into that interface, but it may not invent permission or
weaken an existing decision.

## Supported contract

PelicanBench currently accepts rights-ledger schema `1.0.0` only. Missing, older and newer
versions fail before decisions are used. The source registry and ledger remain committed JSON;
JSONL artifacts refer to them through stable `source_id` values or an explicit
`project-original*` declaration.

External importers must emit a staged, reviewable packet containing source identity, fixity,
proposed permitted use and the exact derived records. Import is a bridge into review, not a
bridge around review. Raw third-party bytes remain outside the repository unless the ledger
records permission for that artifact class and use.

## Migration policy

Any contract migration must:

1. add a version-specific reader or a deterministic offline migration command;
2. preserve original source IDs and decision rationale, recording any identifier mapping;
3. retain the pre-migration registry and ledger in release history;
4. demonstrate idempotence and fail-closed behavior with old, malformed and future-version
   fixtures;
5. rerun the rights audit and full repository harness; and
6. record a decision and release note stating compatibility and redistribution impact.

Automatic best-effort coercion is prohibited. A future schema is unsupported until its reader
and migration evidence ship together.

## Deprecation policy

A supported schema or bridge receives deprecation notice in at least one tagged release and
remains readable for one subsequent minor release. Security or legal necessity may shorten that
window, but requires an explicit decision record and migration instructions. Removal requires a
major compatibility decision, retained regression fixtures and a frozen bridge comparison.

Deprecating software support never deprecates evidence custody. Historical ledgers, hashes,
decision rationale and release-bound audit receipts remain archived and must not be silently
rewritten. A revoked or narrowed permission creates a new decision and release blocker; it does
not erase the earlier record or authorize continued redistribution.

## Compatibility classes

- Adding metadata that existing readers ignore is compatible only when permission meaning is
  unchanged.
- Adding a new decision vocabulary or changing default interpretation requires a bridge study
  and at least a minor contract version.
- Renaming source IDs, weakening fail-closed behavior or changing the meaning of an operative
  permission is breaking and requires a major compatibility decision.

This policy defines repository behavior only. It does not grant rights, resolve ambiguous terms
or replace accountable legal and source-owner review.
