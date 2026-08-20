# T14 lifecycle, migration, and deprecation policy

The current repair metric contract is `render-repair-v1`. Its output fields and rendering
parameters are part of the evidence contract, not an invitation to silently reinterpret old
scores.

## Migration

Any change to mask threshold, canvas size, background, downsampling, component threshold,
locality formula, or field meaning must:

1. introduce a new method/version identifier;
2. retain the old implementation and fixtures for comparison;
3. run a deterministic bridge over the complete committed repair fixture set;
4. report changed values, rank/order changes, and compatibility impact; and
5. record a Conductor decision before any release or normative use.

Malformed, unsafe, or unsupported inputs remain rejected. Best-effort coercion and silent
historical-score recalculation are prohibited.

## Deprecation

`render-repair-v1` remains readable for at least one subsequent minor release after a
replacement is published. Removal requires a major compatibility decision, retained bridge
fixtures, and an archived manifest of prior outputs. Calibration may recommend a replacement,
but cannot silently change the historical method.
