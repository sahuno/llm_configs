#!/bin/bash
# Validate YAML syntax after editing config files
# Author: Samuel Ahuno
# Date: 2026-02-17

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')

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
