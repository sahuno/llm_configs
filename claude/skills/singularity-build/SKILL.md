---
name: singularity-build
description: |
  Expert Singularity/Apptainer container builder for bioinformatics tools on
  MSKCC HPC (RHEL 8, no sudo). Builds containers using --fakeroot with
  root-mapped namespace, conda-based package management (never apt-get), and
  SLURM-safe build scripts. Use this skill proactively whenever the user asks to:
  create/build a Singularity or Apptainer container, write a .def definition file,
  containerize a bioinformatics tool or software package, build a SIF image,
  troubleshoot a failed container build (exit status 1/15/141/255), fix a
  "command gcc failed" or "cannot find libc" or "CUDA_INCLUDE_DIRS" error in a
  container build, or package any software into a reproducible container image.
  Also trigger when the user mentions: .def file, .sif file, apptainer build,
  singularity build, fakeroot build, container for dorado/samtools/modkit or
  any bioinformatics tool, or asks to install software that requires root.
  Do NOT trigger for: running an existing container (apptainer exec/run),
  pulling pre-built images (apptainer pull), or Docker/Podman workflows.
version: 1.0.0
author: Samuel Ahuno (ekwame001@gmail.com)
---

# Singularity/Apptainer Fakeroot Container Build Skill

Build reproducible Apptainer/Singularity containers on MSKCC HPC without sudo,
using --fakeroot with root-mapped namespace and conda-based package management.

For the full reference guide with all numbered rules, read:
`references/build_guide.md` (in this skill's directory).

## Bundled Scripts

This skill includes three scripts in `scripts/` that handle the mechanical, error-prone
parts of container building. Use them instead of generating boilerplate from scratch —
they encode every lesson learned from real build failures on this HPC.

### `scripts/generate_def.sh`
Generates a complete `.def` file for any tier. Handles all compiler symlinks, sysroot
libc symlinks, CUDA header symlinks, conda environment activation, and cleanup.

```bash
# Tier 1 — conda-installable
scripts/generate_def.sh --name samtools --version 1.21 --tier 1 \
  --packages "samtools=1.21"

# Tier 2 — Python with compiled extensions
scripts/generate_def.sh --name locusmasterte --version latest --tier 2 \
  --python-version 3.6 --env-name locusmasterte \
  --packages "cython=0.29.7 numpy=1.16.3 htslib samtools" \
  --pip-packages "pysam==0.15.2" \
  --git-repo "https://github.com/jasonwong-lab/LocusMasterTE.git"

# Tier 3 — Full C++ with CUDA
scripts/generate_def.sh --name dorado --version v1.4.0 --tier 3 \
  --packages "cmake=3.30 make zlib openssl" \
  --git-repo "https://github.com/nanoporetech/dorado.git" --git-branch v1.4.0 \
  --cmake-args "-DDORADO_DISABLE_TESTS=ON"

# Tier 0 — Pre-built binary
scripts/generate_def.sh --name dorado --version 1.4.0 --tier 0 \
  --binary-url "https://cdn.oxfordnanoportal.com/software/analysis/dorado-1.4.0-linux-x64.tar.gz"
```

### `scripts/generate_build_script.sh`
Generates a SLURM-safe build script with absolute `PROJECT_DIR` (never `SCRIPT_DIR`),
`unset APPTAINER_BIND`, `APPTAINER_CACHEDIR`, `--ignore-fakeroot-command`, `|| true`
guarded smoke tests, and tier-appropriate SLURM resource recommendations.

```bash
scripts/generate_build_script.sh --name samtools --version 1.21 --tier 1 \
  --project-dir /data1/greenbab/users/ahunos/project

scripts/generate_build_script.sh --name dorado --version v1.4.0 --tier 3 \
  --project-dir /data1/greenbab/users/ahunos/project \
  --build-args "DORADO_VERSION=v1.4.0 BUILD_THREADS=8" --gpu
```

### `scripts/diagnose_build_log.sh`
Diagnoses a failed build by grepping for known error patterns and outputting structured
cause + fix for each issue found. Run this first when a build fails.

```bash
scripts/diagnose_build_log.sh /home/ahunos/slurm_logs/build_tool_12345.out
scripts/diagnose_build_log.sh build.log stderr.log   # can also pass stderr file
```

Detected patterns: unused build-args, /dev/tty errors, gcc failures (missing compiler vs
missing libc), CUDA_INCLUDE_DIRS, permission denied (SLURM spool), apt-get/setgroups,
SIGTERM (exit 15), SIGPIPE (exit 141). Also flags harmless warnings (nodev, fakeroot
command not found).

## When to Use This Skill

**Use when** the user needs to:
- Create a .def file for any bioinformatics tool
- Build a .sif container image
- Containerize software that normally needs root to install
- Troubleshoot a failed apptainer/singularity build
- Package a GitHub tool into a reproducible container

**Do NOT use for**: running existing containers, Docker workflows, or pulling images.

## Build Environment Constraints

This HPC has specific constraints that shape every decision:

- **No sudo, no true fakeroot.** User is not in `/etc/subuid`. Apptainer uses root-mapped namespace — a limited unprivileged mode.
- **RHEL 8, GLIBC 2.28, kernel 4.18.** Many modern images assume newer GLIBC.
- **`apt-get` is blocked** — `setgroups()` syscall fails in root-mapped namespace.
- **NVIDIA `.run` installers are blocked** — they require `/dev/tty` which doesn't exist in fakeroot.
- **`/tmp` is a host bind mount** in fakeroot — `rm -rf /tmp/*` destroys host files.

These constraints mean: always use `condaforge/miniforge3` as the base image, install
everything via `mamba`, and never touch `/tmp` broadly.

## Step 1: Classify the Build Tier

Every containerization request falls into one of four tiers. Classify first, then
follow the tier-specific recipe.

### Tier 0 — Pre-built binary
The tool distributes pre-compiled binaries (tarball, zip) that just need to be extracted.
Examples: dorado from ONT CDN, IGV, commercial tools.

**Recipe:**
- Install `wget` via mamba
- Download and extract to `/opt/toolname`
- No compilers needed
- SLURM: 2 CPUs, 8G, 15 min

### Tier 1 — Conda-installable
The tool exists as a package in conda-forge or bioconda.
Examples: samtools, minimap2, bedtools, STAR, modkit.

**Recipe:**
- `mamba install -y -c conda-forge -c bioconda tool=version`
- Simplest possible .def file
- SLURM: 2 CPUs, 8G, 15 min

### Tier 2 — Python/R package with compiled extensions
The tool has a `setup.py` or C/Cython extensions that need compilation.
Examples: LocusMasterTE, Telescope, pysam from source.

**Recipe (everything from Tier 1 plus):**
- Add `gcc_linux-64`, `gxx_linux-64`, `sysroot_linux-64` to conda packages
- Symlink compilers: `x86_64-conda-linux-gnu-gcc` -> `gcc`, `g++`, `cc`
- Symlink sysroot libc to `/lib64/` and `/usr/lib64/` (the linker needs these)
- If specific Python version required, use `mamba create -n envname python=X.Y`
- SLURM: 4 CPUs, 16G, 30 min

### Tier 3 — Full C/C++ compilation with CUDA
The tool must be compiled from source and needs CUDA.
Examples: dorado from source, Clair3 with GPU, custom CUDA tools.

**Recipe (everything from Tier 2 plus):**
- `mamba install -c nvidia cuda-toolkit=12.8`
- Symlink CUDA headers/libs from `/opt/conda/targets/x86_64-linux/` to `/opt/conda/include/` and `/opt/conda/lib/`
- Set `CUDA_HOME`, `CUDA_PATH`, `CUDA_INCLUDE_DIRS`, `CUDA_TOOLKIT_ROOT_DIR`
- Pass explicit cmake CUDA hints: `-DCUDAToolkit_ROOT`, `-DCUDA_INCLUDE_DIRS`, `-DCMAKE_CUDA_COMPILER`
- Remove source after install to reduce image size
- SLURM: 8 CPUs, 64G, 4 hours

## Step 2: Generate the .def File

Every .def file follows this structure. Sections marked (required) are never omitted.

```
Bootstrap: docker
From: condaforge/miniforge3:latest

%labels                    (required)
    Author Samuel Ahuno
    Date <YYYY-MM-DD>
    Purpose <one-line description>
    Version <tool version>
    Source <URL if applicable>

%arguments                 (if using build-args)
    TOOL_VERSION=<default>

%post                      (required)
    <installation commands — see tier-specific recipes>
    mamba clean --all --yes
    # Do NOT rm -rf /tmp/*

%environment               (required)
    export PATH="/opt/conda/bin:$PATH"

%runscript                 (required)
    exec <primary_tool> "$@"

%test                      (required)
    <primary_tool> --version
```

### Critical %post rules (these prevent the most common failures):

1. **Never `rm -rf /tmp/*`** — `/tmp` is the host's `/tmp` under fakeroot.
2. **Never use `apt-get`** — `setgroups()` is blocked in root-mapped namespace.
3. **Never use NVIDIA `.run` installers** — no `/dev/tty` available.
4. **Pin all package versions** — `samtools=1.21` not `samtools`.
5. **Always `mamba clean --all --yes`** after installation.
6. **Every `--build-arg` must match a `%arguments` entry** — unused args are FATAL.

### Compiler symlinks (Tier 2+):
```bash
# Compilers are prefixed — build systems expect plain 'gcc'
ln -sf ${BIN}/x86_64-conda-linux-gnu-gcc ${BIN}/gcc
ln -sf ${BIN}/x86_64-conda-linux-gnu-g++ ${BIN}/g++
ln -sf ${BIN}/x86_64-conda-linux-gnu-cc ${BIN}/cc
ln -sf ${BIN}/x86_64-conda-linux-gnu-ar ${BIN}/ar
ln -sf ${BIN}/x86_64-conda-linux-gnu-ranlib ${BIN}/ranlib
```

### Sysroot libc symlinks (Tier 2+):
```bash
# The conda linker expects these at standard paths
SYSROOT="${ENV_PREFIX}/x86_64-conda-linux-gnu/sysroot"
mkdir -p /lib64 /usr/lib64
ln -sf ${SYSROOT}/lib64/libc.so.6 /lib64/libc.so.6
ln -sf ${SYSROOT}/usr/lib64/libc_nonshared.a /usr/lib64/libc_nonshared.a
ln -sf ${SYSROOT}/usr/lib64/libc.so /usr/lib64/libc.so
```

### CUDA symlinks (Tier 3):
```bash
# Conda cuda-toolkit puts headers/libs in a non-standard path
# Downstream cmake (PyTorch/Caffe2/libtorch) won't find them without symlinks
CUDA_TARGET="/opt/conda/targets/x86_64-linux"
for f in ${CUDA_TARGET}/include/*.h ${CUDA_TARGET}/include/*.hpp; do
    [ -f "$f" ] && ln -sf "$f" /opt/conda/include/
done
for d in ${CUDA_TARGET}/include/*/; do
    [ -d "$d" ] && ln -sfn "$d" /opt/conda/include/
done
for f in ${CUDA_TARGET}/lib/*.so* ${CUDA_TARGET}/lib/*.a; do
    [ -f "$f" ] && ln -sf "$f" /opt/conda/lib/
done
```

### Conda environments for specific Python versions:
```bash
# In %post — activate via sourcing, not conda init
. /opt/conda/etc/profile.d/conda.sh
conda activate envname

# In %environment — prepend PATH, never conda activate
export PATH="/opt/conda/envs/envname/bin:$PATH"
export CONDA_DEFAULT_ENV="envname"
export CONDA_PREFIX="/opt/conda/envs/envname"
```

## Step 3: Generate the Build Script

Every build script follows this template. The critical detail: use absolute
`PROJECT_DIR`, never `SCRIPT_DIR` from `BASH_SOURCE[0]` — SLURM copies scripts
to `/var/spool/slurmd/` which breaks relative path resolution.

```bash
#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: <YYYY-MM-DD>
# Purpose: Build <tool> Apptainer container using --fakeroot

set -euo pipefail

PROJECT_DIR="<absolute path to project directory>"
DEF_FILE="${PROJECT_DIR}/<tool>.def"
SIF_FILE="${PROJECT_DIR}/<tool>_v<version>.sif"
LOG_FILE="${PROJECT_DIR}/build_<tool>_$(date '+%Y%m%d_%H%M%S').log"

# Prevent host bind vars from leaking into %post
unset APPTAINER_BIND SINGULARITY_BIND 2>/dev/null || true

# Set cache dir to avoid home quota issues on compute nodes
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
mkdir -p "${APPTAINER_CACHEDIR}"

echo "=== Building <tool> container ===" | tee "$LOG_FILE"
echo "DEF:  ${DEF_FILE}" | tee -a "$LOG_FILE"
echo "SIF:  ${SIF_FILE}" | tee -a "$LOG_FILE"
echo "Start: $(date)" | tee -a "$LOG_FILE"

# --ignore-fakeroot-command: required for miniforge3 base on RHEL 8
apptainer build --fakeroot --ignore-fakeroot-command \
    "${SIF_FILE}" \
    "${DEF_FILE}" \
    2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=== Build finished: $(date) ===" | tee -a "$LOG_FILE"

# Smoke test
if [[ -f "${SIF_FILE}" ]]; then
    echo "=== Smoke test ===" | tee -a "$LOG_FILE"
    apptainer exec "${SIF_FILE}" <tool> --version 2>&1 | tee -a "$LOG_FILE" || true
    echo "=== DONE: build_<tool>.sh completed successfully ===" | tee -a "$LOG_FILE"
else
    echo "ERROR: SIF file not created" | tee -a "$LOG_FILE"
    exit 1
fi
```

Key build script rules:
- `set -euo pipefail` at top, but guard piped smoke test commands with `|| true` to avoid SIGPIPE (exit 141)
- `unset APPTAINER_BIND SINGULARITY_BIND` prevents host bind vars leaking into `%post`
- `APPTAINER_CACHEDIR` on shared filesystem avoids home quota issues
- `--fakeroot --ignore-fakeroot-command` are both always required
- For GPU tools, use `apptainer exec --nv` in the smoke test
- Log everything with `tee -a "$LOG_FILE"` and `2>&1`

## Step 4: Submit via SLURM

Use the SLURM MCP tools or provide an sbatch command. Resource estimates by tier:

| Tier | CPUs | Memory | Time |
|------|------|--------|------|
| 0 (pre-built binary) | 2 | 8G | 15 min |
| 1 (conda install) | 2 | 8G | 15 min |
| 2 (compiled extensions) | 4 | 16G | 30 min |
| 3 (full C++ + CUDA) | 8 | 64G | 4 hours |

Container builds never need GPU — submit to CPU partitions only.

## Debugging Failed Builds

When a build fails, check these in order:

| Error message | Cause | Fix |
|---------------|-------|-----|
| `unused build args: X` | `--build-arg` without matching `%arguments` | Add to `%arguments` or remove from build command |
| `cannot create /dev/tty` | Installer needs terminal (NVIDIA .run) | Use conda package or pre-built binary instead |
| `command 'gcc' failed` + gcc not found | Missing compiler | Add `gcc_linux-64` and create symlinks |
| `command 'gcc' failed` + `cannot find libc.so.6` | Linker can't find sysroot | Symlink sysroot libc to `/lib64/` and `/usr/lib64/` |
| `Could NOT find CUDA (missing: CUDA_INCLUDE_DIRS)` | Conda CUDA headers in non-standard path | Symlink headers to `/opt/conda/include/` and pass cmake hints |
| `Permission denied` writing log | SLURM spool dir not writable | Use absolute `PROJECT_DIR` not `SCRIPT_DIR` |
| Exit code 141 but SIF exists | SIGPIPE from piped smoke test | Build succeeded; add `\|\| true` to piped commands |
| Exit code 15 | SIGTERM from installer | Installer killed itself (no TTY); use conda alternative |

Always read the last 5 lines before the `FATAL:` line — that's where the actual error is.

## Harmless Warnings (Ignore These)

- `User not listed in /etc/subuid, trying root-mapped namespace` — expected, this is how we build
- `fakeroot command not found` — expected with `--ignore-fakeroot-command`
- `'nodev' mount option set on /tmp` — normal on compute nodes
- `SINGULARITY_DOCKER_PASSWORD is set, but APPTAINER_DOCKER_PASSWORD is preferred` — just a naming preference
- `gocryptfs not found` — for encrypted containers, which we don't use

## Production Container Checklist

After a successful build:
- [ ] SIF file exists and size is reasonable (not suspiciously small or large)
- [ ] Smoke test passes (`tool --version` or `python -c "import module"`)
- [ ] SIF named with version: `toolname_vX.Y.Z.sif`
- [ ] .def file kept alongside (or version-controlled) — the recipe must survive
- [ ] Build log kept for reproducibility audit trail
- [ ] Container registered in `profiles/software_configs/softwares_containers_config.yaml` if production
