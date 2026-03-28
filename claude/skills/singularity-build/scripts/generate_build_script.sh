#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-03-26
# Purpose: Generate a SLURM-safe Apptainer build script
#
# Usage:
#   generate_build_script.sh --name <tool> --version <ver> --tier <0|1|2|3> \
#     --project-dir <absolute_path> \
#     [--def-file <name.def>] \
#     [--sif-file <name_vX.Y.Z.sif>] \
#     [--build-args "KEY1=VAL1 KEY2=VAL2"] \
#     [--gpu] \
#     [--output <path>]
#
# Examples:
#   generate_build_script.sh --name samtools --version 1.21 --tier 1 \
#     --project-dir /data1/greenbab/users/ahunos/project
#
#   generate_build_script.sh --name dorado --version v1.4.0 --tier 3 \
#     --project-dir /data1/greenbab/users/ahunos/project \
#     --build-args "DORADO_VERSION=v1.4.0 BUILD_THREADS=8" --gpu

set -euo pipefail

# ── Defaults ──
NAME=""
VERSION=""
TIER=""
PROJECT_DIR=""
DEF_FILE=""
SIF_FILE=""
BUILD_ARGS=""
GPU=false
OUTPUT=""

# ── Parse arguments ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)        NAME="$2"; shift 2 ;;
        --version)     VERSION="$2"; shift 2 ;;
        --tier)        TIER="$2"; shift 2 ;;
        --project-dir) PROJECT_DIR="$2"; shift 2 ;;
        --def-file)    DEF_FILE="$2"; shift 2 ;;
        --sif-file)    SIF_FILE="$2"; shift 2 ;;
        --build-args)  BUILD_ARGS="$2"; shift 2 ;;
        --gpu)         GPU=true; shift ;;
        --output)      OUTPUT="$2"; shift 2 ;;
        *) echo "ERROR: Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ── Validate ──
if [[ -z "$NAME" || -z "$VERSION" || -z "$TIER" || -z "$PROJECT_DIR" ]]; then
    echo "ERROR: --name, --version, --tier, and --project-dir are required" >&2
    exit 1
fi

# Ensure project-dir is absolute
if [[ "$PROJECT_DIR" != /* ]]; then
    echo "ERROR: --project-dir must be an absolute path (got: ${PROJECT_DIR})" >&2
    echo "  SLURM copies scripts to /var/spool/slurmd/ — relative paths will break" >&2
    exit 1
fi

# Defaults
if [[ -z "$DEF_FILE" ]]; then
    DEF_FILE="${NAME}.def"
fi
if [[ -z "$SIF_FILE" ]]; then
    SIF_FILE="${NAME}_v${VERSION}.sif"
fi
if [[ -z "$OUTPUT" ]]; then
    OUTPUT="build_${NAME}.sh"
fi

# SLURM resources by tier
case "$TIER" in
    0) CPUS=2;  MEM="8G";  TIME="00:15:00" ;;
    1) CPUS=2;  MEM="8G";  TIME="00:15:00" ;;
    2) CPUS=4;  MEM="16G"; TIME="00:30:00" ;;
    3) CPUS=8;  MEM="64G"; TIME="04:00:00" ;;
    *) echo "ERROR: --tier must be 0, 1, 2, or 3" >&2; exit 1 ;;
esac

# Build the --build-arg flags
BUILD_ARG_FLAGS=""
if [[ -n "$BUILD_ARGS" ]]; then
    for arg in $BUILD_ARGS; do
        BUILD_ARG_FLAGS="${BUILD_ARG_FLAGS}    --build-arg \"${arg}\" \\
"
    done
fi

# Smoke test command
if [[ "$GPU" == true ]]; then
    SMOKE_EXEC="apptainer exec --nv \"\${SIF_FILE}\" ${NAME} --version 2>&1 | tee -a \"\$LOG_FILE\" || true"
else
    SMOKE_EXEC="apptainer exec \"\${SIF_FILE}\" ${NAME} --version 2>&1 | tee -a \"\$LOG_FILE\" || true"
fi

# ── Generate ──
cat > "$OUTPUT" <<SCRIPT
#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: $(date '+%Y-%m-%d')
# Purpose: Build ${NAME} v${VERSION} Apptainer container using --fakeroot
# Tier: ${TIER} | SLURM: ${CPUS} CPUs, ${MEM} memory, ${TIME} time limit

set -euo pipefail

# ── Absolute paths — NEVER use SCRIPT_DIR from BASH_SOURCE[0] ──
# SLURM copies scripts to /var/spool/slurmd/ which breaks relative paths
PROJECT_DIR="${PROJECT_DIR}"
DEF_FILE="\${PROJECT_DIR}/${DEF_FILE}"
SIF_FILE="\${PROJECT_DIR}/${SIF_FILE}"
LOG_FILE="\${PROJECT_DIR}/build_${NAME}_\$(date '+%Y%m%d_%H%M%S').log"

# ── Prevent host bind vars from leaking into %post ──
unset APPTAINER_BIND SINGULARITY_BIND 2>/dev/null || true

# ── Set cache dir to avoid home quota issues on compute nodes ──
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
mkdir -p "\${APPTAINER_CACHEDIR}"

echo "=== Building ${NAME} v${VERSION} container (Tier ${TIER}) ===" | tee "\$LOG_FILE"
echo "DEF:  \${DEF_FILE}" | tee -a "\$LOG_FILE"
echo "SIF:  \${SIF_FILE}" | tee -a "\$LOG_FILE"
echo "Start: \$(date)" | tee -a "\$LOG_FILE"

# ── Build ──
# --fakeroot: required (no sudo)
# --ignore-fakeroot-command: required for miniforge3 base on RHEL 8 (GLIBC 2.28 vs 2.33)
apptainer build --fakeroot --ignore-fakeroot-command \\
${BUILD_ARG_FLAGS}    "\${SIF_FILE}" \\
    "\${DEF_FILE}" \\
    2>&1 | tee -a "\$LOG_FILE"

echo "" | tee -a "\$LOG_FILE"
echo "=== Build finished: \$(date) ===" | tee -a "\$LOG_FILE"

# ── Smoke test ──
# Guard piped commands with || true to prevent SIGPIPE (exit 141) under pipefail
if [[ -f "\${SIF_FILE}" ]]; then
    echo "=== Smoke test ===" | tee -a "\$LOG_FILE"
    ${SMOKE_EXEC}
    echo "=== DONE: build_${NAME}.sh completed successfully ===" | tee -a "\$LOG_FILE"
else
    echo "ERROR: SIF file not created" | tee -a "\$LOG_FILE"
    exit 1
fi
SCRIPT

chmod +x "$OUTPUT"

echo "Generated: ${OUTPUT}"
echo "  SLURM recommendation: ${CPUS} CPUs, ${MEM} memory, ${TIME} time limit"
echo "  Submit with: sbatch --cpus-per-task=${CPUS} --mem=${MEM} --time=${TIME} ${OUTPUT}"
