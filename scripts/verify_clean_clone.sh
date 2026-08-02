#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="${1:-HEAD}"
OUTPUT="${2:-$ROOT/artifacts/clean-clone-receipt.json}"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1785628800}"
TMPDIR_ROOT="$(mktemp -d -t pelicanbench-clean-clone-XXXXXX)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

mkdir -p "$(dirname "$OUTPUT")"
git clone --local --no-hardlinks --quiet "$ROOT" "$TMPDIR_ROOT/repo"
git -C "$TMPDIR_ROOT/repo" checkout --detach --quiet "$REF"
COMMIT="$(git -C "$TMPDIR_ROOT/repo" rev-parse HEAD)"
TREE="$(git -C "$TMPDIR_ROOT/repo" rev-parse 'HEAD^{tree}')"
BEFORE="$(git -C "$TMPDIR_ROOT/repo" status --porcelain=v1 --untracked-files=all)"
if [[ -n "$BEFORE" ]]; then
  printf '%s\n' 'Clean clone was unexpectedly dirty before verification.' >&2
  exit 1
fi

(
  cd "$TMPDIR_ROOT/repo"
  export SOURCE_DATE_EPOCH
  bash scripts/harness.sh
) | tee "$TMPDIR_ROOT/harness.log"

AFTER="$(git -C "$TMPDIR_ROOT/repo" status --porcelain=v1 --untracked-files=all)"
if [[ -n "$AFTER" ]]; then
  printf '%s\n' 'Verification changed tracked or unignored files in the clean clone.' >&2
  printf '%s\n' "$AFTER" >&2
  exit 1
fi

ROOT="$ROOT" OUTPUT="$OUTPUT" COMMIT="$COMMIT" TREE="$TREE" \
HARNESS_LOG="$TMPDIR_ROOT/harness.log" SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" \
python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ['ROOT'])
output = Path(os.environ['OUTPUT'])
log = Path(os.environ['HARNESS_LOG'])
source_date_epoch = int(os.environ['SOURCE_DATE_EPOCH'])
receipt = {
    'schema_version': '1.0.0',
    'verification': 'local-clean-clone',
    'verified_at': datetime.fromtimestamp(source_date_epoch, tz=timezone.utc)
        .isoformat()
        .replace('+00:00', 'Z'),
    'source_repository': root.as_posix(),
    'commit': os.environ['COMMIT'],
    'tree': os.environ['TREE'],
    'harness_result': 'HARNESS_OK',
    'harness_log_sha256': 'sha256:' + hashlib.sha256(log.read_bytes()).hexdigest(),
    'python': platform.python_version(),
    'platform': platform.platform(),
    'limitations': [
        'This is a clean-clone reproduction in the same execution environment.',
        'It is E2 evidence and does not satisfy the V1 second-environment E4 gate.',
    ],
}
output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(output)
PY
