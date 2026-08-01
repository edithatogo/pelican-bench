# Governance

Dylan Mordaunt is the initial maintainer and benchmark steward. The repository is deliberately optimised for a single developer with strong automation rather than a simulated large team.

## Decision classes

- **Editorial:** documentation or non-score-affecting presentation changes.
- **Implementation:** internal changes that preserve public contracts and scores.
- **Benchmark:** task, ontology, rubric, scorer, aggregation or eligibility changes.
- **Governance:** licensing, rights, sealed-set access or release-policy changes.

Benchmark and governance decisions require an ADR or decision-log entry, evidence from the regression suite, a contamination assessment and a release-compatibility determination. Major score-affecting changes create a new benchmark major or dated release and, where possible, a bridge study.

Automated agents may propose changes but cannot autonomously promote a heuristic into the normative benchmark or disclose sealed content.
