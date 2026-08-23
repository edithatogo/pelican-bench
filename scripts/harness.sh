#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1785628800}"
if [[ "$(uname -s)" == "Darwin" && -d /opt/homebrew/lib ]]; then
  export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:/usr/lib${DYLD_FALLBACK_LIBRARY_PATH:+:${DYLD_FALLBACK_LIBRARY_PATH}}"
fi

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
python -m pelicanbench.cli release-readiness --profile v0.4-alpha

printf '%s\n' '== First-party ecosystem and model qualification audit =='
python -m pelicanbench.cli ecosystem-audit \
  --registry benchmark/integrations/ecosystem-registry.json \
  --output artifacts/ecosystem-audit.json >/dev/null
python -m pelicanbench.cli model-registry-status > artifacts/model-registry-status.json

printf '%s\n' '== GitHub work graph dry run =='
python scripts/sync_github_issues.py --summary-only
python scripts/create_github_project.py --summary-only

printf '%s\n' '== Prospective candidate, empirical bridge, and canary commitments =='
python -m pelicanbench.cli validate-v1-candidate \
  --root . --output artifacts/v1-candidate-validation.json >/dev/null
python -m pelicanbench.cli candidate-commitment \
  --root . --output "${PB_TMPDIR}/candidate-commitment.json" >/dev/null
diff -u benchmark/tasks/v1-candidate-commitment.json "${PB_TMPDIR}/candidate-commitment.json"
python -m pelicanbench.cli analyse-empirical-prompt-bridge \
  --root . --output "${PB_TMPDIR}/empirical-bridge.json" >/dev/null
python - "${PB_TMPDIR}/empirical-bridge.json" <<'PYINNER'
import json
import sys
from pathlib import Path
root = Path('.')
actual = json.loads(Path(sys.argv[1]).read_text())
expected_report = json.loads((root / 'benchmark/evidence/snapshots/castillo-2026-empirical-nlp-report.json').read_text())
expected_coverage = json.loads((root / 'benchmark/evidence/snapshots/castillo-2026-design-coverage.json').read_text())
assert actual['nlp_report'] == expected_report
assert actual['design_coverage'] == expected_coverage
PYINNER

printf '%s\n' '== Deterministic model and judge qualification plans =='
python -m pelicanbench.cli plan-model-qualification \
  --root . --output "${PB_TMPDIR}/model-qualification.json" >/dev/null
diff -u benchmark/evidence/snapshots/model-qualification-plan.json "${PB_TMPDIR}/model-qualification.json"
python -m pelicanbench.cli plan-judge-qualification \
  --root . \
  --output "${PB_TMPDIR}/judge-qualification.json" \
  --cells-output "${PB_TMPDIR}/judge-qualification-cells.jsonl" >/dev/null
diff -u benchmark/evidence/snapshots/judge-qualification-plan.json "${PB_TMPDIR}/judge-qualification.json"
diff -u benchmark/evidence/snapshots/judge-qualification-cells.jsonl "${PB_TMPDIR}/judge-qualification-cells.jsonl"

printf '%s\n' '== Deterministic staged prospective execution plan =='
python -m pelicanbench.cli plan-prospective-pilot \
  --root . \
  --output "${PB_TMPDIR}/prospective-a.json" \
  --cells-output "${PB_TMPDIR}/prospective-a-cells.jsonl" >/dev/null
python -m pelicanbench.cli plan-prospective-pilot \
  --root . \
  --output "${PB_TMPDIR}/prospective-b.json" \
  --cells-output "${PB_TMPDIR}/prospective-b-cells.jsonl" >/dev/null
diff -u "${PB_TMPDIR}/prospective-a.json" "${PB_TMPDIR}/prospective-b.json"
diff -u "${PB_TMPDIR}/prospective-a-cells.jsonl" "${PB_TMPDIR}/prospective-b-cells.jsonl"
diff -u benchmark/evidence/snapshots/prospective-pilot-plan.json "${PB_TMPDIR}/prospective-a.json"
diff -u benchmark/evidence/snapshots/prospective-pilot-plan-cells.jsonl "${PB_TMPDIR}/prospective-a-cells.jsonl"

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

printf '%s\n' '== Coverage-guided SVG mutation fuzzing =='
python -m pelicanbench.cli fuzz-svg \
  --source benchmark/fixtures/svg/pelican-bicycle-valid.svg \
  --guided \
  --cases 60 \
  --seed 20260801 \
  --budget-ms 2000 \
  --output artifacts/svg-fuzz-guided-report.json >/dev/null
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('artifacts/svg-fuzz-guided-report.json').read_text())
assert report['passed'], report
assert report['coverage_guided'] is True, report
assert report['coverage_lines'] > 0, report
PY

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
  --profile v0.4-alpha \
  --artifact artifacts/sbom-a.spdx.json >/dev/null

printf '%s\n' '== Deterministic publication hand-off =='
uv build --quiet --out-dir "${PB_TMPDIR}/dist"
ls "${PB_TMPDIR}/dist"/*.whl >/dev/null
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
  --profile v0.4-alpha \
  --output artifacts/repository-verification-receipt.json \
  --coverage coverage.xml \
  --artifact artifacts/ecosystem-audit.json \
  --artifact artifacts/model-registry-status.json \
  --artifact artifacts/release-manifest.json \
  --artifact artifacts/scorer-challenge-report.json \
  --artifact artifacts/svg-fuzz-report.json >/dev/null

printf '%s\n' '== Dependency-free quality, prose, toolchain, mutation, and taxonomy gates =='
python scripts/static_audit.py --output artifacts/static-audit.json
python scripts/prose_audit.py --output artifacts/prose-audit.json
python scripts/toolchain_preflight.py --output artifacts/toolchain-preflight.json >/dev/null
python scripts/mutation_smoke.py --output artifacts/mutation-smoke.json >/dev/null
python scripts/run_test_matrix.py --output artifacts/test-taxonomy.json >/dev/null
python scripts/quality_gate.py --output artifacts/quality-gate.json --coverage coverage.xml >/dev/null

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
if command -v basedpyright >/dev/null 2>&1; then
  printf '%s\n' '== Pyright =='
  basedpyright src/pelicanbench/adapters.py src/pelicanbench/verification.py
  printf '%s\n' '== Pyright public-API type completeness =='
  verify_score="$(basedpyright --verifytypes pelicanbench 2>/dev/null | awk '/Type completeness score/ {gsub(/%/,"",$4); print $4}')"
  echo "type completeness score: ${verify_score}%"
  awk -v s="${verify_score}" 'BEGIN { exit (s+0 < 90) }' || { echo 'pyright --verifytypes: completeness below 90%'; exit 1; }
else
  printf '%s\n' 'Pyright lane skipped: executable unavailable.'
fi
if command -v vale >/dev/null 2>&1; then
  printf '%s\n' '== Vale =='
  vale README.md docs conductor
else
  printf '%s\n' 'Vale lane skipped: executable unavailable; repository-native prose audit passed.'
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
