# RB-02 Prespecification Amendment 1 — Provider Contingency (2026-08-24)

Amends `docs/rb02-prespecification-nim-pilot.md`. Recorded before any amended-cell
data exists. Motivating event: NVIDIA NIM returned sustained HTTP 500
(`urn:inference-connection`) for `mistralai/mistral-nemotron` across replicate
waves 2–3 (59/66 calls failed) and HTTP 504s for
`deepseek-ai/deepseek-v4-flash-0731`, while other NIM cells remained healthy —
indicating per-model backend degradation on the provider side, not client fault.

## A1. Provider routing contingency
Trials record endpoint/adapter identity in provenance automatically. If a model
is unavailable on its primary provider but the *same revision-equivalent model*
is served by an alternate OpenAI-compatible provider, the cell may be executed
on the alternate provider with no change to model identity, tasks, seeds, or
scoring. Registered alternate routes:
- `deepseek/deepseek-v4-flash-0731` via OpenRouter (`router`-compatible API),
  canary result 2026-08-24: 30/30 scored, mean aggregate 0.256.
- Rationale: identical weights via a different route minimises construct drift.

## A2. mistral-nemotron wave invalidation and retry policy
Replicate waves 2–3 of `mistralai/mistral-nemotron` on NIM are invalidated by
the provider-side failures above (wave 1 of the current numbering likewise
affected). Policy, in order:
1. Retry the three mistral waves on NIM after ≥24 h, ≤72 h from amendment time.
2. If NIM remains unavailable at retry, substitute the closest same-family
   prespecified alternative `mistralai/mistral-medium-3.1` (OpenRouter) as a
   *model substitution* (documented construct change, weaker than A1), running
   all three replicates fresh.
Invalidated waves are retained on disk as failure evidence; they are excluded
from analysis aggregates.

## A3. Cross-replicate completeness rule
A model cell is analysable when ≥2 replicate waves exist with ≥80% task-level
scorecard coverage; per-task statistics use only complete-case replicates.
This rule was applied mechanically by `scripts/merge_pilot_replicates.py`
before any aggregate was reported.

— ox-alpha, conductor execution agent, on steward delegation 2026-08-24.
