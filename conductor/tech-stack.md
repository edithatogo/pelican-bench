# Technology stack

## Normative core

- Python 3.13 and 3.14 for schemas, orchestration, analysis, Hugging Face integration and reference scorers.
- Rust 2024 as the planned hardened parsing, geometry, sandbox boundary and WebAssembly implementation.
- Mojo as an experimental acceleration and conformance lane, never the sole normative scorer before stability.
- JSON Schema, JSON-LD, JSONL and Parquet or Arrow-compatible records for durable interfaces.

## Evaluation and analysis

Pydantic v2, defusedxml, CairoSVG, Pillow, JSON Schema, NumPy, optional SciPy, statsmodels and Pandas, Inspect AI adapters, OpenEnv-compatible environment contracts and blinded pairwise human evaluation.

## Reproducible environments

- `pyproject.toml` is the dependency contract.
- `uv.lock` is required for public benchmark releases once a complete registry resolution is available.
- `constraints/reference-environment.txt` is a snapshot of the installed development closure and is not a substitute for a resolver lock.
- OCI digests and release SBOMs bind published runs to concrete environments.
- Python 3.13 and 3.14 are exercised in remote CI; a clean-clone verification is required locally before packaging.

## Infrastructure

GitHub Actions with immutable commit pins, artifact attestations, dependency-aware SPDX SBOMs, Hugging Face datasets, Spaces and Jobs, OCI containers, Entire development provenance, W3C PROV, RO-Crate and content-addressed benchmark run and release manifests.

## Frontend

A dependency-light TypeScript and HTML PelicanCanvas prototype and a Gradio Hub explorer for V1. A larger frontend framework can be selected only after the interaction model stabilises.
