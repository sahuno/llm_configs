#!/bin/bash
# Warn when hardcoded contig/chromosome names are written into scripts
# Contigs should always be parsed from genome sizes files or FASTA index
# Author: Samuel Ahuno
# Date: 2026-02-17

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
NEW_STRING=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty')

if [ -z "$FILE_PATH" ] || [ -z "$NEW_STRING" ]; then
  exit 0
fi

# Only check scripts, not configs/data files
if ! echo "$FILE_PATH" | grep -qE '\.(py|R|r|sh|smk|nf)$|Snakefile'; then
  exit 0
fi

# Check for hardcoded chromosome lists (common pattern: ["chr1", "chr2", ...] or chr1 chr2 ...)
if echo "$NEW_STRING" | grep -qE '(chr[0-9]+.*chr[0-9]+|"chr[0-9]+".*"chr[0-9]+"|chrX.*chrY)'; then
  echo "WARNING: Detected hardcoded chromosome names. Parse contigs from the genome sizes file or FASTA index instead of hardcoding them." >&2
fi

# Always allow — this is a warning, not a block
exit 0
