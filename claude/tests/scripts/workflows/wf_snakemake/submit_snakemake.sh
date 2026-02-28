#!/usr/bin/env bash
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: 2026-02-26
# Purpose: Submit the Snakemake coordinator itself as a SLURM job so it never runs as a
#          blocking foreground process (required for Claude Code and robust production use).
#
# Usage:
#   bash submit_snakemake.sh [--cores N] [--extra-args "..."] [--dry-run]
#
# Monitoring after submission:
#   squeue -j <JOBID>
#   tail -f logs/coordinator_<TIMESTAMP>.log
#   sacct -j <JOBID> --format=State,ExitCode

set -euo pipefail

# ── Paths (all absolute) ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAKEFILE="${SCRIPT_DIR}/Snakefile"
PROFILE_DIR="${SCRIPT_DIR}/profiles/slurm_fixed"
EXPERIMENT_DIR="/data1/greenbab/users/ahunos/apps/llm_configs/claude/tests"
LOG_DIR="${EXPERIMENT_DIR}/logs"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

# ── Parse arguments ──────────────────────────────────────────────────────────────────────
CORES=1
EXTRA_ARGS=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cores)      CORES="$2"; shift 2 ;;
        --extra-args) EXTRA_ARGS="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=true; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Logging setup ────────────────────────────────────────────────────────────────────────
mkdir -p "${LOG_DIR}"
SUBMIT_LOG="${LOG_DIR}/submit_snakemake_${TIMESTAMP}.log"
exec > >(tee -a "${SUBMIT_LOG}") 2>&1

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log_msg "=== Snakemake SLURM submission wrapper ==="
log_msg "Snakefile:      ${SNAKEFILE}"
log_msg "Profile dir:    ${PROFILE_DIR}"
log_msg "Experiment dir: ${EXPERIMENT_DIR}"
log_msg "Cores:          ${CORES}"
log_msg "Dry-run mode:   ${DRY_RUN}"
log_msg "Submit log:     ${SUBMIT_LOG}"

# ── Validate paths ───────────────────────────────────────────────────────────────────────
[[ -f "${SNAKEFILE}" ]]      || { log_msg "ERROR: Snakefile not found: ${SNAKEFILE}"; exit 1; }
[[ -d "${PROFILE_DIR}" ]]    || { log_msg "ERROR: Profile dir not found: ${PROFILE_DIR}"; exit 1; }
[[ -d "${EXPERIMENT_DIR}" ]] || { log_msg "ERROR: Experiment dir not found: ${EXPERIMENT_DIR}"; exit 1; }

# ── Check for stale locks ────────────────────────────────────────────────────────────────
LOCK_DIR="${EXPERIMENT_DIR}/.snakemake/locks"
if [[ -d "${LOCK_DIR}" ]] && [[ -n "$(ls -A "${LOCK_DIR}" 2>/dev/null)" ]]; then
    log_msg "WARNING: Stale lock files detected in ${LOCK_DIR}"
    log_msg "Run this to unlock before submitting:"
    log_msg "  bash ${SCRIPT_DIR}/unlock_and_status.sh"
    exit 1
fi

# ── Resolve snakemake binary ─────────────────────────────────────────────────────────────
SNAKEMAKE_BIN="$(which snakemake)"
CONDA_ENV_BIN="$(dirname "${SNAKEMAKE_BIN}")"
log_msg "Snakemake binary: ${SNAKEMAKE_BIN}"
log_msg "Conda env bin:    ${CONDA_ENV_BIN}"

# ── Build the snakemake command string ───────────────────────────────────────────────────
SNAKEMAKE_CMD="${SNAKEMAKE_BIN} -s ${SNAKEFILE} --workflow-profile ${PROFILE_DIR} --directory ${EXPERIMENT_DIR} --cores ${CORES} --rerun-incomplete"
if [[ -n "${EXTRA_ARGS}" ]]; then
    SNAKEMAKE_CMD="${SNAKEMAKE_CMD} ${EXTRA_ARGS}"
fi
if [[ "${DRY_RUN}" == "true" ]]; then
    SNAKEMAKE_CMD="${SNAKEMAKE_CMD} --dry-run"
fi

log_msg "Snakemake command: ${SNAKEMAKE_CMD}"

# ── Write coordinator sbatch script (use quoted heredoc — no variable expansion inside) ──
COORDINATOR_SCRIPT="${LOG_DIR}/coordinator_${TIMESTAMP}.sh"
COORDINATOR_LOG="${LOG_DIR}/coordinator_${TIMESTAMP}.log"

# Write static template first (quoted << 'EOF' = no expansion), then append dynamic parts
cat > "${COORDINATOR_SCRIPT}" << 'STATIC_HEADER'
#!/usr/bin/env bash
#SBATCH --job-name=smk_coordinator
#SBATCH --partition=componc_cpu
#SBATCH --account=greenbab
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=4000
#SBATCH --time=08:00:00

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log_msg "=== Snakemake coordinator started ==="
log_msg "Host: $(hostname)"
log_msg "SLURM job: ${SLURM_JOBID}"
STATIC_HEADER

# Append dynamic parts (values known at submit time)
cat >> "${COORDINATOR_SCRIPT}" << DYNAMIC
#SBATCH --output=${COORDINATOR_LOG}
#SBATCH --error=${COORDINATOR_LOG}

# Inject conda env into PATH (needed when SLURM_EXPORT_ENV=NONE strips environment)
export PATH="${CONDA_ENV_BIN}:\${PATH}"
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
# Prevent srun conflict: SLURM_MEM_PER_NODE must not coexist with SLURM_MEM_PER_CPU in child jobs
unset SLURM_MEM_PER_NODE

log_msg "Working dir: ${EXPERIMENT_DIR}"
log_msg "Snakemake:   ${SNAKEMAKE_BIN} -- version: \$(snakemake --version 2>&1)"

START_TIME=\$(date +%s)

${SNAKEMAKE_CMD}
EXIT_CODE=\$?

END_TIME=\$(date +%s)
ELAPSED=\$(( END_TIME - START_TIME ))
log_msg "Exit code: \${EXIT_CODE} | Wall time: \${ELAPSED}s"

if [[ \${EXIT_CODE} -eq 0 ]]; then
    log_msg "=== DONE: coordinator completed successfully ==="
else
    log_msg "=== FAILED: coordinator exited with code \${EXIT_CODE} ==="
    exit \${EXIT_CODE}
fi
DYNAMIC

# Fix: #SBATCH directives must be at the top — move the output/error lines up
# (sed swap: move the two #SBATCH output lines to after line 2)
FIXED_SCRIPT="${LOG_DIR}/coordinator_${TIMESTAMP}_fixed.sh"
{
    head -1 "${COORDINATOR_SCRIPT}"           # #!/usr/bin/env bash
    grep '^#SBATCH' "${COORDINATOR_SCRIPT}"   # all #SBATCH lines together
    grep -v '^#SBATCH' "${COORDINATOR_SCRIPT}" | tail -n +2  # rest (no shebang, no #SBATCH)
} > "${FIXED_SCRIPT}"
mv "${FIXED_SCRIPT}" "${COORDINATOR_SCRIPT}"
chmod +x "${COORDINATOR_SCRIPT}"

log_msg "Coordinator script written: ${COORDINATOR_SCRIPT}"

# ── Submit or show dry-run ───────────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" == "true" ]]; then
    log_msg "DRY RUN — coordinator script contents:"
    cat "${COORDINATOR_SCRIPT}"
    log_msg "Would submit with: sbatch ${COORDINATOR_SCRIPT}"
    log_msg "=== DONE: submit_snakemake.sh (dry-run) completed successfully ==="
    exit 0
fi

JOBID="$(sbatch "${COORDINATOR_SCRIPT}" | awk '{print $NF}')"
log_msg "Submitted coordinator as SLURM job: ${JOBID}"
log_msg ""
log_msg "Monitor:"
log_msg "  squeue -j ${JOBID}"
log_msg "  tail -f ${COORDINATOR_LOG}"
log_msg "  sacct -j ${JOBID} --format=State,ExitCode"
log_msg "=== DONE: submit_snakemake.sh completed successfully ==="
