# Release and score-compatibility policy

Packages and APIs use semantic versioning. Benchmark datasets use calendar-labelled releases such as `PB-2026.08` and immutable Hub/Git tags.

## Change classes

- **Editorial:** documentation only; scores unaffected.
- **Compatible:** bug fix demonstrably preserving score distributions within a declared tolerance.
- **Bridge-required:** scorer, ontology, rendering, judge, or task change that may alter ranks or thresholds.
- **Breaking:** changed construct, critical gate, protected task distribution, or result schema.

Bridge-required and breaking changes publish old/new paired results on a frozen bridge set, distribution-drift analysis, human-alignment evidence where relevant, migration notes, and an explicit decision record. Historical results are never silently recalculated under a new scorer.

## Release artifacts

A release contains source, task and schema bundles, scorer versions, public commitments, fixture outputs, container/build metadata, SBOM, test report, benchmark/data/scorer cards, citation metadata, and checksums. Sealed task bytes remain outside public artifacts until retirement.
