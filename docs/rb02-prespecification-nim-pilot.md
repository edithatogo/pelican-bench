# RB-02 prespecification — NVIDIA NIM student-tier model selection

Committed **before** any prospective pilot data exists, per the before-data locking
policy (T20-P2-W01). This record fixes the model set for the RB-02-C1 pilot run.

## Selection

| # | Model ID | Lineage | Canary result (2026-08-23) |
|---|---|---|---|
| 1 | `meta/llama-3.3-70b-instruct` | Meta Llama | HTTP 200, 83 s |
| 2 | `mistralai/mistral-nemotron` | Mistral × Nemotron | HTTP 200, 1 s |
| 3 | `deepseek-ai/deepseek-v4-flash-0731` | DeepSeek MoE | HTTP 200, 91 s |
| 4 | `nvidia/llama-3.3-nemotron-super-49b-v1` | NVIDIA post-trained | HTTP 200, 2 s |

## Constraint disclosure

The provider is the NVIDIA NIM student tier (`integrate.api.nvidia.com/v1`,
OpenAI-compatible). Model availability on this tier constrained the candidate pool:
`mistral-large-2`, `nemotron-ultra-253b`, and `gemma-3-27b` returned 404/410 on this
tier; two further candidates exceeded 115 s time-to-first-token. The four selected
models were chosen for training-lineage diversity *subject to* that availability
constraint, which is disclosed here rather than discovered after results.

## Runtime

- Profile: `generic-svg-openai-v1` (`hf/runtime-profiles.json`)
- Replicates: 3 per condition (seed-frozen design `PB-2026.08-v1-pilot`)
- Retries: bounded, failure-retaining; rate-limit backoff tuned empirically at canary
- Credentials: `NVAPI_KEY` from `.env`; never written to result metadata

## Threats to validity recorded

Provider-side model drift (NIM serves latest revisions; revision pinned as
`nim-integrate-api-2026-08-23`), free-tier latency variance, and single-provider
hosting. Second-environment reproduction (RB-04-C4) remains the independent check.
