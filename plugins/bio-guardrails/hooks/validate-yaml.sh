#!/bin/bash
# Validate YAML syntax after editing config files
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

# Only check YAML files
if ! echo "$FILE_PATH" | grep -qE '\.(yaml|yml)$'; then
  exit 0
fi

if command -v python3 &> /dev/null; then
  RESULT=$(python3 -c "import yaml; yaml.safe_load(open('$FILE_PATH'))" 2>&1)
  if [ $? -ne 0 ]; then
    echo "WARNING: Invalid YAML syntax in $FILE_PATH:"
    echo "$RESULT"
  fi
fi

exit 0
