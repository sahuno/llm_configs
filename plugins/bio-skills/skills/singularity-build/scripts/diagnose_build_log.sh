#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-03-26
# Purpose: Diagnose a failed Apptainer fakeroot build from its log file
#
# Usage:
#   diagnose_build_log.sh <log_file>
#   diagnose_build_log.sh /home/ahunos/slurm_logs/build_tool_12345.out
#
# Output: Structured diagnosis with error, cause, and fix for each detected issue.
# Exit code: 0 if issues found and diagnosed, 1 if no log file, 2 if no issues detected.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: diagnose_build_log.sh <log_file> [stderr_file]" >&2
    exit 1
fi

LOG_FILE="$1"
ERR_FILE="${2:-}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "ERROR: Log file not found: ${LOG_FILE}" >&2
    exit 1
fi

ISSUES_FOUND=0

# ── Helper ──
diagnose() {
    local pattern="$1"
    local error_name="$2"
    local cause="$3"
    local fix="$4"

    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    echo "═══════════════════════════════════════════════════════"
    echo "ISSUE #${ISSUES_FOUND}: ${error_name}"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "  PATTERN MATCHED:"
    echo "    ${pattern}"
    echo ""
    echo "  CAUSE:"
    echo "    ${cause}"
    echo ""
    echo "  FIX:"
    echo "    ${fix}"
    echo ""
}

echo "Analyzing: ${LOG_FILE}"
if [[ -n "$ERR_FILE" && -f "$ERR_FILE" ]]; then
    echo "Stderr:    ${ERR_FILE}"
fi
echo ""

# Combine log and stderr for analysis
COMBINED=$(cat "$LOG_FILE" ${ERR_FILE:+"$ERR_FILE"} 2>/dev/null)

# ── Check for FATAL line and extract exit status ──
FATAL_LINE=$(echo "$COMBINED" | grep -o "exit status [0-9]*" | tail -1 || true)
if [[ -n "$FATAL_LINE" ]]; then
    EXIT_CODE=$(echo "$FATAL_LINE" | grep -o "[0-9]*$")
    echo "Build failed with ${FATAL_LINE}"
    echo ""

    # Show the 5 lines before FATAL for context
    echo "── Last lines before FATAL ──"
    echo "$COMBINED" | grep -B5 "^FATAL:" | head -10
    echo ""
fi

# ── Pattern: unused build args ──
if echo "$COMBINED" | grep -q "unused build args"; then
    UNUSED_ARGS=$(echo "$COMBINED" | grep "unused build args" | sed 's/.*unused build args: //' | sed 's/\..*//')
    diagnose \
        "unused build args: ${UNUSED_ARGS}" \
        "Unused build arguments" \
        "The build script passes --build-arg ${UNUSED_ARGS} but the .def file has no matching %arguments entry." \
        "Either add '${UNUSED_ARGS}' to the %arguments section of the .def file, or remove --build-arg \"${UNUSED_ARGS}=...\" from the build script."
fi

# ── Pattern: cannot create /dev/tty ──
if echo "$COMBINED" | grep -q "cannot create /dev/tty"; then
    diagnose \
        "cannot create /dev/tty: No such device or address" \
        "Installer requires TTY (terminal)" \
        "An installer (likely NVIDIA CUDA .run) is trying to open /dev/tty for interactive prompts. Inside fakeroot builds there is no TTY — the installer sends SIGTERM to itself." \
        "Do NOT use .run installers. Replace with conda package: 'mamba install -c nvidia cuda-toolkit=12.8'. If it's a different installer, find a non-interactive alternative (wget pre-built binary, conda package, etc.)."
fi

# ── Pattern: command 'gcc' failed ──
if echo "$COMBINED" | grep -q "command 'gcc' failed"; then
    # Sub-check: is it a missing gcc or a linker error?
    if echo "$COMBINED" | grep -q "cannot find.*libc"; then
        diagnose \
            "command 'gcc' failed + cannot find libc.so.6 / libc_nonshared.a" \
            "Linker cannot find system libc" \
            "The conda compiler_compat/ld linker expects libc at /lib64/libc.so.6 and /usr/lib64/libc_nonshared.a. Inside the fakeroot miniforge3 build, these standard system paths don't exist." \
            "Add sysroot libc symlinks in %post:
    SYSROOT=\"\${ENV_PREFIX}/x86_64-conda-linux-gnu/sysroot\"
    mkdir -p /lib64 /usr/lib64
    ln -sf \${SYSROOT}/lib64/libc.so.6 /lib64/libc.so.6
    ln -sf \${SYSROOT}/usr/lib64/libc_nonshared.a /usr/lib64/libc_nonshared.a
    ln -sf \${SYSROOT}/usr/lib64/libc.so /usr/lib64/libc.so"
    elif echo "$COMBINED" | grep -qi "gcc.*not found\|No such file"; then
        diagnose \
            "command 'gcc' failed — gcc not found" \
            "No C compiler available" \
            "The build requires gcc but it's not installed or not in PATH. Conda compilers are prefixed as x86_64-conda-linux-gnu-gcc." \
            "1. Add gcc_linux-64, gxx_linux-64, sysroot_linux-64 to conda packages.
  2. Create symlinks:
    ln -sf \${BIN}/x86_64-conda-linux-gnu-gcc \${BIN}/gcc
    ln -sf \${BIN}/x86_64-conda-linux-gnu-g++ \${BIN}/g++
    ln -sf \${BIN}/x86_64-conda-linux-gnu-cc \${BIN}/cc"
    else
        diagnose \
            "command 'gcc' failed with exit status 1" \
            "C compilation or linking failed" \
            "The gcc command was found but compilation/linking failed. Check the lines above for the specific error (missing headers, incompatible flags, etc.)." \
            "Read the full compiler output above the error line. Common sub-causes:
  - Missing header: install the -devel package via conda
  - Linker error with libc: add sysroot symlinks (see above)
  - Wrong gcc version: specify gcc_linux-64=13 for C++17/C++20 projects"
    fi
fi

# ── Pattern: CUDA not found ──
if echo "$COMBINED" | grep -q "Could NOT find CUDA\|missing: CUDA_INCLUDE_DIRS"; then
    diagnose \
        "Could NOT find CUDA (missing: CUDA_INCLUDE_DIRS)" \
        "Conda CUDA headers in non-standard location" \
        "Conda's cuda-toolkit installs headers to /opt/conda/targets/x86_64-linux/include/ instead of the standard /usr/local/cuda/include/. CMake's find_package(CUDAToolkit) finds it, but downstream cmake scripts (PyTorch/Caffe2/libtorch) use their own CUDA search which doesn't know about this path." \
        "1. Symlink CUDA headers and libs:
    CUDA_TARGET=\"/opt/conda/targets/x86_64-linux\"
    for f in \${CUDA_TARGET}/include/*.h \${CUDA_TARGET}/include/*.hpp; do
        [ -f \"\$f\" ] && ln -sf \"\$f\" /opt/conda/include/
    done
    for d in \${CUDA_TARGET}/include/*/; do
        [ -d \"\$d\" ] && ln -sfn \"\$d\" /opt/conda/include/
    done
    for f in \${CUDA_TARGET}/lib/*.so* \${CUDA_TARGET}/lib/*.a; do
        [ -f \"\$f\" ] && ln -sf \"\$f\" /opt/conda/lib/
    done

  2. Pass cmake hints:
    -DCUDAToolkit_ROOT=/opt/conda
    -DCUDA_INCLUDE_DIRS=/opt/conda/targets/x86_64-linux/include
    -DCMAKE_CUDA_COMPILER=/opt/conda/bin/nvcc"
fi

# ── Pattern: Permission denied writing log ──
if echo "$COMBINED" | grep -q "Permission denied.*\.log\|Permission denied.*build_"; then
    diagnose \
        "Permission denied writing log file" \
        "Build script running from SLURM spool directory" \
        "SLURM copies the script to /var/spool/slurmd/jobNNNNN/ before executing it. If the script derives paths from BASH_SOURCE[0] or \$0, it resolves to the spool dir which is not writable." \
        "Use an absolute PROJECT_DIR instead of SCRIPT_DIR:
  # WRONG:
  SCRIPT_DIR=\"\$(cd \"\$(dirname \"\${BASH_SOURCE[0]}\")\" && pwd)\"
  # CORRECT:
  PROJECT_DIR=\"/data1/greenbab/users/ahunos/path/to/project\""
fi

# ── Pattern: setgroups / apt-get failure ──
if echo "$COMBINED" | grep -qi "setgroups\|apt-get.*denied\|_apt.*permission"; then
    diagnose \
        "setgroups() / apt-get permission error" \
        "apt-get blocked in root-mapped namespace" \
        "apt-get internally drops to the _apt user via setgroups() — this syscall is blocked in root-mapped namespace (fakeroot without /etc/subuid entry)." \
        "Never use apt-get in fakeroot builds on this HPC. Use conda/mamba for all package management. Use condaforge/miniforge3 as the base image."
fi

# ── Pattern: Signal caught / SIGTERM (exit 15) ──
if echo "$COMBINED" | grep -q "Signal caught\|exit status 15"; then
    if ! echo "$COMBINED" | grep -q "cannot create /dev/tty"; then
        diagnose \
            "Signal caught / exit status 15 (SIGTERM)" \
            "Process killed itself or was killed" \
            "An installer or process received SIGTERM. This often happens when a .run installer can't access /dev/tty, or when a process exceeds memory limits." \
            "Check if:
  1. A .run installer was used (replace with conda package)
  2. The build ran out of memory (increase --mem in SLURM submission)
  3. SLURM killed the job for exceeding time limit (increase --time)"
    fi
fi

# ── Pattern: SIGPIPE (exit 141) ──
if echo "$COMBINED" | grep -q "exit status 141\|exit code.*141"; then
    diagnose \
        "Exit code 141 (SIGPIPE)" \
        "Piped command broke the pipe" \
        "A command like 'tool --version | head -1' causes SIGPIPE when head closes the pipe early. Under 'set -euo pipefail', this is treated as a fatal error even though the build itself may have succeeded." \
        "1. Check if the SIF file was actually created (it probably was).
  2. Add '|| true' after piped commands in the smoke test:
    apptainer exec container.sif tool --version 2>&1 | head -1 | tee -a \"\$LOG_FILE\" || true"
fi

# ── Pattern: nodev warning (harmless) ──
if echo "$COMBINED" | grep -q "'nodev' mount option set on /tmp"; then
    echo "NOTE: 'nodev mount option on /tmp' warning detected — this is HARMLESS."
    echo "  Normal on compute nodes. Does not prevent builds."
    echo ""
fi

# ── Pattern: fakeroot command not found (harmless) ──
if echo "$COMBINED" | grep -q "fakeroot command not found"; then
    echo "NOTE: 'fakeroot command not found' detected — this is EXPECTED."
    echo "  The --ignore-fakeroot-command flag deliberately skips the miniforge3 faked binary"
    echo "  (it's compiled against GLIBC >= 2.33, which crashes on RHEL 8's GLIBC 2.28)."
    echo ""
fi

# ── Summary ──
if [[ $ISSUES_FOUND -eq 0 ]]; then
    # Check if build actually succeeded
    if echo "$COMBINED" | grep -q "Build complete:"; then
        echo "No issues detected. Build appears to have SUCCEEDED."
        echo ""
        SIF_PATH=$(echo "$COMBINED" | grep "Build complete:" | sed 's/.*Build complete: //')
        if [[ -n "$SIF_PATH" ]]; then
            echo "SIF file: ${SIF_PATH}"
            if [[ -f "$SIF_PATH" ]]; then
                echo "Size: $(ls -lh "$SIF_PATH" | awk '{print $5}')"
            fi
        fi
    else
        echo "No known error patterns detected, but build may still have failed."
        echo "Review the last 20 lines of the log manually:"
        echo "  tail -20 ${LOG_FILE}"
    fi
    exit 2
else
    echo "───────────────────────────────────────────────────────"
    echo "Total issues diagnosed: ${ISSUES_FOUND}"
    echo "───────────────────────────────────────────────────────"
    exit 0
fi
