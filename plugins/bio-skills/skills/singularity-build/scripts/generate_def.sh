#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-03-26
# Purpose: Generate a .def file for Apptainer fakeroot builds on MSKCC HPC
#
# Usage:
#   generate_def.sh --name <tool> --version <ver> --tier <0|1|2|3> \
#     [--packages "pkg1=ver1 pkg2=ver2"] \
#     [--pip-packages "pkg1==ver1 pkg2==ver2"] \
#     [--python-version 3.6] \
#     [--env-name <conda_env_name>] \
#     [--cuda-version 12.8] \
#     [--git-repo <url>] \
#     [--git-branch <tag_or_branch>] \
#     [--cmake-args "<extra cmake flags>"] \
#     [--binary-url <download_url>] \
#     [--binary-install-dir /opt/toolname] \
#     [--source <source_url>] \
#     [--test-command "tool --version"] \
#     [--output <path>]
#
# Examples:
#   # Tier 1 — conda-installable
#   generate_def.sh --name samtools --version 1.21 --tier 1 --packages "samtools=1.21"
#
#   # Tier 2 — Python package with compiled extensions
#   generate_def.sh --name locusmasterte --version latest --tier 2 \
#     --python-version 3.6 --env-name locusmasterte \
#     --packages "cython=0.29.7 numpy=1.16.3 pandas=1.1.3 scipy=1.2.1 intervaltree=3.0.2 htslib samtools minimap2 subread" \
#     --pip-packages "pysam==0.15.2" \
#     --git-repo "https://github.com/jasonwong-lab/LocusMasterTE.git" \
#     --test-command "python3 -c 'import LocusMasterTE; print(\"OK\")'"
#
#   # Tier 3 — Full C++ with CUDA
#   generate_def.sh --name dorado --version v1.4.0 --tier 3 \
#     --cuda-version 12.8 \
#     --packages "cmake=3.30 make autoconf automake zlib openssl libxml2" \
#     --git-repo "https://github.com/nanoporetech/dorado.git" --git-branch v1.4.0 \
#     --cmake-args "-DDORADO_DISABLE_TESTS=ON"
#
#   # Tier 0 — Pre-built binary
#   generate_def.sh --name dorado --version 1.4.0 --tier 0 \
#     --binary-url "https://cdn.oxfordnanoportal.com/software/analysis/dorado-1.4.0-linux-x64.tar.gz" \
#     --binary-install-dir /opt/dorado

set -euo pipefail

# ── Defaults ──
NAME=""
VERSION=""
TIER=""
PACKAGES=""
PIP_PACKAGES=""
PYTHON_VERSION=""
ENV_NAME=""
CUDA_VERSION="12.8"
GIT_REPO=""
GIT_BRANCH=""
CMAKE_ARGS=""
BINARY_URL=""
BINARY_INSTALL_DIR=""
SOURCE_URL=""
TEST_COMMAND=""
OUTPUT=""
AUTHOR="Samuel Ahuno"
DATE="$(date '+%Y-%m-%d')"

# ── Parse arguments ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)           NAME="$2"; shift 2 ;;
        --version)        VERSION="$2"; shift 2 ;;
        --tier)           TIER="$2"; shift 2 ;;
        --packages)       PACKAGES="$2"; shift 2 ;;
        --pip-packages)   PIP_PACKAGES="$2"; shift 2 ;;
        --python-version) PYTHON_VERSION="$2"; shift 2 ;;
        --env-name)       ENV_NAME="$2"; shift 2 ;;
        --cuda-version)   CUDA_VERSION="$2"; shift 2 ;;
        --git-repo)       GIT_REPO="$2"; shift 2 ;;
        --git-branch)     GIT_BRANCH="$2"; shift 2 ;;
        --cmake-args)     CMAKE_ARGS="$2"; shift 2 ;;
        --binary-url)     BINARY_URL="$2"; shift 2 ;;
        --binary-install-dir) BINARY_INSTALL_DIR="$2"; shift 2 ;;
        --source)         SOURCE_URL="$2"; shift 2 ;;
        --test-command)   TEST_COMMAND="$2"; shift 2 ;;
        --output)         OUTPUT="$2"; shift 2 ;;
        --author)         AUTHOR="$2"; shift 2 ;;
        *) echo "ERROR: Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ── Validate ──
if [[ -z "$NAME" || -z "$VERSION" || -z "$TIER" ]]; then
    echo "ERROR: --name, --version, and --tier are required" >&2
    exit 1
fi

if [[ ! "$TIER" =~ ^[0123]$ ]]; then
    echo "ERROR: --tier must be 0, 1, 2, or 3" >&2
    exit 1
fi

# Default output path
if [[ -z "$OUTPUT" ]]; then
    OUTPUT="${NAME}.def"
fi

# Default test command
if [[ -z "$TEST_COMMAND" ]]; then
    TEST_COMMAND="${NAME} --version"
fi

# Default env name for tier 2 with python version
if [[ -n "$PYTHON_VERSION" && -z "$ENV_NAME" ]]; then
    ENV_NAME="${NAME}"
fi

# Default binary install dir for tier 0
if [[ "$TIER" == "0" && -z "$BINARY_INSTALL_DIR" ]]; then
    BINARY_INSTALL_DIR="/opt/${NAME}"
fi

# Source URL for labels
if [[ -z "$SOURCE_URL" && -n "$GIT_REPO" ]]; then
    SOURCE_URL="$GIT_REPO"
fi

# ── Generate ──
{
    # Header
    cat <<HEADER
Bootstrap: docker
From: condaforge/miniforge3:latest

%labels
    Author ${AUTHOR}
    Date ${DATE}
    Purpose ${NAME} container (Tier ${TIER} fakeroot build)
    Version ${VERSION}
HEADER

    if [[ -n "$SOURCE_URL" ]]; then
        echo "    Source ${SOURCE_URL}"
    fi

    # Arguments section (Tier 0 and 3 use build args)
    if [[ "$TIER" == "0" || "$TIER" == "3" ]]; then
        cat <<'ARGS_HEADER'

%arguments
ARGS_HEADER
        echo "    ${NAME^^}_VERSION=${VERSION}"
        if [[ "$TIER" == "3" ]]; then
            echo "    BUILD_THREADS=8"
        fi
    fi

    # %post section
    echo ""
    echo "%post"

    # Build args in post
    if [[ "$TIER" == "0" || "$TIER" == "3" ]]; then
        echo "    ${NAME^^}_VERSION={{ ${NAME^^}_VERSION }}"
        if [[ "$TIER" == "3" ]]; then
            echo "    BUILD_THREADS={{ BUILD_THREADS }}"
        fi
        echo ""
    fi

    # ── TIER 0: Pre-built binary ──
    if [[ "$TIER" == "0" ]]; then
        cat <<TIER0
    # ── Download pre-built binary ──
    mamba install -y -c conda-forge wget
    mamba clean --all --yes

    mkdir -p ${BINARY_INSTALL_DIR}
    wget -q "${BINARY_URL}" -O /tmp/${NAME}_download.tar.gz
    tar -xzf /tmp/${NAME}_download.tar.gz -C ${BINARY_INSTALL_DIR} --strip-components=1
    rm -f /tmp/${NAME}_download.tar.gz

    ls -la ${BINARY_INSTALL_DIR}/bin/${NAME}

    # Do NOT rm -rf /tmp/* — under fakeroot, /tmp is host bind mount
TIER0
    fi

    # ── TIER 1: Conda-installable ──
    if [[ "$TIER" == "1" ]]; then
        echo "    # ── Install via mamba ──"
        echo -n "    mamba install -y -c conda-forge -c bioconda"
        for pkg in $PACKAGES; do
            echo " \\"
            echo -n "        ${pkg}"
        done
        echo ""
        cat <<'TIER1_CLEAN'
    mamba clean --all --yes

    # Do NOT rm -rf /tmp/* — under fakeroot, /tmp is host bind mount
TIER1_CLEAN
    fi

    # ── TIER 2: Python/R with compiled extensions ──
    if [[ "$TIER" == "2" ]]; then
        if [[ -n "$ENV_NAME" ]]; then
            echo "    # ── Create conda environment with pinned dependencies ──"
            echo -n "    mamba create -y -n ${ENV_NAME} \\"
            echo ""
            echo "        -c conda-forge -c bioconda \\"
            if [[ -n "$PYTHON_VERSION" ]]; then
                echo "        python=${PYTHON_VERSION} \\"
            fi
            for pkg in $PACKAGES; do
                echo "        ${pkg} \\"
            done
            echo "        git \\"
            echo "        pip \\"
            echo "        gcc_linux-64 \\"
            echo "        gxx_linux-64 \\"
            echo "        sysroot_linux-64"
        else
            echo "    # ── Install dependencies ──"
            echo -n "    mamba install -y -c conda-forge -c bioconda"
            for pkg in $PACKAGES; do
                echo " \\"
                echo -n "        ${pkg}"
            done
            echo " \\"
            echo "        gcc_linux-64 gxx_linux-64 sysroot_linux-64"
        fi

        echo ""
        if [[ -n "$ENV_NAME" ]]; then
            cat <<TIER2_ACTIVATE
    # ── Activate environment ──
    . /opt/conda/etc/profile.d/conda.sh
    conda activate ${ENV_NAME}

TIER2_ACTIVATE
            SYMLINK_BIN="/opt/conda/envs/${ENV_NAME}/bin"
            SYMLINK_PREFIX="/opt/conda/envs/${ENV_NAME}"
        else
            SYMLINK_BIN="/opt/conda/bin"
            SYMLINK_PREFIX="/opt/conda"
        fi

        cat <<TIER2_COMPILER
    # ── Symlink conda compilers to standard names ──
    ENV_BIN="${SYMLINK_BIN}"
    ENV_PREFIX="${SYMLINK_PREFIX}"
    ln -sf \${ENV_BIN}/x86_64-conda-linux-gnu-gcc \${ENV_BIN}/gcc
    ln -sf \${ENV_BIN}/x86_64-conda-linux-gnu-g++ \${ENV_BIN}/g++
    ln -sf \${ENV_BIN}/x86_64-conda-linux-gnu-cc \${ENV_BIN}/cc
    ln -sf \${ENV_BIN}/x86_64-conda-linux-gnu-ar \${ENV_BIN}/ar
    ln -sf \${ENV_BIN}/x86_64-conda-linux-gnu-ranlib \${ENV_BIN}/ranlib

    # ── Symlink sysroot libc for the linker ──
    SYSROOT="\${ENV_PREFIX}/x86_64-conda-linux-gnu/sysroot"
    mkdir -p /lib64 /usr/lib64
    ln -sf \${SYSROOT}/lib64/libc.so.6 /lib64/libc.so.6
    ln -sf \${SYSROOT}/lib64/libc-*.so /lib64/ 2>/dev/null || true
    ln -sf \${SYSROOT}/usr/lib64/libc_nonshared.a /usr/lib64/libc_nonshared.a
    ln -sf \${SYSROOT}/usr/lib64/libc.so /usr/lib64/libc.so 2>/dev/null || true

    gcc --version
TIER2_COMPILER

        # pip packages
        if [[ -n "$PIP_PACKAGES" ]]; then
            echo ""
            for pkg in $PIP_PACKAGES; do
                echo "    pip install ${pkg}"
            done
        fi

        # git clone and install
        if [[ -n "$GIT_REPO" ]]; then
            local_branch=""
            if [[ -n "$GIT_BRANCH" ]]; then
                local_branch="--branch ${GIT_BRANCH} "
            fi
            cat <<TIER2_GIT

    # ── Clone and install ──
    cd /opt
    git clone ${local_branch}${GIT_REPO}
    cd ${NAME}*
    python3 setup.py build
    python3 setup.py install
TIER2_GIT
        fi

        cat <<'TIER2_CLEAN'

    # ── Cleanup ──
    mamba clean --all --yes
    pip cache purge 2>/dev/null || true

    # Do NOT rm -rf /tmp/* — under fakeroot, /tmp is host bind mount
TIER2_CLEAN
    fi

    # ── TIER 3: Full C/C++ compilation with CUDA ──
    if [[ "$TIER" == "3" ]]; then
        cat <<TIER3_INSTALL
    # ── Install CUDA toolkit + build dependencies via mamba ──
    mamba install -y -c conda-forge -c nvidia \\
        cuda-toolkit=${CUDA_VERSION} \\
        gcc_linux-64=13 \\
        gxx_linux-64=13 \\
TIER3_INSTALL
        for pkg in $PACKAGES; do
            echo "        ${pkg} \\"
        done
        cat <<'TIER3_DEPS'
        git \
        ca-certificates
    mamba clean --all --yes

    # ── Symlink conda compilers to standard names ──
    CONDA_BIN="/opt/conda/bin"
    ln -sf ${CONDA_BIN}/x86_64-conda-linux-gnu-gcc ${CONDA_BIN}/gcc
    ln -sf ${CONDA_BIN}/x86_64-conda-linux-gnu-g++ ${CONDA_BIN}/g++
    ln -sf ${CONDA_BIN}/x86_64-conda-linux-gnu-cc ${CONDA_BIN}/cc
    ln -sf ${CONDA_BIN}/x86_64-conda-linux-gnu-ar ${CONDA_BIN}/ar
    ln -sf ${CONDA_BIN}/x86_64-conda-linux-gnu-ranlib ${CONDA_BIN}/ranlib

    gcc --version
    nvcc --version

    # ── Symlink CUDA headers/libs to where downstream cmake expects them ──
    CUDA_DIR="/opt/conda"
    CUDA_TARGET="/opt/conda/targets/x86_64-linux"
    export PATH="${CUDA_DIR}/bin:${PATH}"
    export LD_LIBRARY_PATH="${CUDA_TARGET}/lib:${CUDA_DIR}/lib:${LD_LIBRARY_PATH:-}"
    export CUDA_HOME="${CUDA_DIR}"
    export CUDA_PATH="${CUDA_DIR}"
    export CUDA_INCLUDE_DIRS="${CUDA_TARGET}/include"
    export CUDA_TOOLKIT_ROOT_DIR="${CUDA_DIR}"

    for f in ${CUDA_TARGET}/include/*.h ${CUDA_TARGET}/include/*.hpp; do
        [ -f "$f" ] && ln -sf "$f" ${CUDA_DIR}/include/ 2>/dev/null || true
    done
    for d in ${CUDA_TARGET}/include/*/; do
        [ -d "$d" ] && ln -sfn "$d" ${CUDA_DIR}/include/ 2>/dev/null || true
    done
    for f in ${CUDA_TARGET}/lib/*.so* ${CUDA_TARGET}/lib/*.a; do
        [ -f "$f" ] && ln -sf "$f" ${CUDA_DIR}/lib/ 2>/dev/null || true
    done
TIER3_DEPS

        # git clone
        if [[ -n "$GIT_REPO" ]]; then
            local_branch_flag=""
            if [[ -n "$GIT_BRANCH" ]]; then
                local_branch_flag="--branch ${GIT_BRANCH} "
            fi
            cat <<TIER3_BUILD

    # ── Clone and build from source ──
    cd /opt
    git clone ${local_branch_flag}--depth 1 --recurse-submodules \\
        ${GIT_REPO} ${NAME}-src
    cd ${NAME}-src

    cmake \\
        -DCUDAToolkit_ROOT=\${CUDA_DIR} \\
        -DCUDA_TOOLKIT_ROOT_DIR=\${CUDA_DIR} \\
        -DCUDA_INCLUDE_DIRS=\${CUDA_TARGET}/include \\
        -DCMAKE_CUDA_COMPILER=\${CUDA_DIR}/bin/nvcc \\
        -DCMAKE_BUILD_TYPE=Release \\
        -DCMAKE_INSTALL_PREFIX=/opt/${NAME} \\
TIER3_BUILD
            if [[ -n "$CMAKE_ARGS" ]]; then
                for arg in $CMAKE_ARGS; do
                    echo "        ${arg} \\"
                done
            fi
            cat <<TIER3_BUILD2
        -S . -B cmake-build

    cmake --build cmake-build --config Release -j \${BUILD_THREADS}
    cmake --install cmake-build --prefix /opt/${NAME}

    ls -la /opt/${NAME}/bin/${NAME}

    # ── Cleanup build artifacts ──
    rm -rf /opt/${NAME}-src
TIER3_BUILD2
        fi

        cat <<'TIER3_CLEAN'

    # Do NOT rm -rf /tmp/* — under fakeroot, /tmp is host bind mount
TIER3_CLEAN
    fi

    # ── %environment ──
    echo ""
    echo "%environment"
    if [[ "$TIER" == "0" ]]; then
        echo "    export PATH=\"${BINARY_INSTALL_DIR}/bin:\$PATH\""
    elif [[ "$TIER" == "1" ]]; then
        echo "    export PATH=\"/opt/conda/bin:\$PATH\""
    elif [[ "$TIER" == "2" && -n "$ENV_NAME" ]]; then
        cat <<ENV2
    export PATH="/opt/conda/envs/${ENV_NAME}/bin:\$PATH"
    export CONDA_DEFAULT_ENV="${ENV_NAME}"
    export CONDA_PREFIX="/opt/conda/envs/${ENV_NAME}"
ENV2
    elif [[ "$TIER" == "2" ]]; then
        echo "    export PATH=\"/opt/conda/bin:\$PATH\""
    elif [[ "$TIER" == "3" ]]; then
        echo "    export PATH=\"/opt/${NAME}/bin:/opt/conda/bin:\$PATH\""
        echo "    export LD_LIBRARY_PATH=\"/opt/conda/lib:/opt/${NAME}/lib:\${LD_LIBRARY_PATH:-}\""
    fi

    # ── %runscript ──
    echo ""
    echo "%runscript"
    echo "    exec ${NAME} \"\$@\""

    # ── %test ──
    echo ""
    echo "%test"
    if [[ "$TIER" == "2" && -n "$ENV_NAME" ]]; then
        echo "    export PATH=\"/opt/conda/envs/${ENV_NAME}/bin:\$PATH\""
    fi
    if [[ "$TIER" == "3" ]]; then
        echo "    ${TEST_COMMAND} || echo \"NOTE: ${NAME} may require GPU; binary presence verified during build\""
    else
        echo "    ${TEST_COMMAND}"
    fi

} > "$OUTPUT"

echo "Generated: ${OUTPUT} (Tier ${TIER})"
