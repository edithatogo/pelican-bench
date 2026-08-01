# Entire provenance

This repository commits `.entire/settings.json` so Entire is enabled as a project policy from the first revision. Install the current Entire CLI and run:

```bash
entire enable --agent codex --project --telemetry=false
entire agent add claude-code
entire agent add gemini
entire status
```

A separate private checkpoint remote is recommended once created:

```bash
entire configure --checkpoint-remote github:edithatogo/pelican-bench-checkpoints
```

Entire captures development-session provenance. It does not replace PelicanBench run manifests, model revision pins, container digests or artifact hashes.
