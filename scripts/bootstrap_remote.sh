#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${1:-edithatogo/pelican-bench}"
OWNER="${REPO%%/*}"
DESCRIPTION="Longitudinal, ontology-driven visual and agentic drawing benchmark"

if ! command -v gh >/dev/null 2>&1; then
  printf 'gh CLI is required. Install and authenticate it, then rerun.\n' >&2
  exit 1
fi

gh auth status
if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" \
    --public \
    --source . \
    --description "$DESCRIPTION" \
    --disable-wiki
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/${REPO}.git"
else
  git remote add origin "https://github.com/${REPO}.git"
fi

git push -u origin main
git push origin --tags
python scripts/sync_github_issues.py --repo "$REPO" --apply
python scripts/create_github_project.py --owner "$OWNER" --repo "$REPO" --apply

printf 'Remote repository, native issue hierarchy and Projects v2 roadmap are synchronized.\n'
