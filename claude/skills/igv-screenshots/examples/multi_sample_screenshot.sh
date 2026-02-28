#!/bin/bash
# Multi-sample IGV screenshots — compare tumor vs normal
# Author: Samuel Ahuno
# Date: 2026-02-13

set -euo pipefail

TUMOR_BAM="/path/to/tumor.bam"
NORMAL_BAM="/path/to/normal.bam"
REGIONS="/path/to/regions.bed"
OUTDIR="/path/to/IGV_hg38_tumor_normal_comparison"  # Convention: IGV_{genome}_{description}
GENOME="hg38"
IGVER_IMAGE="docker://sahuno/igver:latest"

mkdir -p "${OUTDIR}"

# Multiple BAMs are loaded into the same IGV session — each appears as a separate track
singularity exec \
    --bind /data1 \
    "${IGVER_IMAGE}" \
    igver \
        --input "${TUMOR_BAM}" "${NORMAL_BAM}" \
        --regions "${REGIONS}" \
        --output "${OUTDIR}" \
        --genome "${GENOME}" \
        --dpi 600 \
        --overlap-display squish \
        --max-panel-height 500 \
        --no-singularity \
        --format png

echo "[SUCCESS] Comparison screenshots saved to: ${OUTDIR}"

# --- Alternative: use a text file listing BAM paths ---
# Create tracks.txt with one BAM path per line:
#   /path/to/tumor.bam
#   /path/to/normal.bam
#
# Then use:
#   --input tracks.txt
