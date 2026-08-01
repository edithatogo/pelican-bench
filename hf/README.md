# Hugging Face topology

Target resources under `edithatogo`:

1. Dataset/benchmark: `edithatogo/pelican-bench`
2. Explorer Space: `edithatogo/pelican-bench-explorer`
3. OpenEnv Space: `edithatogo/pelican-bench-openenv`
4. Storage Bucket: raw traces, renders, Inspect logs and Trackio experiments

The versioned dataset remains the authoritative public record. Mutable Buckets
hold intermediate and large run artifacts; promoted release bundles are copied
into an immutable dataset revision. Model repositories may publish
`.eval_results/*.yaml` records that link to source traces. `setup_huggingface.py`
is dry-run by default and does not upload rights-controlled data.
