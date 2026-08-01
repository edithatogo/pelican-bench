#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1785542400}"

printf '%s\n' '== Syntax =='
python -m compileall -q src tests scripts hf envs

printf '%s\n' '== Unit, malicious, integration, and contract tests =='
python -m pytest -q --cov=pelicanbench --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90

printf '%s\n' '== Repository contracts =='
python scripts/validate_repo.py
python scripts/sync_conductor_install.py --check
python scripts/check_rights.py

printf '%s\n' '== GitHub work graph dry run =='
python scripts/sync_github_issues.py --summary-only
python scripts/create_github_project.py --summary-only

printf '%s\n' '== Deterministic fixture replay =='
rm -rf artifacts/harness-a artifacts/harness-b
python -m pelicanbench.cli run-fixture --output artifacts/harness-a >/dev/null
python -m pelicanbench.cli run-fixture --output artifacts/harness-b >/dev/null
python - <<'PY'
import json
from pathlib import Path
for name in ('harness-a','harness-b'):
    p=Path('artifacts')/name/'run-manifest.json'
    d=json.loads(p.read_text()); d.pop('created_at',None); p.write_text(json.dumps(d,sort_keys=True))
assert (Path('artifacts/harness-a/run-manifest.json').read_text()==Path('artifacts/harness-b/run-manifest.json').read_text())
PY

printf '%s\n' '== Deterministic SBOM =='
python scripts/generate_sbom.py --output artifacts/sbom-a.spdx.json >/dev/null
python scripts/generate_sbom.py --output artifacts/sbom-b.spdx.json >/dev/null
diff -u artifacts/sbom-a.spdx.json artifacts/sbom-b.spdx.json

if command -v cargo >/dev/null 2>&1; then
  cargo fmt --all --check
  cargo clippy --workspace --all-targets -- -D warnings
  cargo test --workspace
else
  printf '%s\n' 'Rust lane skipped: cargo unavailable.'
fi
if command -v mojo >/dev/null 2>&1; then
  mojo experiments/mojo/src/conformance.mojo
else
  printf '%s\n' 'Mojo lane skipped: compiler unavailable.'
fi
if command -v entire >/dev/null 2>&1; then
  entire status
else
  printf '%s\n' 'Entire runtime check skipped: CLI unavailable; project settings are validated.'
fi
printf '%s\n' 'HARNESS_OK'
