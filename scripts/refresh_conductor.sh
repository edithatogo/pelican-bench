#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHA="99ba10e1a11130fc159f681b7ba8803489239cbf"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --filter=blob:none --no-checkout https://github.com/gemini-cli-extensions/conductor.git "$TMP/conductor"
git -C "$TMP/conductor" checkout "$SHA"
rm -rf "$ROOT/.agents/plugins/conductor"
mkdir -p "$ROOT/.agents/plugins"
cp -a "$TMP/conductor" "$ROOT/.agents/plugins/conductor"
rm -rf "$ROOT/.agents/plugins/conductor/.git"
python "$ROOT/scripts/sync_conductor_install.py"
echo "Installed exact Conductor snapshot $SHA"
