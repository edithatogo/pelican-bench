# T14 steward interface

`scripts/t14_steward_app.py` remains the historical two-episode rehearsal interface. It is a repository-owned, offline alternative to a
general annotation platform. It is deliberately standard-library-only and binds
the submitted response to the exact blinded manifest used by the rehearsal.

Run it from the repository root:

```sh
python scripts/t14_steward_app.py
```

Open `http://127.0.0.1:8765/`, then open the **Open instructions in another tab**
link before rating. That page explains what before/after mean and defines every
choice in the rubric. Complete each response and stop the process when finished.
The default output is
`benchmark/evidence/snapshots/t14-human-rating-response.json`. Validate it with:

```sh
python scripts/validate_t14_rating_template.py \
  benchmark/evidence/snapshots/t14-human-rating-response.json
```

The repository-owned rehearsal receipt can then be generated with:

```sh
PYTHONPATH=src python scripts/analyze_t14_steward_response.py
```

If the local SVG renderer is unavailable, the receipt records that limitation
instead of fabricating automatic metrics.

The validator also checks the response's canonical `response_sha256` when that
field is present; the analysis receipt carries both that canonical hash and the
raw response-file hash.

The interface exposes only blinded aliases and before/after fixture renders. It
does not display source labels, automatic scores, requirements, or agent advice.
The generated response includes the manifest SHA-256 and a response SHA-256;
these are provenance aids, not a human signature or calibration result. The
steward remains the sole human rater and decision-maker. Agent summaries cannot
fill missing fields or establish independent review/E3 evidence.

This is a two-episode development rehearsal. It cannot promote T14, create a
held-out calibration set, or change score compatibility.

## Frozen 96-episode preparation

`scripts/t14_frozen_steward_app.py` is the separate interface for the D044-frozen package. It
reads the two restricted custody artifacts without copying them into Git, validates their
exact public commitments, and exposes only 106 unique assignment aliases. Episode aliases,
source identifiers, duplicate identity, development/held-out allocation, automatic scores,
and agent advice never enter the browser payload or response ledger.

The default command is validation-only and cannot start collection:

```sh
PYTHONPATH=src python scripts/t14_frozen_steward_app.py \
  --restricted-alias-manifest /restricted/path/restricted-alias-manifest.json \
  --restricted-assignment-manifest /restricted/path/restricted-duplicate-schedule.json
```

Expected status is `ready-not-authorized`, with 96 source episodes, 106 assignments, 10
duplicates, `ratings_started: false`, and `unblinded: false`.

Serving requires all of `--serve`, `--rating-authorization`, `--ledger`, and `--output`.
The authorization must bind the D044 receipt and authorize ratings only. Ledger and output
paths must be outside the repository. Each response becomes a mode-0600, hash-chained JSONL
event and cannot be replaced; the final response is created once after all 106 assignments.
This route remains sole-steward and non-independent unless a separately governed multi-rater
protocol is executed.
