# Entire and scientific provenance

`.entire/settings.json` enables Entire project provenance from the repository’s first commit. `scripts/bootstrap_entire.sh` installs agent hooks once the official CLI is present. Entire checkpoints preserve prompts, responses, tool calls, and changed files on a separate branch.

Entire does not replace an evaluation run manifest. A benchmark run remains reproducible without Entire and records task release, source commit, model revision, adapter, prompts, seed, environment digest, costs, artifacts, scores, and hashes. Development-session material may be private even when the benchmark repository is public.
