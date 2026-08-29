#!/usr/bin/env bash
# fusion_call_validation.sh — pattern for gene-fusion DNA-level validation.
#
# Validates a list of candidate gene fusion calls (BCR-ABL,
# RUNX1-RUNX1T1, IGH translocations) against the BAMs that produced
# them. Distinct from RNA-level fusion validation (Arriba, STAR-Fusion):
# this skill validates that chimeric DNA reads support each
# breakpoint, not that fusion transcripts are expressed.
#
# Run pattern:
#   bash examples/fusion_call_validation.sh <calls.tsv> <output_dir>
#
# calls.tsv schema (tab-separated, '#' header):
#   #event_id  patient  host_chrom  host_pos  tumor_bam  normal_bam  svlen_bp
#
# Notes for fusion-specific runs:
#   - Use --rubric gene_fusion (looser n-reads threshold, tighter
#     breakpoint concordance, repeats not flagged).
#   - The "target contig" is the partner gene region. For
#     reciprocal translocations, run twice: once with each partner
#     as --target-contig.
#   - For BCR-ABL where ABL1 is on chr9 and BCR is on chr22, use
#     chr9 as host and chr22 as target (or vice versa). The BAM
#     records will have the partner's region in the SA tag.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="${SKILL_DIR}/scripts"

CALLS_TSV="${1:-}"
OUT_DIR="${2:-}"
TARGET_CONTIG="${3:-chr22}"  # default: BCR-side for an ABL-host run

if [[ -z "${CALLS_TSV}" || -z "${OUT_DIR}" ]]; then
    echo "Usage: $0 <calls.tsv> <output_dir> [target_contig]"
    exit 2
fi

mkdir -p "${OUT_DIR}/data"

# 1. Extract.
python3 "${SCRIPTS}/extract_chimeric_reads.py" \
    --calls "${CALLS_TSV}" \
    --target-contig "${TARGET_CONTIG}" \
    --output-dir "${OUT_DIR}/data" \
    --flanking-bp 500   # tighter than viral — fusion breakpoints sit at exon boundaries

# 2. Validate with the gene_fusion rubric.
python3 "${SCRIPTS}/compute_validation_report.py" \
    --calls "${CALLS_TSV}" \
    --per-int-dir "${OUT_DIR}/data/per_integration" \
    --rubric gene_fusion \
    --target-contig "${TARGET_CONTIG}" \
    --output "${OUT_DIR}/data/fusion_validation_report.tsv"

# 3. Render.
python3 "${SCRIPTS}/render_supp_table_caption.py" \
    --validation-tsv "${OUT_DIR}/data/fusion_validation_report.tsv" \
    --output "${OUT_DIR}/Methods_validation.md"

echo "=== DONE ==="
echo "Output: ${OUT_DIR}/data/fusion_validation_report.tsv"
