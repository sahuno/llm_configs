#!/usr/bin/env bash
# Optional CLI only. Do not install as a hook — Grok/Claude have native /copy.
# Author: Samuel Ahuno
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$ROOT/save_llm_response.py"
DEST="$HOME/.llm_configs"

if [[ ! -f "$SCRIPT" ]]; then
  echo "missing $SCRIPT" >&2
  exit 1
fi

mkdir -p "$DEST/cache"
cp "$SCRIPT" "$DEST/save_llm_response.py"
chmod +x "$DEST/save_llm_response.py" "$ROOT/install.sh"

echo "Installed CLI: python3 $DEST/save_llm_response.py last"
echo "Grok/Claude: use builtin /copy instead of hooks."
echo "This installer does not register hooks or slash commands."
