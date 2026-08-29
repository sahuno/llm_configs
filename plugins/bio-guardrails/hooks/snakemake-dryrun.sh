#!/bin/bash
# Run snakemake dry-run after editing .smk or Snakefile files
# Only runs if snakemake is available and a Snakefile exists nearby
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

# Only trigger for snakemake-related files
if ! echo "$FILE_PATH" | grep -qE '\.(smk|snake)$|Snakefile'; then
  exit 0
fi

# Find the Snakefile directory
DIR=$(dirname "$FILE_PATH")
SNAKEFILE=""
for candidate in "$DIR/Snakefile" "$DIR/../Snakefile" "$DIR/workflow/Snakefile"; do
  if [ -f "$candidate" ]; then
    SNAKEFILE=$(realpath "$candidate")
    break
  fi
done

if [ -z "$SNAKEFILE" ]; then
  echo "Note: No Snakefile found near $FILE_PATH — skipping dry-run."
  exit 0
fi

SNAKEDIR=$(dirname "$SNAKEFILE")

if command -v snakemake &> /dev/null; then
  echo "Running snakemake dry-run for $SNAKEFILE..."
  cd "$SNAKEDIR" && snakemake -n --quiet 2>&1 | tail -20
  if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "WARNING: Snakemake dry-run failed. Check the DAG for errors."
  else
    echo "Snakemake dry-run passed."
  fi
fi

exit 0
