#!/bin/bash
# mosdepth-scope-warning.sh
# WARN if `mosdepth --by <X.bed>` restricts coverage to non-canonical contigs only
# (e.g., viral / spike-in / decoy contigs without any host autosomes / sex / MT).
#
# Why: the ATLL Project_17424 cohort QC was scoped viral-only by design, which left
# no host hg38 per-chromosome coverage data. Discovered post-hoc — required a full
# mosdepth re-run on 12 BAMs for manuscript host-coverage QC. This hook surfaces
# the scope mismatch at command-design time instead.
#
# Trigger: tool_name == "Bash" and command matches /\bmosdepth\b.*--by\s+\S+/
# Action:  warn to stderr (visible to Claude); exit 0 (does not block).
#
# Author: Samuel Ahuno
# Date: 2026-05-02

# Portable JSON parsing (prefers jq, falls back to python3, warns loudly
# if neither exists rather than silently passing everything through).
. "${BASH_SOURCE[0]%/*}/lib/json.sh"
json_backend_check || exit 0

INPUT=$(cat)
TOOL_NAME=$(json_get "$INPUT" tool_name)
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND=$(json_get "$INPUT" tool_input.command)
[ -z "$COMMAND" ] && exit 0

# Match mosdepth invocation with --by <path>; capture path
# Supports apptainer/singularity exec wrappers, conda activate prefixes, etc.
echo "$COMMAND" | grep -qE '\bmosdepth\b' || exit 0
echo "$COMMAND" | grep -qE '\bmosdepth\b.*--by[[:space:]]+[^[:space:]|;&]+' || exit 0

# Extract the BED path immediately after --by
BED=$(echo "$COMMAND" \
  | grep -oE '\bmosdepth\b.*' \
  | grep -oE '\-\-by[[:space:]]+[^[:space:]|;&]+' \
  | head -1 \
  | sed -E 's/^--by[[:space:]]+//' \
  | tr -d '"'"'")

# If we couldn't extract a path, abort silently (don't false-positive on edge cases)
[ -z "$BED" ] && exit 0

# If the path contains shell variables ($VAR / ${VAR}), we can't resolve at hook time.
# Skip the check rather than warn incorrectly.
case "$BED" in *'$'*) exit 0 ;; esac

# If the path doesn't exist on disk (BED created earlier in same compound command,
# or relative path not resolvable from hook cwd), skip silently.
[ -f "$BED" ] || exit 0

# Canonical host-genome contigs we look for. Covers hg38/mm10/mm39 ("chr1"... style)
# AND Ensembl/GRCh37 ("1"... style without prefix). Presence of ANY one of these
# means the BED contains real host data; no warning.
#
# We check the FIRST column only (BED chromosome) and skip comment lines.
HOST_HITS=$(awk 'BEGIN{n=0}
  /^#/ {next}
  NF==0 {next}
  {
    chr=$1
    if (chr=="chr1" || chr=="chr2" || chr=="chr3" || chr=="chrX" || chr=="chrY" || chr=="chrM" || \
        chr=="1"    || chr=="2"    || chr=="3"    || chr=="X"    || chr=="Y"    || chr=="MT") n++
  }
  END{print n}' "$BED" 2>/dev/null)

# Default to 0 if awk failed for any reason
HOST_HITS=${HOST_HITS:-0}

# Total non-comment row count, for reporting
TOTAL_ROWS=$(awk '/^#/ {next} NF==0 {next} {n++} END{print n+0}' "$BED" 2>/dev/null)
TOTAL_ROWS=${TOTAL_ROWS:-0}

# Sample of contig names (first 5 distinct) for the warning message
CONTIGS_SAMPLE=$(awk '/^#/ {next} NF==0 {next} {print $1}' "$BED" 2>/dev/null \
  | awk '!seen[$0]++' \
  | head -5 \
  | tr '\n' ',' \
  | sed 's/,$//')

if [ "$HOST_HITS" -eq 0 ] && [ "$TOTAL_ROWS" -gt 0 ]; then
  cat >&2 <<EOF
[mosdepth-scope-warning] mosdepth --by ${BED} appears to restrict coverage to
non-canonical contigs only.
  - BED rows: ${TOTAL_ROWS}
  - First contigs: ${CONTIGS_SAMPLE}
  - Canonical host hits (chr1/2/3/X/Y/M or 1/2/3/X/Y/MT): 0

This will produce ${CONTIGS_SAMPLE}-only coverage QC. Per-chromosome host-genome
coverage (autosome distribution, X/Y dosage sex check, MT outliers) will NOT be
captured by this run.

If you also need host-genome QC for the manuscript, run a parallel mosdepth
WITHOUT --by (or with a BED that includes host autosomes). Reference:
results/20260502_hg38plusHTLV1EBV_cohort_host_qc/ has the pattern.

To suppress this warning, the BED must include >= 1 of:
  chr1, chr2, chr3, chrX, chrY, chrM (hg38/mm-style), or
  1, 2, 3, X, Y, MT (Ensembl/GRCh37-style).
EOF
fi

exit 0
