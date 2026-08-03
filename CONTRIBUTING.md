# Contributing

PelicanBench is maintained as a single-developer research repository, but evidence-backed contributions and scorer challenges are welcome. The repository is intentionally operated as a one-person project: local checks are fast and deterministic, while GitHub remains the hosted source of truth for review, issue state and protected release evidence.

## Solo-developer loop

1. Open or select a Conductor/GitHub track (`track → phase → work package`).
2. Add or update the specification and phased plan before implementation.
3. Add tests before or with behavioural changes.
4. Run `./BOOTSTRAP_LOCAL.sh`, then `scripts/harness.sh`.
5. Inspect `git diff`, commit with a conventional commit, and push only the intended branch.
6. Regenerate projections with `python scripts/generate_workgraph.py` and synchronize issues with `python scripts/sync_github_issues.py --repo edithatogo/pelican-bench --apply` when metadata changes.
7. Read back hosted CI, Codecov and Renovate results before calling a change complete.

Local green is necessary but does not imply hosted CI, rights clearance, participant approval, independent reproduction or E3/E4 maturity. Keep those gates explicit in the relevant Conductor records.

GitHub repository conventions are kept in `.github/CODEOWNERS`, the issue templates and the pull-request template. Renovate is the sole dependency-update authority; do not add a second bot configuration.

Scorer changes require before/after results on the public regression set and a declaration of whether scores remain comparable. Security reports should follow `SECURITY.md` rather than public issues.

Never include sealed tasks, credentials or rights-restricted source media in a pull request. Use the issue and pull-request templates as a compact release checklist; do not bypass a failing gate by lowering thresholds or deleting evidence.
