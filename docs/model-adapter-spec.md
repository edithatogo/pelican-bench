# Model adapter specification

## Identity and eligibility

A model registry entry declares an immutable model identity, resolved revision, licence,
access mechanism, accepted benchmark tracks, output media, remote-code policy, runtime
profile, evaluation role, and first-party provenance. A candidate is eligible only when:

- its status is `eligible` or `reviewed`;
- the revision is immutable and resolved;
- required remote code is disabled;
- its licence is compatible with the intended evaluation and artifact publication;
- its track and media capabilities match the task; and
- its canary and runtime conditions have been reviewed.

The registry reports every blocker. `--allow-unqualified` is an explicit experimental
override and must not be used for a normative leaderboard run.

## Runtime profiles

Prompt transformations are separate, versioned records under
[`hf/runtime-profiles.json`](../hf/runtime-profiles.json). They can specify:

- system prompt;
- first-user prefix;
- assistant prefill;
- temperature and output budget;
- compatible model identifiers; and
- provenance notes.

This prevents a benchmark run from silently changing model-specific invocation conditions.
The first-party Qwen3 Hermes adapters use the recorded `/no_think` user prefix and empty
thinking-wrapper assistant prefill, but remain qualification-gated for SVG generation.

## OpenAI-compatible protocol boundary

`OpenAICompatibleAdapter` supports local Ollama, llama.cpp, MLX, Hermes and compatible
HTTP gateways without binding PelicanBench to one server implementation. It:

- sends a bounded `/v1/chat/completions` request;
- accepts an explicit token environment variable only;
- never records the token in adapter metadata;
- retains finish reason and usage metadata;
- extracts a complete SVG without repairing it;
- records HTTP, timeout, malformed-response and missing-SVG failures; and
- works with the run checkpoint and failure-retention machinery.

Remote code is disabled by default. Provider models record the provider version, invocation
time and available sampling settings. An adapter may retry only through an explicit bounded
retry policy whose attempts are recorded.

## Output contract

Every successful or failed invocation returns enough information to derive:

```text
scenario_id -> prompt_id -> condition_id -> trial_id
             -> artifact_id -> evaluation_id -> run_id
```

Adapters may not silently rewrite prompts, strip model output, rerender an artifact, choose
a best-of-N sample, or omit a refusal/failure. These are benchmark interventions and require
a separate condition and provenance record.

## First-party model lane

Dylan's public Qwen adapters are included because they provide a useful local-model lane,
not because they are presumed competitive. The prospective pilot planner currently marks
their cells `qualification-required`. To promote one, record:

1. exact Hub commit;
2. base model and adapter format;
3. licence review;
4. runtime profile;
5. successful valid-SVG canary;
6. resource and cost envelope;
7. repeated-output stability; and
8. decision record approving the evaluation role.
