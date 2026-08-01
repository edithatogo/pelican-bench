# Model adapter specification

An adapter declares an immutable model identity, revision, access mechanism, accepted task tracks, output media, prompt transformation, seed semantics, timeout, cost accounting, and raw-response retention policy.

Adapters must return the original task ID, exact output, media type, non-secret metadata, and raw-response hash. They may not silently repair, strip, rerender, or retry output unless the intervention defines and records that behaviour. Provider safety refusals, truncation, timeout, and malformed artifacts are valid outcomes.

Remote code is disabled by default. Open-weight models are pinned by commit and container digest. Provider models record the provider’s version identifier and invocation date. Canary success is required before scheduled evaluation.
