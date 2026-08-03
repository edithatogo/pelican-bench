# Human-calibration operations

## Adjudication

Original ratings are immutable. The adjudication queue identifies records requiring expert or consensus review without replacing the source observations.

Items enter the queue when:

- open-set labels lack the prespecified modal agreement;
- mean recognition confidence is below the threshold; or
- prompt-aware criterion ratings span the prespecified range.

Each queue item is content-addressed and records only identifiers, counts, agreement and reason. Adjudication outcomes become a separate analysis layer.

## Stopping rules

Human collection can stop only when every prespecified gate passes:

- minimum valid responses for each stage;
- maximum invalid-response fraction;
- maximum recognition Brier score;
- minimum nominal agreement for required open-set fields; and
- minimum repeat consistency for required fields.

Failure of any gate keeps collection or remediation open. Missing reliability metrics fail closed rather than being interpreted as satisfactory.

## Commands

```bash
pelicanbench build-calibration-adjudication \
  --source responses.jsonl \
  --output artifacts/calibration-adjudication.jsonl

pelicanbench evaluate-calibration-stopping \
  --analysis calibration-analysis.json \
  --output artifacts/calibration-stopping.json
```

These tools are E2 operational contracts. Governance approval, recruitment, participant data and empirical reliability remain required for E3 calibration.
