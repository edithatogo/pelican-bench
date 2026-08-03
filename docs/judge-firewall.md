# Automatic-judge input firewall

## Purpose

A canonical render can be source-independent and still contain text intended to influence a multimodal evaluator. PelicanBench therefore treats source security and judge-input safety as separate gates.

The V1 candidate does not request visible text. The normative policy in `benchmark/judges/firewall-policy.json` therefore retains text-bearing artifacts in the generation denominator but quarantines them from automatic semantic judging. Quarantine is not deletion: validity, rendering, cost, latency and failure outcomes remain reportable.

## Evidence boundary

The automatic judge receives only the canonical raster, the task information permitted for its role and a content-addressed judge contract. It never receives:

- SVG source;
- element identifiers or classes;
- comments or metadata;
- declared semantic roles; or
- hidden evaluation labels.

Blind open-set judges also do not receive the original prompt.

## Decisions

The firewall returns one of three decisions:

- `eligible`: the source gate passed, the canonical render is nonblank and no prohibited visible text was detected;
- `quarantined`: the artifact remains a retained benchmark outcome but automatic semantic scores are withheld; or
- `rejected`: source security or rendering failed.

A quarantined artifact fails the `judge_input_safe` critical gate. A precomputed semantic assessment cannot restore credit after quarantine.

## Threats and residual risk

The V1 implementation detects visible SVG text elements and instruction-like source text. It does not claim reliable optical recognition of words converted to paths, rasterised lettering or pictographic prompt injection. Before any judge reaches E3 status, its qualification study must include render-level adversarial canaries, same-family sensitivity and human comparison. A later text-bearing benchmark requires a separate masking or optical-text protocol and a bridge study rather than relaxing the V1 rule silently.

## Regression evidence

- `benchmark/fixtures/adversarial/visible-judge-prompt-injection.svg`
- `benchmark/scorer-challenges/known-exploits.json`
- `tests/test_judge_firewall.py`
- `src/pelicanbench/judge_firewall.py`
