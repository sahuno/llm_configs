#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-02-23
# Purpose: Replace the old lab name with "Greenbaum Lab" across all text files in llm_configs.
# The OLD string is split to prevent this script from matching itself on future runs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Split the misspelling so this file doesn't match its own search pattern
OLD="Green""berg Lab"
NEW="Greenbaum Lab"

echo "Scanning: $REPO_ROOT"
echo "Replacing: '$OLD' → '$NEW'"
echo ""

# Find all text files, excluding git internals and binary formats
mapfile -t files < <(
    grep -rl "$OLD" "$REPO_ROOT" \
        --include="*.md" \
        --include="*.sh" \
        --include="*.py" \
        --include="*.R" \
        --include="*.yaml" \
        --include="*.yml" \
        --include="*.txt" \
        --include="*.json" \
        2>/dev/null
)

if [ ${#files[@]} -eq 0 ]; then
    echo "No occurrences of '$OLD' found. Nothing to do."
    exit 0
fi

echo "Files to update:"
for f in "${files[@]}"; do
    echo "  $f"
done
echo ""

for f in "${files[@]}"; do
    sed -i "s/${OLD}/${NEW}/g" "$f"
    echo "Fixed: $f"
done

echo ""
echo "Done. ${#files[@]} file(s) updated."
echo "Run: grep -r \"${OLD}\" \"${REPO_ROOT}\" to verify no occurrences remain."
