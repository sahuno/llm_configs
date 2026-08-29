#!/bin/bash
# Block Write/Edit operations targeting data/raw/ directories
# Raw data is IMMUTABLE — all transformations go to data/processed/
# Author: Samuel Ahuno
# Date: 2026-02-17

# Portable JSON parsing (prefers jq, falls back to python3, warns loudly
# if neither exists rather than silently passing everything through).
. "${BASH_SOURCE[0]%/*}/lib/json.sh"
json_backend_check || exit 0

INPUT=$(cat)
FILE_PATH=$(json_get "$INPUT" tool_input.file_path)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if echo "$FILE_PATH" | grep -qE '(^|/)data/raw/'; then
  echo "BLOCKED: Cannot write to data/raw/. Raw data is immutable. Write to data/processed/ instead." >&2
  exit 2
fi

exit 0
