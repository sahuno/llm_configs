#!/bin/bash
# Basic IGV screenshot — single BAM, inline region
# Author: Samuel Ahuno
# Date: 2026-02-13

set -euo pipefail

BAM="/path/to/sample.bam"
OUTDIR="/path/to/output"
GENOME="hg38"
IGVER_IMAGE="docker://sahuno/igver:latest"

mkdir -p "${OUTDIR}"

singularity exec \
    --bind /data1 \
    "${IGVER_IMAGE}" \
    igver \
        --input "${BAM}" \
        --regions "chr1:1000000-2000000" \
        --output "${OUTDIR}" \
        --genome "${GENOME}" \
        --dpi 300 \
        --overlap-display squish \
        --max-panel-height 200 \
        --no-singularity \
        --format png

echo "[SUCCESS] Screenshots saved to: ${OUTDIR}"
