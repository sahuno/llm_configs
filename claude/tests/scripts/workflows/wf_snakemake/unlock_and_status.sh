#!/usr/bin/env bash
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: 2026-02-26
# Purpose: Unlock a stale Snakemake run and report pipeline status.
#          Run this when a coordinator was killed mid-run (e.g., by Claude Code timeout).
#
# Usage: bash unlock_and_status.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAKEFILE="${SCRIPT_DIR}/Snakefile"
PROFILE_DIR="${SCRIPT_DIR}/profiles/slurm_fixed"
EXPERIMENT_DIR="/data1/greenbab/users/ahunos/apps/llm_configs/claude/tests"

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log_msg "=== Snakemake unlock + status check ==="
log_msg "Experiment dir: ${EXPERIMENT_DIR}"

# Check lock status
LOCK_DIR="${EXPERIMENT_DIR}/.snakemake/locks"
if [[ -d "${LOCK_DIR}" ]] && [[ -n "$(ls -A "${LOCK_DIR}" 2>/dev/null)" ]]; then
    log_msg "Stale locks found:"
    ls -la "${LOCK_DIR}"
    log_msg "Unlocking..."
    snakemake --unlock \
      -s "${SNAKEFILE}" \
      --workflow-profile "${PROFILE_DIR}" \
      --directory "${EXPERIMENT_DIR}"
    log_msg "Unlocked."
else
    log_msg "No stale locks detected."
fi

# Dry-run to show what would run
log_msg ""
log_msg "=== Dry-run status ==="
snakemake -n \
  -s "${SNAKEFILE}" \
  --workflow-profile "${PROFILE_DIR}" \
  --directory "${EXPERIMENT_DIR}" 2>&1 || true

log_msg "=== DONE: unlock_and_status.sh completed successfully ==="
