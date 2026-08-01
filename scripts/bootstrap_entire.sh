#!/usr/bin/env bash
set -euo pipefail
if ! command -v entire >/dev/null 2>&1; then
  echo "Entire CLI is not installed. Install it from the official Entire distribution, then rerun." >&2
  exit 2
fi
entire enable --agent codex --project --telemetry=false
entire agent add claude-code || true
entire agent add gemini || true
entire status
