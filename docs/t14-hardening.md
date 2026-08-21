# T14 hardening and resource budget

T14 repair scoring is a diagnostic boundary over untrusted SVG. It must remain bounded,
source-independent, and reproducible while calibration is pending.

## Budgets and controls

- Canonical render sizes are restricted to 32–4096 pixels per side by `render_svg`; the
  repair scorer uses a fixed 128-pixel canvas unless a versioned study protocol says otherwise.
- SVG inspection and rendering fail closed on malformed, unsafe, external-resource, or
  dimensionally inconsistent input.
- Render repair computes masks and connected components on bounded arrays; component analysis
  downsamples to at most 64×64 and ignores components below four pixels.
- Bounded and coverage-guided mutation campaigns enforce a per-case wall-clock budget and
  retain every failure rather than silently dropping it. The harness runs both campaigns.
- No repair score is promoted to a normative benchmark score; score compatibility remains
  `none-until-normative-release` until the authorized human-calibration pilot is complete.
- Dependency and provenance checks are inherited from the repository harness: Ruff, mypy,
  Pyright, Rust conformance, SBOM, static audit, and Entire provenance.

## Evidence

`tests/test_longitudinal_repair_trajectory.py`, `tests/test_fuzzing.py`,
`src/pelicanbench/render.py`, `src/pelicanbench/repair.py`, `src/pelicanbench/fuzzing.py`,
and `scripts/harness.sh` provide fixture and resource-budget evidence. These controls are
E2 hardening evidence, not empirical calibration or independent reproduction.
