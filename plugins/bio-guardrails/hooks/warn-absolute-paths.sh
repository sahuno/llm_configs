#!/bin/bash
# Warn when absolute paths are written into scripts
# Scripts should use relative paths for portability
# Author: Samuel Ahuno
# Date: 2026-02-17

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
NEW_STRING=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty')

if [ -z "$FILE_PATH" ] || [ -z "$NEW_STRING" ]; then
  exit 0
fi

# Only check scripts, not configs (configs legitimately have absolute paths)
if ! echo "$FILE_PATH" | grep -qE '\.(py|R|r|sh|smk|nf)$|Snakefile'; then
  exit 0
fi

# Skip config-loading files that reference profiles (those are expected to have absolute paths)
if echo "$FILE_PATH" | grep -qE '(config|profile|database)'; then
  exit 0
fi

# Check for /data1/ or /home/ absolute paths (common on MSKCC HPC)
if echo "$NEW_STRING" | grep -qE '"/data1/|"/home/|= /data1/|= /home/'; then
  echo "WARNING: Detected hardcoded absolute paths in $FILE_PATH. Use relative paths or load from config files for portability." >&2
fi

# Always allow — this is a warning, not a block
exit 0
