# Reproducible environments

PelicanBench distinguishes four environment records because no single file is sufficient evidence of reproducibility.

1. `pyproject.toml` declares supported dependency ranges and optional capability groups.
2. A future committed `uv.lock` will record the registry-resolved Python environment used for public benchmark releases.
3. `constraints/reference-environment.txt` records the dependency closure actually installed in the current development environment.
4. OCI image digests, SBOMs and the release manifest identify the environment used for a particular published run or release.

## Current alpha limitation

The development environment used to build the `v0.2.0-alpha.1` and `v0.3.0-alpha.1`
lines could not resolve all declared packages through its configured package mirror. A
synthetic or incomplete `uv.lock` would create false reproducibility confidence, so none
is committed. The reference-environment snapshot is explicitly an evidence artifact, not
a universal resolver lock.

The stable release gate therefore remains open until all of the following exist:

- a registry-resolved and reviewed `uv.lock`;
- an immutable OCI image digest;
- a dependency-aware SPDX or CycloneDX SBOM;
- a clean-clone reproduction from the release artifacts;
- a second-environment reproduction for V1;
- a release manifest that binds the source, tasks, scorer, environment and output artifacts.

## Regeneration

```bash
python scripts/generate_reference_environment.py
uv lock --python 3.13
bash scripts/verify_clean_clone.sh HEAD artifacts/clean-clone-receipt.json
```

The `uv lock` command is expected to fail rather than silently weaken requirements when the configured package index does not expose a required distribution.
