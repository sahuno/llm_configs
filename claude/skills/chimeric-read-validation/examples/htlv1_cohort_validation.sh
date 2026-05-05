#!/usr/bin/env bash
# htlv1_cohort_validation.sh — full reproduction of the ATLL HTLV-1
# integration validation run (May 2026).
#
# Reproduces /data1/greenbab/projects/ont/Project_17424/results/
#   20260503_hg38plusHTLV1EBV_cohort_chimeric_read_evidence/
# but using the generalized skill scripts. Expected verdict: 9/9 PASS.
#
# Run:
#   bash examples/htlv1_cohort_validation.sh
#
# Requires:
#   - samtools and bedtools on PATH
#   - python3 with stdlib only (no pandas/pysam)

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="${SKILL_DIR}/scripts"

# ---- Inputs -----------------------------------------------------------
PROJECT_ROOT="/data1/greenbab/projects/ont/Project_17424"
TABLE1="${PROJECT_ROOT}/docs/manuscript/tables/Table1_htlv1_integrations.tsv"
BAM_DIR="${PROJECT_ROOT}/analysis/htlv1_offshelf_eval/20260501_hg38plusHTLV1EBV_cohort/realign"
RMSK_BED="/data1/greenbab/database/RepeatMaskerDB/repeatmasker_dot_org/hg38/RepLibrary20140131/rmsk_all_repeats_hg38.bed.gz"
MOSDEPTH_PATTERN="${PROJECT_ROOT}/results/20260502_hg38plusHTLV1EBV_cohort_host_qc/mosdepth_host/{patient}_tumor.mosdepth.summary.txt"

# ---- Run dir ----------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${PROJECT_ROOT}/results/${TS}_hg38plusHTLV1EBV_chimeric_read_validation"
DATA_DIR="${RUN_DIR}/data"
mkdir -p "${DATA_DIR}"

# ---- Build the calls TSV from the manuscript Table 1 ------------------
CALLS_TSV="${DATA_DIR}/calls.tsv"
awk -v BAM="${BAM_DIR}" 'BEGIN{
    print "#event_id\tpatient\thost_chrom\thost_pos\ttumor_bam\tnormal_bam\tsvlen_bp\tprovirus_class\tstrict_somatic\tseverus_id"
}
NR == 1 { next }   # skip Table 1 header (also "#"-prefixed; awk treats as data)
/^#/ { next }
{
    eid = $1 "_" $2 "_" $3 "_" $4
    print eid "\t" $1 "\t" $2 "\t" $3 "\t" BAM "/" $1 "_tumor.combined.bam\t" \
          BAM "/" $1 "_normal.combined.bam\t" $5 "\t" $6 "\t" $7 "\t" $4
}' "${TABLE1}" > "${CALLS_TSV}"

echo "Built ${CALLS_TSV}:"
head -3 "${CALLS_TSV}"
echo ""

# ---- 1. Extract chimeric reads ----------------------------------------
python3 "${SCRIPTS}/extract_chimeric_reads.py" \
    --calls "${CALLS_TSV}" \
    --target-contig HTLV1 \
    --output-dir "${DATA_DIR}" \
    --flanking-bp 1000

# ---- 2. Compute validation report -------------------------------------
python3 "${SCRIPTS}/compute_validation_report.py" \
    --calls "${CALLS_TSV}" \
    --per-int-dir "${DATA_DIR}/per_integration" \
    --rubric viral_integration \
    --target-contig HTLV1 \
    --rmsk-bed "${RMSK_BED}" \
    --mosdepth-summary-pattern "${MOSDEPTH_PATTERN}" \
    --output "${DATA_DIR}/cohort_validation_report.tsv"

# ---- 3. Render manuscript-ready Markdown ------------------------------
python3 "${SCRIPTS}/render_supp_table_caption.py" \
    --validation-tsv "${DATA_DIR}/cohort_validation_report.tsv" \
    --output "${RUN_DIR}/Methods_validation.md"

echo ""
echo "=== DONE ==="
echo "Run directory: ${RUN_DIR}"
echo "Validation TSV: ${DATA_DIR}/cohort_validation_report.tsv"
echo "Markdown: ${RUN_DIR}/Methods_validation.md"
echo ""
echo "Expected: 9/9 PASS verdicts."
