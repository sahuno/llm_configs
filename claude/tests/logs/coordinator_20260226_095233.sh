#!/usr/bin/env bash
#SBATCH --job-name=smk_coordinator
#SBATCH --partition=componc_cpu
#SBATCH --account=greenbab
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=4000
#SBATCH --time=08:00:00
#SBATCH --output=/data1/greenbab/users/ahunos/apps/llm_configs/claude/tests/logs/coordinator_20260226_095233.log
#SBATCH --error=/data1/greenbab/users/ahunos/apps/llm_configs/claude/tests/logs/coordinator_20260226_095233.log

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log_msg "=== Snakemake coordinator started ==="
log_msg "Host: $(hostname)"
log_msg "SLURM job: ${SLURM_JOBID}"

# Inject conda env into PATH (needed when SLURM_EXPORT_ENV=NONE strips environment)
export PATH="/home/ahunos/miniforge3/envs/snakemake/bin:${PATH}"
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
# Prevent srun conflict: SLURM_MEM_PER_NODE must not coexist with SLURM_MEM_PER_CPU in child jobs
unset SLURM_MEM_PER_NODE

log_msg "Working dir: /data1/greenbab/users/ahunos/apps/llm_configs/claude/tests"
log_msg "Snakemake:   /home/ahunos/miniforge3/envs/snakemake/bin/snakemake -- version: $(snakemake --version 2>&1)"

START_TIME=$(date +%s)

/home/ahunos/miniforge3/envs/snakemake/bin/snakemake -s /data1/greenbab/users/ahunos/apps/llm_configs/claude/tests/scripts/workflows/wf_snakemake/Snakefile --workflow-profile /data1/greenbab/users/ahunos/apps/llm_configs/claude/tests/scripts/workflows/wf_snakemake/profiles/slurm_fixed --directory /data1/greenbab/users/ahunos/apps/llm_configs/claude/tests --cores 1 --rerun-incomplete --forceall
EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
log_msg "Exit code: ${EXIT_CODE} | Wall time: ${ELAPSED}s"

if [[ ${EXIT_CODE} -eq 0 ]]; then
    log_msg "=== DONE: coordinator completed successfully ==="
else
    log_msg "=== FAILED: coordinator exited with code ${EXIT_CODE} ==="
    exit ${EXIT_CODE}
fi
