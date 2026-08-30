#!/usr/bin/env bash
# Audit site-specific paths across the plugins, line by line.
# Author: Samuel Ahuno
#
# Why line-level: a file-level grep cannot make this call. The same file — and
# sometimes the same bullet — holds two different kinds of path:
#
#   EXECUTABLE  the path gets run or pasted into a command. Broken for anyone
#               else. Must resolve from the path registry instead.
#               e.g. `export APPTAINER_CACHEDIR=/data1/.../apptainer_cache`
#
#   REGISTRY    the path lives in a site profile (hpc-site/profiles/sites/) —
#               that IS the
#               site layer, so real paths are its purpose, not a leak. Swapping
#               this file out is how another cluster is onboarded.
#               Auto-classified; not part of the manual triage burden.
#
#   EVIDENCE    the path is a citation backing a dated claim. Nobody executes
#               it. Rewriting it destroys the ability to re-check the finding
#               and turns a falsifiable record into folklore.
#               e.g. "Confirmed 2026-05-05 on ... (/data1/.../clair3_v2.0.1_gpu.sif)"
#
# Every occurrence must be classified in docs/site-path-allowlist.tsv. Anything
# unclassified fails the audit. Entries are keyed by content hash, not line
# number, so moving a line is fine but EDITING it forces re-review — which is
# correct: a changed claim is a new claim.
#
# Usage:
#   tools/audit_site_paths.sh              # audit; exit 1 if anything unreviewed
#   tools/audit_site_paths.sh --bootstrap  # seed the allowlist with current hits

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

ALLOWLIST="docs/site-path-allowlist.tsv"
PATTERN='/data1/|greenbab|/home/ahunos'
SCAN_DIRS="plugins"
BOOTSTRAP=0
[ "${1:-}" = "--bootstrap" ] && BOOTSTRAP=1

hash_line() { printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | md5 -q 2>/dev/null || \
              printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | md5sum | cut -d' ' -f1; }

# Collect every matching line as file<TAB>hash<TAB>content
collect() {
  grep -rInE "$PATTERN" $SCAN_DIRS 2>/dev/null | while IFS=: read -r file line content; do
    printf '%s\t%s\t%s\n' "$file" "$(hash_line "$content")" "$(echo "$content" | cut -c1-120)"
  done
}

if [ "$BOOTSTRAP" -eq 1 ]; then
  mkdir -p "$(dirname "$ALLOWLIST")"
  {
    echo "# Site-path triage. One line per reviewed occurrence."
    echo "# class: EXECUTABLE (must be converted to the path registry) | EVIDENCE (citation, keep)"
    echo "# Keyed by content hash — editing the line forces re-review."
    printf '#file\tclass\thash\texcerpt\n'
    collect | grep -v '^plugins/hpc-site/profiles/sites/' | while IFS=$'\t' read -r f h c; do
      printf '%s\tUNREVIEWED\t%s\t%s\n' "$f" "$h" "$c"
    done
  } > "$ALLOWLIST"
  echo "Seeded $ALLOWLIST with $(grep -cv '^#' "$ALLOWLIST") occurrences — classify each, then re-run."
  exit 0
fi

if [ ! -f "$ALLOWLIST" ]; then
  echo "No $ALLOWLIST. Run: tools/audit_site_paths.sh --bootstrap" >&2
  exit 1
fi

UNREVIEWED=0; UNCONVERTED=0; EVIDENCE=0; REGISTRY=0; TOTAL=0
while IFS=$'\t' read -r file hash excerpt; do
  TOTAL=$((TOTAL+1))
  # The site layer is meant to hold real paths — that is what it is for.
  case "$file" in
    plugins/hpc-site/profiles/sites/*) REGISTRY=$((REGISTRY+1)); continue ;;
  esac
  # Key on file+hash, not hash alone: identical lines recur across files
  # (`export APPTAINER_CACHEDIR=...` appears in 4), so a hash-only lookup
  # matches the wrong row and silently mis-classifies.
  class=$(awk -F'\t' -v f="$file" -v h="$hash" '$1==f && $3==h {print $2; exit}' "$ALLOWLIST")
  case "$class" in
    EVIDENCE)   EVIDENCE=$((EVIDENCE+1)) ;;
    EXECUTABLE) UNCONVERTED=$((UNCONVERTED+1))
                printf '  \033[31mUNCONVERTED\033[0m %s\n       %s\n' "$file" "$excerpt" ;;
    *)          UNREVIEWED=$((UNREVIEWED+1))
                printf '  \033[33mUNREVIEWED\033[0m  %s\n       %s\n' "$file" "$excerpt" ;;
  esac
done < <(collect)

echo "──────────────────────────────────────────────────────────────"
printf 'total %d   registry %d (ok)   evidence %d (ok)   executable-unconverted %d   unreviewed %d\n' \
  "$TOTAL" "$REGISTRY" "$EVIDENCE" "$UNCONVERTED" "$UNREVIEWED"
[ $((UNCONVERTED + UNREVIEWED)) -eq 0 ] || exit 1
