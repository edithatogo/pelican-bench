# Hugging Face architecture

PelicanBench uses three independently versioned Hub surfaces:

1. `edithatogo/pelican-bench` dataset for public tasks, schemas, cards, results, retired holdouts, and human annotations.
2. `edithatogo/pelican-bench-explorer` Space for browsing, pairwise comparison, and score explanations.
3. `edithatogo/pelican-bench-openenv` Space for the agent environment boundary.

Large mutable traces belong in a Bucket or temporary job storage and are promoted into a versioned dataset only after validation. Model discovery creates candidates; capability, revision, licence, remote-code, canary, duplicate, and budget gates determine eligibility. “Every model” means every eligible model, with exclusions recorded.
