#!/usr/bin/env bash
# run_snakemake.sh -- Submit modkit pileup Snakemake workflow on SLURM
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: 2026-03-05
# Purpose: Launch the modkit pileup workflow as a SLURM coordinator job.
#          Uses --mem-per-cpu (never --mem) to avoid SLURM_MEM_PER_NODE propagation.

#SBATCH --job-name=smk_modkit_pileup
#SBATCH --partition=componc_cpu
#SBATCH --account=greenbab
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4000
#SBATCH --time=24:00:00
#SBATCH --output=logs/snakemake_coordinator_%j.out
#SBATCH --error=logs/snakemake_coordinator_%j.err

set -euo pipefail

# ---------------------------------------------------------------------------
# CRITICAL: Unset SLURM_MEM_PER_NODE to prevent propagation to child jobs.
# When the coordinator is submitted with --mem=XG, SLURM sets this variable.
# snakemake-executor-plugin-slurm wraps rules in srun, which inherits this
# variable and conflicts with the per-cpu memory requested by rules.
# ---------------------------------------------------------------------------
unset SLURM_MEM_PER_NODE

# ---------------------------------------------------------------------------
# Paths -- edit these for your run
# ---------------------------------------------------------------------------

# Absolute path to the Snakefile
SNAKEFILE="/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/snakemake/evals/snakemake-workspace/iteration-1/eval-1-modkit-workflow/with_skill/outputs/Snakefile"

# Absolute path to the run config (copy config_template.yaml and fill in)
CONFIGFILE="/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/snakemake/evals/snakemake-workspace/iteration-1/eval-1-modkit-workflow/with_skill/outputs/config.yaml"

# Absolute path to the SLURM workflow profile
PROFILE="/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/snakemake/evals/snakemake-workspace/iteration-1/eval-1-modkit-workflow/with_skill/outputs/profiles/slurm"

# ---------------------------------------------------------------------------
# Create log directory
# ---------------------------------------------------------------------------
mkdir -p logs

# ---------------------------------------------------------------------------
# Unlock if stale lock exists from a previous killed run
# ---------------------------------------------------------------------------
snakemake \
    --snakefile "${SNAKEFILE}" \
    --configfile "${CONFIGFILE}" \
    --unlock 2>/dev/null || true

# ---------------------------------------------------------------------------
# Dry run first to validate DAG
# ---------------------------------------------------------------------------
echo "=== Dry run ==="
snakemake \
    --snakefile "${SNAKEFILE}" \
    --configfile "${CONFIGFILE}" \
    --workflow-profile "${PROFILE}" \
    -n

echo ""
echo "=== Dry run passed. Starting execution... ==="
echo ""

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
snakemake \
    --snakefile "${SNAKEFILE}" \
    --configfile "${CONFIGFILE}" \
    --workflow-profile "${PROFILE}" \
    --rerun-incomplete

echo ""
echo "=== DONE: run_snakemake.sh completed successfully ==="
