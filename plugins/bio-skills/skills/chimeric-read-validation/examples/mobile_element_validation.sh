#!/usr/bin/env bash
# mobile_element_validation.sh — pattern for mobile element insertion
# (L1, Alu, SVA) validation.
#
# Validates a list of candidate mobile element insertions against the
# BAMs that produced them. The "target contig" is the consensus element
# sequence (e.g., L1HS_consensus, AluY_consensus) — typically a custom
# contig added to the reference for MELT / xTea / TLDR / Mobster
# detection.
#
# Run pattern:
#   bash examples/mobile_element_validation.sh <calls.tsv> <output_dir> <element_contig>
#
# calls.tsv schema (tab-separated, '#' header):
#   #event_id  patient  host_chrom  host_pos  tumor_bam  normal_bam  svlen_bp  provirus_class
#
# Where provirus_class repurposes the column: "intact" for full-length
# insertions, "defective" for 5'-truncated / partial insertions (most
# L1 insertions are 5'-truncated; SVA and Alu are usually full-length).
#
# Notes for MEI-specific runs:
#   - Use --rubric mobile_element (looser breakpoint concordance, wider
#     concordance window for TSD ambiguity, repeats never flagged).
#   - Set svlen_bp to the actual element length (≈ 300 for Alu,
#     ≈ 6000 for L1, ≈ 2000 for SVA), NOT including the TSD.
#   - For population-polymorphic MEIs (1000G panel hits), expect
#     non-zero T/N overlap — relax the verdict logic if appropriate.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="${SKILL_DIR}/scripts"

CALLS_TSV="${1:-}"
OUT_DIR="${2:-}"
ELEMENT_CONTIG="${3:-L1HS_consensus}"

if [[ -z "${CALLS_TSV}" || -z "${OUT_DIR}" ]]; then
    echo "Usage: $0 <calls.tsv> <output_dir> [element_contig]"
    exit 2
fi

mkdir -p "${OUT_DIR}/data"

# 1. Extract.
python3 "${SCRIPTS}/extract_chimeric_reads.py" \
    --calls "${CALLS_TSV}" \
    --target-contig "${ELEMENT_CONTIG}" \
    --output-dir "${OUT_DIR}/data" \
    --flanking-bp 1000

# 2. Validate with mobile_element rubric.
python3 "${SCRIPTS}/compute_validation_report.py" \
    --calls "${CALLS_TSV}" \
    --per-int-dir "${OUT_DIR}/data/per_integration" \
    --rubric mobile_element \
    --target-contig "${ELEMENT_CONTIG}" \
    --output "${OUT_DIR}/data/mei_validation_report.tsv"

# 3. Render.
python3 "${SCRIPTS}/render_supp_table_caption.py" \
    --validation-tsv "${OUT_DIR}/data/mei_validation_report.tsv" \
    --output "${OUT_DIR}/Methods_validation.md"

echo "=== DONE ==="
echo "Output: ${OUT_DIR}/data/mei_validation_report.tsv"
