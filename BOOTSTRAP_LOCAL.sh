#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${PELICANBENCH_REMOTE_URL:-https://github.com/edithatogo/pelican-bench.git}"
BRANCH="${PELICANBENCH_BRANCH:-main}"
APPLY_REMOTE="${PELICANBENCH_APPLY_REMOTE:-0}"
SYNC_ISSUES="${PELICANBENCH_SYNC_ISSUES:-0}"
PUBLISH_HF="${PELICANBENCH_PUBLISH_HF:-0}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "PelicanBench bootstrap: $ROOT"

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git branch -M "$BRANCH"

if command -v uv >/dev/null 2>&1; then
  uv sync --all-extras --dev
  # uv does not activate the environment it creates.  The harness deliberately uses
  # ``python`` so activate the repository-local interpreter before running any gate.
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -e '.[dev]'
else
  echo "Python 3 is required." >&2
  exit 1
fi

if [[ -x scripts/harness.sh ]]; then
  scripts/harness.sh
else
  python -m pytest
fi

if [[ "$APPLY_REMOTE" == "1" ]]; then
  git push --set-upstream origin "$BRANCH"
  git push origin --tags
fi

if [[ "$SYNC_ISSUES" == "1" ]]; then
  python scripts/sync_github_issues.py --apply
  python scripts/create_github_project.py --apply || true
fi

if [[ "$PUBLISH_HF" == "1" ]]; then
  python scripts/setup_huggingface.py --apply
fi

echo "Bootstrap complete."
