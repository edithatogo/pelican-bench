# PelicanBench autonomous setup prompt

Extract this archive into a new local directory, open a terminal in the repository root, and act autonomously.

1. Read `AGENTS.md`, `README.md`, the Conductor context and status files, and the current protocol lock before changing anything.
2. Run `./BOOTSTRAP_LOCAL.sh` to install dependencies and execute the complete local harness.
3. Preserve the existing Git history and annotated tags. Confirm that `origin` is `https://github.com/edithatogo/pelican-bench.git` and that the branch is `main`.
4. Fix any reproducible failures you encounter. Do not weaken coverage, mutation, typing, linting, prose, security, rights, protocol-lock, assurance, or release gates. Add regression tests for every fix.
5. Refresh generated Conductor status, work-package and GitHub issue manifests only through their source generators. Keep the hierarchy `track → phase → work package` and preserve evidence-backed completion states.
6. Run the complete test taxonomy, coverage, static/prose audits, mutation smoke, deterministic simulation, contract, metamorphic, agent and autonomous tests. Run Ruff, mypy, Pyright, Vale, Hypothesis, full mutation, Rust and other configured CI tools when available.
7. Commit any necessary fixes with clear conventional commits. Never rewrite public history or force-push.
8. Push `main` and all tags to the remote. Then run the repository’s idempotent GitHub issue and Projects synchronizers with `--apply` so all parent issues, nested subissues, labels and milestones are created or updated.
9. Publish the prepared Hugging Face dataset and Spaces using the repository scripts when authenticated. Do not upload rights-restricted source material or secrets.
10. Verify the remote CI, Codecov and Renovate results. Address failures until all available gates pass.
11. Produce a final report listing exact commit and tag identifiers, tests and coverage, remote URLs, issue counts, Hugging Face artifacts, remaining empirical or permission-dependent blockers, and any claims that remain below E3 maturity.

Prefer completing safe work over asking questions. Stop only for missing credentials, an irreversible external action not already authorised above, or a genuine rights or research-governance decision.
