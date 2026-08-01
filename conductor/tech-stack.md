# Technology stack

## Normative core

- Python 3.13/3.14 for schemas, orchestration, analysis, Hugging Face integration and reference scorers.
- Rust 2024 as the planned hardened parsing, geometry, sandbox boundary and WebAssembly implementation.
- Mojo as an experimental acceleration and conformance lane, never the sole normative scorer before stability.
- JSON Schema, JSONL and Parquet/Arrow-compatible records for durable interfaces.

## Evaluation and analysis

Pydantic v2, defusedxml, JSON Schema, NumPy, optional SciPy/statsmodels/Pandas, Inspect AI adapters, OpenEnv-compatible environment contracts and blinded pairwise human evaluation.

## Infrastructure

GitHub Actions, immutable action pins before stable release, artifact attestations, SPDX SBOMs, Hugging Face datasets/Spaces/Jobs, OCI containers, Entire development provenance and content-addressed benchmark run manifests.

## Frontend

A dependency-light TypeScript/HTML PelicanCanvas prototype and a Gradio Hub explorer for V1; a framework can be selected only after the interaction model stabilises.
