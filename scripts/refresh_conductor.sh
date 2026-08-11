#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHA="f06add33b598f4262a190f234828dda551db70d7"
PLUGIN="$ROOT/.agents/plugins/conductor"

git -C "$ROOT" submodule update --init --checkout -- .agents/plugins/conductor
git -C "$PLUGIN" fetch origin main --tags
git -C "$PLUGIN" checkout --detach "$SHA"
python "$ROOT/scripts/sync_conductor_install.py" --check
echo "Installed exact Conductor snapshot $SHA"
