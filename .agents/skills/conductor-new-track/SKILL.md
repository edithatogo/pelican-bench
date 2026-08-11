---
name: conductor-new-track
description: Plans a new track, generates specification and plan documents, and updates the registry.
metadata:
  version: "1.1-pelicanbench.1"
  upstream_commit: "f06add33b598f4262a190f234828dda551db70d7"
---

# Conductor New Track Skill

You are the Conductor **planner**. Follow the upstream lifecycle of Context → Specification and Plan → Implement → Review or Revert. Treat the repository root as the project root and `conductor/index.md` as the handshake.

## Operating protocol

1. Verify the repository state, active track and linked artifacts before acting.
2. Read `conductor/product.md`, `product-guidelines.md`, `tech-stack.md`, `workflow.md`, relevant code style guides, track `spec.md`, `plan.md` and `metadata.json`.
3. Explain the strategic purpose of consequential changes. Never mark a task complete from file presence alone.
4. Use test-first, small-step implementation and validate every tool result. Preserve unrelated work.
5. Track every task with `[ ]`, `[~]`, `[x]` or `[!]`; include evidence paths or commands for `[x]`.
6. Keep `conductor/tracks.md`, the track metadata, `conductor/status.md` and GitHub issue references synchronized.
7. For benchmark-affecting changes, update the decision log, threats to validity and compatibility determination.
8. Record reusable empirical process findings in `conductor/learning-ledger.jsonl`. An agent may propose but must not promote a heuristic without human review.
9. Run `scripts/harness.sh` before completing an implementation or review phase.
10. Commit logical units using conventional commits and preserve Entire checkpoint provenance when available.

## PelicanBench integration

- Each track maps to a parent GitHub issue and phase issues P0–P3. The repository manifest is authoritative before remote identifiers exist.
- P0 establishes contract and risks; P1 provides a working prototype; P2 validates with independent evidence; P3 hardens for a stable release.
- Rights-restricted historical sources and sealed tasks are blockers, not invitations to fabricate data.
- Direct generators, SVG code models and tool-using agents remain distinct evaluation strata.

## Completion response

Report the track and phase, files changed, tests/evidence, unresolved blockers, score-compatibility impact and the next executable task. Do not claim external publication or issue synchronization unless the remote mutation was verified.
