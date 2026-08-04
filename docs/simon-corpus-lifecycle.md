# Simon corpus lifecycle

The Atom importer, metadata JSONL records and empirical-NLP `PromptRecord` bridge currently use
Simon corpus schema `1.0.0`. Derived analysis and persisted export reject absent or unsupported
versions; callers must not coerce future or legacy records by shape alone.

## Bridge contract

The bridge preserves `source_id`, stable `record_id`, source URL, timestamps, categories and
content fixity. It may expose content only when the in-memory corpus carries an analysis-compatible
rights status and retained text. Metadata-only ingestion remains the default. A bridge never
upgrades a rights decision or asserts archive completeness.

## Migration and deprecation

A new schema requires a deterministic offline migration, before-and-after fixtures, identifier
and fixity preservation checks, a rights-impact review, and a full harness run. Older records stay
available through tagged release history; historical derived reports are not silently regenerated.

Deprecation receives notice in at least one tagged release and support for one later minor release.
Removal requires a major compatibility decision, retained bridge fixtures, migration instructions
and a correction plan for affected downstream reports. Security or legal containment may disable
content export immediately, but metadata custody and prior receipts remain archived.

This policy governs repository compatibility. It does not grant redistribution permission or
replace validation against the complete source archive.
