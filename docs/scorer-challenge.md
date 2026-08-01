# Scorer challenge programme

PelicanBench invites adversarial submissions that obtain high automatic scores without visibly satisfying the task, or that visibly satisfy the task while receiving an unreasonably low score.

## Normative local challenge

The alpha release includes five executable metamorphic attacks:

1. remove semantic IDs, classes and accessibility labels;
2. rename every author-controlled semantic label;
3. add semantic words in source comments;
4. add fully transparent labelled geometry; and
5. add labelled geometry outside the visible canvas.

Run them with:

```bash
pelicanbench scorer-challenges \
  --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
  --output artifacts/scorer-challenge-report.json
```

The command fails the release harness unless render-equivalent mutations preserve semantic dimensions and none can improve the aggregate result. Known exploits and their exact regression tests are registered in `benchmark/scorer-challenges/known-exploits.json`.

## Additional challenge classes

- rendered prompt injection against visual judges;
- primitive substitution, transforms, clipping and masks;
- renderer disagreement;
- pathological path complexity or resource exhaustion;
- semantic near-neighbours, such as a pelican beside rather than riding a bicycle;
- object-part proxies, such as two circles without a coherent bicycle;
- adversarial captions and model-family judge bias; and
- preservation and edit-locality failures in repair tasks.

## Triage and disclosure

A submission is reproduced against immutable task, scorer, renderer and judge versions. Severity reflects effects on security, critical gates, semantic validity, ordering and diagnostics. Score-affecting fixes require a bridge study, explicit compatibility decision, retained fixture and public regression test.

The built-in suite is E2 developer evidence. RB-01 remains open until an independent challenge has been conducted and critical findings are resolved.
