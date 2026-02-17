#!/bin/bash
# DNA methylation IGV screenshots from ONT BAMs
# Requires BAM with MM/ML tags (from dorado/guppy basecalling)
# Author: Samuel Ahuno
# Date: 2026-02-13

set -euo pipefail

BAM="/path/to/modBaseCalls_dedup_sorted.bam"
REGIONS="/path/to/regions.bed"
OUTDIR="/path/to/methylation_screenshots"
GENOME="hg38"
IGVER_IMAGE="docker://sahuno/igver:latest"

mkdir -p "${OUTDIR}"

# --- Preprocess BED if needed: add 'chr' prefix ---
# Uncomment if BED uses non-chr chromosome names (1, 2, ...) but BAM uses chr1, chr2, ...
# BED_FIXED="${OUTDIR}/regions_chrPrefix.bed"
# awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' "${REGIONS}" > "${BED_FIXED}"
# REGIONS="${BED_FIXED}"

# --- Create IGV config for methylation coloring ---
IGV_CONFIG="${OUTDIR}/igv_methylation_prefs.txt"
echo "colorBy BASE_MODIFICATION" > "${IGV_CONFIG}"

# --- Run igver ---
# Settings: expand mode + large panel height for ONT long reads
singularity exec \
    --bind /data1 \
    "${IGVER_IMAGE}" \
    igver \
        --input "${BAM}" \
        --regions "${REGIONS}" \
        --output "${OUTDIR}" \
        --genome "${GENOME}" \
        --dpi 600 \
        --overlap-display expand \
        --max-panel-height 1000 \
        --no-singularity \
        --format png \
        --igv-config "${IGV_CONFIG}"

# Colors: Red = methylated CpG, Blue = unmethylated CpG
echo "[SUCCESS] Methylation screenshots saved to: ${OUTDIR}"
