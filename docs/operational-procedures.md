# Operational procedures

This document defines operational ownership, incident response and archival procedures for the PelicanBench repository. It satisfies the P3 Hardened requirement for Track T00 (Foundation, governance and Conductor).

## Operational ownership

### Stewardship

- **Benchmark steward:** Dylan Mordaunt (initial maintainer)
- **Repository ownership:** Single-developer model with strong automation (per GOVERNANCE.md)
- **Decision authority:** Steward holds final authority for all decision classes (Editorial, Implementation, Benchmark, Governance)

### Responsibility matrix

| Domain | Owner | Backup | Escalation |
|--------|-------|--------|------------|
| Repository infrastructure (CI, scripts, tooling) | Steward | N/A | N/A |
| Benchmark contracts (tasks, schemas, ontologies) | Steward | N/A | N/A |
| Release process (packaging, manifests, attestations) | Steward | N/A | N/A |
| Rights and ethics (rights-ledger, human protocol) | Steward | N/A | Ethics review |
| Security (adversarial testing, scorer challenges) | Steward | N/A | Responsible disclosure |
| External publication (GitHub, Hugging Face, arXiv) | Steward | N/A | N/A |

### Operational invariants

- All external mutations are dry-run by default and idempotent
- No paid execution, secret exposure, or rights-restricted publication without explicit approval
- Sealed challenge tasks remain outside public artifacts until retirement
- Entire provenance captures agent-session checkpoints independently of benchmark runs

## Incident response

### Incident classes

| Class | Description | Response time | Example |
|-------|-------------|---------------|---------|
| **P0 - Critical** | Score-affecting regression, security exploit, rights violation | Immediate | Scorer metamorphic failure, label-injection exploit |
| **P1 - High** | CI failure, publication failure, calibration drift | Within 4 hours | Remote CI red, HF upload failure, judge calibration shift |
| **P2 - Medium** | Documentation gap, non-score-affecting bug, deferred CI lane | Within 24 hours | Vale warning, mypy error, missing doc |
| **P3 - Low** | Enhancement, refactor, technical debt | Next sprint | Code style, dependency update |

### Response procedure

1. **Detect:** Harness failure, CI alert, external report, or scheduled review
2. **Classify:** Assign incident class (P0–P3) and document in decision log
3. **Contain:** Revert, disable, or isolate the affected component
4. **Diagnose:** Root-cause analysis using reproducible evidence (manifests, SBOM, PROV)
5. **Resolve:** Fix with focused commit, regression test, and evidence update
6. **Verify:** Run full harness (`scripts/harness.sh`) and any targeted validation
7. **Record:** Update decision-log.md, learning-ledger.jsonl, and relevant evidence files
8. **Close:** Confirm resolution with steward; no silent closures

### Communication

- Internal: Decision log entries with `incident:` prefix
- External: GitHub issue for P0/P1; release notes for user-visible changes
- No public disclosure of sealed content or uncalibrated scores

### Rollback criteria

- Any score-affecting change that fails bridge study or distribution-drift analysis
- Any rights or ethics violation
- Any harness regression that cannot be resolved within the incident SLA

## Archival procedures

### Artifact categories

| Category | Retention | Storage | Access |
|----------|-----------|---------|--------|
| Release manifests, SBOMs, PROV/RO-Crate | Permanent | Git tags, Hub, local archives | Public |
| Benchmark run manifests (content-addressed) | Permanent | Hub datasets, local artifacts/ | Public |
| Agent session checkpoints (Entire) | 90 days | Entire checkpoint branch | Steward only |
| Sealed challenge tasks | Until retirement | Encrypted local, never public | Steward only |
| Human calibration data | Per protocol | Encrypted, access-controlled | Authorized only |
| CI logs and attestations | 1 year | GitHub Actions, local artifacts/ | Public |
| Mutation and fuzzing reports | 1 year | Local artifacts/ | Public |

### Archival workflow

1. **Package:** `python scripts/generate_release_manifest.py` produces deterministic manifest
2. **Bundle:** `python -m pelicanbench.cli publication-bundle` creates portable archive
3. **Verify:** `scripts/verify_clean_clone.sh` confirms reproducibility
4. **Tag:** Git tag with `v<version>` or `PB-<calendar>` format
5. **Publish:** Dry-run by default; explicit approval for GitHub, HF, OSF, arXiv
6. **Record:** Update release-blockers.json, decision-log.md, conductor metadata

### Cleanup

- Entire checkpoints: automatic expiry after 90 days
- Temporary harness artifacts: cleaned on `EXIT` trap in `scripts/harness.sh`
- Local build artifacts: `artifacts/` excluded from Git, recreated per run
- No silent deletion of tracked Conductor tracks (archive via `git mv` to `conductor/archive/`)

## Verification checklist

- [x] Operational ownership defined with responsibility matrix
- [x] Incident response classes, procedure, and rollback criteria documented
- [x] Archival categories, workflow, and cleanup procedures documented
- [x] Cross-referenced with GOVERNANCE.md, release-policy.md, quality-engineering.md
- [x] No sealed content or uncalibrated claims exposed

## References

- [GOVERNANCE.md](../GOVERNANCE.md) — Decision classes and stewardship
- [release-policy.md](./release-policy.md) — Release classes, evidence profiles, artifacts
- [quality-engineering.md](./quality-engineering.md) — Test taxonomy, CI tools, evidence interpretation
- [blinding-and-unblinding.md](./blinding-and-unblinding.md) — Blinding policy for calibration
- [human-evaluation-protocol.md](./human-evaluation-protocol.md) — Human participant governance
- [conductor/workflow.md](./conductor/workflow.md) — Track lifecycle and verification
- [conductor/learning-ledger.jsonl](./conductor/learning-ledger.jsonl) — Process observations