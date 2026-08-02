# Quality engineering and constrained-environment verification

PelicanBench uses two complementary quality layers. Repository-native checks run with the
Python standard library and the benchmark's runtime dependencies. Authoritative third-party
checks run in CI when their executables are available. A missing executable is recorded as
`deferred-to-ci`; it is never converted into a passing result.

## Mandatory test taxonomy

Every release candidate executes eleven independently failing lanes:

1. unit tests;
2. integration tests;
3. end-to-end tests;
4. property and invariant tests;
5. mutation sentinels;
6. edge and boundary tests;
7. deterministic simulation tests;
8. consumer-driven contract tests;
9. metamorphic tests;
10. agent tests; and
11. bounded autonomous-agent tests.

`scripts/run_test_matrix.py` gives every lane a bounded execution budget and writes a
machine-readable receipt. The full suite separately enforces at least 90% branch-aware
coverage. The coverage total weights executable lines and branch arcs, matching
`coverage.py`; it does not average line and branch percentages.

## Repository-native floor

The dependency-free checks include:

- Python parsing and byte-code compilation;
- wildcard, unused-import, bare-exception and mutable-default detection;
- public API annotation checks;
- dynamic-code and unsafe subprocess checks;
- explicit network-timeout checks;
- JSON, JSONL, TOML and workflow validation;
- immutable GitHub Action pin validation;
- terminology, unsupported maturity-claim and placeholder checks;
- five mandatory source-level mutation sentinels;
- contract, candidate, empirical-NLP and assurance validation; and
- deterministic task, pilot, publication, SBOM and run-manifest replay.

These checks are deliberately narrower than Ruff, mypy, Pyright, Vale, Hypothesis and
mutmut. Their receipt states that limitation.

## CI-only authoritative tools

The CI configuration fails closed on:

```text
ruff check
ruff format --check
mypy --strict
pyright (strict mode)
Vale prose linting
Hypothesis property tests
mutmut scheduled mutation campaign
Codecov project and patch thresholds
```

Codecov requires 90% project and patch coverage. Renovate is configured with immutable
GitHub Action digests, vulnerability alerts, minimum release age, dependency grouping and
reviewed major updates.

## Evidence interpretation

A local `HARNESS_OK` demonstrates E2 fixture evidence for the checks that actually ran.
It does not establish that absent third-party tools passed, that remote CI is operational,
or that the benchmark is empirically calibrated. E3 requires prospective model and human
calibration evidence. E4 requires reproduction in an independently controlled environment.
