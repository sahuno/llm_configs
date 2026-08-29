#!/bin/bash
# Run snakemake dry-run after editing .smk or Snakefile files
# Only runs if snakemake is available and a Snakefile exists nearby
# Author: Samuel Ahuno
# Date: 2026-02-17

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')

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
