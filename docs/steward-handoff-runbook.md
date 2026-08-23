# Steward hand-off runbook — deferred human decisions

Workflow-assisted completion path for the remaining release blockers. Everything that
can be prepared deterministically has been; each section lists the single decision or
action only the benchmark steward can take, with exact commands. Regenerate all staged
artifacts with `PATH="$PWD/.venv/bin:$PATH" bash scripts/harness.sh` first.

Staged bundle: `artifacts/publication-handoff/` — 45 files,
`sha256:7d2ea92658d7e59fcd1f205939f32aeaae90aa870ad2b3d4c8fd97589f435509`.

## RB-03-C1 — confirm exemption scope (decision only)

The NZ/VUW exemption (`participant-governance-determination-2026-08-23.yaml`) is
recorded. **Steward action:** one-line confirmation that the exemption covers the
recruited panels (general public plus expert panels). The preparer then flips
RB-05-C3-style evidence into RB-03-C1 and regenerates views.

## RB-04-C1/C2/C3 — remote publication (actions only)

All artifacts are staged and hash-bound.

```bash
git remote add origin <url> && git push origin main           # C1
git tag v0.6.0-alpha.1 && git push origin v0.6.0-alpha.1      # immutable release
gh workflow run ci.yml                                         # C2, or push triggers it
hf upload repo/dataset ... artifacts/publication-handoff/      # C3 (per publication-plan.json)
```

**Steward action:** execute (or delegate) the pushes and approve CI/HF runs; paste back
the run URLs and dataset DOI. The preparer records them as closure evidence.

## RB-04-C4 — second-environment reproduction

**Steward action:** designate a second machine/account (or a third party) and run:

```bash
bash scripts/verify_clean_clone.sh
```

Return the receipt JSON; the preparer attaches it to RB-04-C4.

## RB-02-C1 → RB-01-C3/RB-03-C2 — prospective pilot and calibration

Governance is no longer a blocker. The chain is deterministic once model outputs exist:

```bash
python -m pelicanbench.cli plan-prospective-pilot --root .   # frozen plan already committed
# run models via adapters (steward supplies keys through .env, never committed)
python -m pelicanbench.cli design-human-calibration \
  --source <model-outputs>.jsonl --target 96 \
  --output artifacts/human-calibration-design.json
python -m pelicanbench.cli export-human-evaluation-batch \
  --design artifacts/human-calibration-design.json --output artifacts/human-batch
```

**Steward actions:** choose the 4–6 model systems, set the spend cap, supply API keys,
give the recruitment go, and distribute `artifacts/human-batch/`. Collected responses
come back as JSONL; analysis, effect estimation and result drafting are preparer work
(`analyse-human-evaluation`, `analyse-human-calibration-jsonl`, `simulate-design-power`).

## RB-01-C4 / RB-02-C4 — independent challenge and uncertainty reporting

**Steward actions:** nominate an independent challenger for the scorer challenge bundle;
accept their findings report. Uncertainty reporting (C4) executes locally once pilot
data exists — no steward input beyond RB-02 go.
