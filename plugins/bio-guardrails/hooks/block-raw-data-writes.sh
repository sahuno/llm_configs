#!/bin/bash
# Block Write/Edit operations targeting data/raw/ directories
# Raw data is IMMUTABLE — all transformations go to data/processed/
# Author: Samuel Ahuno
# Date: 2026-02-17

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if echo "$FILE_PATH" | grep -qE '(^|/)data/raw/'; then
  echo "BLOCKED: Cannot write to data/raw/. Raw data is immutable. Write to data/processed/ instead." >&2
  exit 2
fi

exit 0
