# T14 steward interface

`scripts/t14_steward_app.py` is a repository-owned, offline alternative to a
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

The interface exposes only blinded aliases and before/after fixture renders. It
does not display source labels, automatic scores, requirements, or agent advice.
The generated response includes the manifest SHA-256 and a response SHA-256;
these are provenance aids, not a human signature or calibration result. The
steward remains the sole human rater and decision-maker. Agent summaries cannot
fill missing fields or establish independent review/E3 evidence.

This is a two-episode development rehearsal. It cannot promote T14, create a
held-out calibration set, or change score compatibility.
