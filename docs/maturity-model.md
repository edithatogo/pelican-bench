# Evidence maturity and hardening model

PelicanBench separates capability implementation from scientific validation. A phase cannot
be described as validated merely because code, tests or documentation exist.

| Level | Name | Minimum evidence |
|---|---|---|
| **E0** | Defined | Scope, intended inference, invariants, threats, rights and exit criteria are documented. |
| **E1** | Implemented | An executable vertical slice exists with stable interfaces and deterministic fixtures. |
| **E2** | Fixture-verified | Unit, property, metamorphic, malicious and reproducibility tests pass on controlled fixtures. |
| **E3** | Empirically calibrated | Prospective data demonstrate construct coverage, reliability, uncertainty and human alignment where applicable. |
| **E4** | Independently reproduced | A second environment or investigator reproduces the declared result from immutable public artifacts. |
| **E5** | Operationally hardened | Drift monitoring, incident response, archival, cost controls, deprecation and maintenance are demonstrated over time. |

## Evidence domains

A maturity claim must identify which domains it covers:

- **Contract:** schema, invariants, versioning, failure modes, rights and threats.
- **Correctness:** unit, property, metamorphic, malicious, mutation and golden tests.
- **Scientific validity:** construct coverage, human alignment, uncertainty, task effects and sensitivity analyses.
- **Reproducibility:** immutable inputs, environment identity, hashes and clean-clone rerun.
- **Security:** bounded resources, isolation, least privilege and adversarial scorer testing.
- **Operations:** observability, cost caps, retries, resumability, rollback and incident handling.
- **Governance:** decision record, issue synchronization, release notes and bridge policy.
- **Sustainability:** dependency budget, maintenance ownership, drift audit and archive path.

## Completion rules

1. Track phase state and evidence level are separate fields.
2. `complete` means the listed phase tasks are complete, not that the capability is E5.
3. Software tests can establish at most E2 unless the claim itself concerns only software behaviour.
4. Human alignment, model comparisons and historical trends require empirical evidence before E3.
5. Remote CI configuration is not remote CI evidence. A workflow must have run successfully.
6. Independent reproduction requires a distinct environment or investigator and immutable inputs.
7. A reopened critical defect lowers the affected claim and linked track until regression evidence is recorded.
8. Every score-affecting change records compatibility, migration and bridge implications.

The machine-readable assurance case is in
[`benchmark/assurance-case.json`](../benchmark/assurance-case.json). Cross-track release
blockers are in [`conductor/release-blockers.json`](../conductor/release-blockers.json).
