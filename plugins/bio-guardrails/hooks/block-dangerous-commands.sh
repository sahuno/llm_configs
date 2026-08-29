#!/bin/bash
# Block dangerous commands that could destroy raw data or project directories
# Exit 2 = block action, Exit 0 = allow
# Author: Samuel Ahuno
# Date: 2026-02-17

COMMAND=$(cat | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Block rm -rf on data/raw directories
if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|.*)(data/raw|data/inbox)'; then
  echo "BLOCKED: Cannot delete files in data/raw/ or data/inbox/. Raw data is immutable." >&2
  exit 2
fi

# Block broad rm -rf that could wipe project dirs
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+(\.|\.\.|\*|/data1)'; then
  echo "BLOCKED: Refusing broad rm -rf that could destroy project data. Be more specific." >&2
  exit 2
fi

# Block snakemake --reason (does not exist)
if echo "$COMMAND" | grep -qE 'snakemake.*--reason'; then
  echo "BLOCKED: snakemake has no --reason argument. Did you mean --summary or --list-rules?" >&2
  exit 2
fi

exit 0
