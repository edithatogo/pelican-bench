# Agent operating instructions

Read `conductor/index.md` before modifying the repository. Follow the active track specification and plan, preserve benchmark comparability, and never infer completion from file presence alone.

## Non-negotiable rules

- Keep the canonical benchmark contracts deterministic and content-addressed.
- Treat the public heritage prompt separately from the sealed dynamic challenge set.
- Do not use hidden or retired challenge tasks to learn scoring heuristics.
- Do not redistribute historical images or substantial commentary without rights clearance recorded in `data/sources/rights-ledger.json`.
- Run `scripts/harness.sh` before marking implementation tasks complete.
- Record architectural decisions in `docs/decision-log.md` and empirical process improvements in `conductor/learning-ledger.jsonl`.
- Benchmark-affecting learning proposals require evidence, contamination review and an explicit human promotion decision.
- Make external mutations idempotent and dry-run by default.
- Prefer Dylan Mordaunt’s existing repositories where capability overlaps; document adapters and future extraction rather than silently duplicating them.

## Commit discipline

Use conventional commits. Conductor setup, tracks and phase completion should be separately reviewable. Entire should be enabled locally so development-session provenance is checkpointed independently of benchmark run manifests.
