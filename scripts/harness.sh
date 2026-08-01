#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1785542400}"

cleanup() {
  if [[ -n "${PB_TMPDIR:-}" && -d "${PB_TMPDIR}" ]]; then
    rm -rf "${PB_TMPDIR}"
  fi
}
trap cleanup EXIT
PB_TMPDIR="$(mktemp -d -t pelicanbench-harness-XXXXXX)"

printf '%s\n' '== Syntax =='
python -m compileall -q src tests scripts hf envs

printf '%s\n' '== Unit, malicious, integration, and contract tests =='
python -m pytest -q --cov=pelicanbench --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90

printf '%s\n' '== Repository contracts and release assurance =='
python scripts/validate_repo.py
python scripts/generate_schemas.py --check
python scripts/generate_issue_manifest.py --check
python scripts/generate_conductor_docs.py --check
python scripts/sync_conductor_install.py --check
python scripts/check_rights.py
python -m pelicanbench.cli release-readiness --profile v0.3-alpha

printf '%s\n' '== First-party ecosystem and model qualification audit =='
python -m pelicanbench.cli ecosystem-audit \
  --registry benchmark/integrations/ecosystem-registry.json \
  --output artifacts/ecosystem-audit.json >/dev/null
python -m pelicanbench.cli model-registry-status > artifacts/model-registry-status.json

printf '%s\n' '== GitHub work graph dry run =='
python scripts/sync_github_issues.py --summary-only
python scripts/create_github_project.py --summary-only

printf '%s\n' '== Prespecified task-set reproducibility =='
python -m pelicanbench.cli generate-v1-pilot --output "${PB_TMPDIR}/v1-pilot.jsonl" >/dev/null
diff -u benchmark/tasks/v1-pilot.jsonl "${PB_TMPDIR}/v1-pilot.jsonl"
diff -u benchmark/tasks/v1-pilot-commitment.json "${PB_TMPDIR}/v1-pilot-commitment.json"

printf '%s\n' '== Deterministic prospective execution plan =='
python -m pelicanbench.cli plan-pilot \
  --output "${PB_TMPDIR}/pilot-a.json" >/dev/null
python -m pelicanbench.cli plan-pilot \
  --output "${PB_TMPDIR}/pilot-b.json" >/dev/null
diff -u "${PB_TMPDIR}/pilot-a.json" "${PB_TMPDIR}/pilot-b.json"
diff -u "${PB_TMPDIR}/pilot-a-cells.jsonl" "${PB_TMPDIR}/pilot-b-cells.jsonl"

printf '%s\n' '== Normative scorer metamorphic challenge =='
mkdir -p artifacts
python -m pelicanbench.cli scorer-challenges \
  --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
  --output artifacts/scorer-challenge-report.json >/dev/null
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('artifacts/scorer-challenge-report.json').read_text())
assert report['passed'], report
assert len(report['outcomes']) >= 5
PY

printf '%s\n' '== Bounded deterministic SVG mutation fuzzing =='
python -m pelicanbench.cli fuzz-svg \
  --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
  --cases 130 \
  --budget-ms 1000 \
  --output artifacts/svg-fuzz-report.json >/dev/null

printf '%s\n' '== Cross-renderer bridge =='
if command -v inkscape >/dev/null 2>&1; then
  python -m pelicanbench.cli renderer-bridge \
    --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
    > artifacts/renderer-bridge.json
  python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('artifacts/renderer-bridge.json').read_text())
assert not report['materially_different'], report
PY
else
  printf '%s\n' 'Renderer bridge skipped: Inkscape unavailable.'
fi

printf '%s\n' '== Deterministic fixture replay =='
rm -rf artifacts/harness-a artifacts/harness-b
python -m pelicanbench.cli run-fixture --output artifacts/harness-a >/dev/null
python -m pelicanbench.cli run-fixture --output artifacts/harness-b >/dev/null
python - <<'PY'
import json
from pathlib import Path
for name in ('harness-a','harness-b'):
    path = Path('artifacts') / name / 'run-manifest.json'
    value = json.loads(path.read_text())
    value.pop('created_at', None)
    path.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')
assert (
    Path('artifacts/harness-a/run-manifest.json').read_text()
    == Path('artifacts/harness-b/run-manifest.json').read_text()
)
PY

printf '%s\n' '== Deterministic SBOM =='
python scripts/generate_sbom.py --output artifacts/sbom-a.spdx.json >/dev/null
python scripts/generate_sbom.py --output artifacts/sbom-b.spdx.json >/dev/null
diff -u artifacts/sbom-a.spdx.json artifacts/sbom-b.spdx.json
python scripts/generate_release_manifest.py \
  --output artifacts/release-manifest.json \
  --profile v0.3-alpha \
  --artifact artifacts/sbom-a.spdx.json >/dev/null

printf '%s\n' '== Deterministic publication hand-off =='
python -m pelicanbench.cli publication-bundle \
  --output "${PB_TMPDIR}/publication-a" \
  --artifact artifacts/scorer-challenge-report.json \
  --artifact artifacts/svg-fuzz-report.json >/dev/null
python -m pelicanbench.cli publication-bundle \
  --output "${PB_TMPDIR}/publication-b" \
  --artifact artifacts/scorer-challenge-report.json \
  --artifact artifacts/svg-fuzz-report.json >/dev/null
diff -ru "${PB_TMPDIR}/publication-a" "${PB_TMPDIR}/publication-b"

printf '%s\n' '== repository-standards verification receipt =='
python -m pelicanbench.cli verification-receipt \
  --profile v0.3-alpha \
  --output artifacts/repository-verification-receipt.json \
  --coverage coverage.xml \
  --artifact artifacts/ecosystem-audit.json \
  --artifact artifacts/model-registry-status.json \
  --artifact artifacts/release-manifest.json \
  --artifact artifacts/scorer-challenge-report.json \
  --artifact artifacts/svg-fuzz-report.json >/dev/null

if command -v ruff >/dev/null 2>&1; then
  printf '%s\n' '== Ruff =='
  ruff check src tests scripts
  ruff format --check src tests scripts
else
  printf '%s\n' 'Ruff lane skipped: executable unavailable.'
fi
if command -v mypy >/dev/null 2>&1; then
  printf '%s\n' '== Mypy =='
  mypy src/pelicanbench
else
  printf '%s\n' 'Mypy lane skipped: executable unavailable.'
fi
if command -v cargo >/dev/null 2>&1; then
  printf '%s\n' '== Rust conformance =='
  cargo fmt --all --check
  cargo clippy --workspace --all-targets -- -D warnings
  cargo test --workspace
else
  printf '%s\n' 'Rust lane skipped: cargo unavailable.'
fi
if command -v mojo >/dev/null 2>&1; then
  printf '%s\n' '== Mojo conformance =='
  mojo experiments/mojo/src/conformance.mojo
else
  printf '%s\n' 'Mojo lane skipped: compiler unavailable.'
fi
if command -v entire >/dev/null 2>&1; then
  printf '%s\n' '== Entire provenance =='
  entire status
else
  printf '%s\n' 'Entire runtime check skipped: CLI unavailable; project settings are validated.'
fi
printf '%s\n' 'HARNESS_OK'
