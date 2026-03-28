## Singularity/Apptainer Fakeroot Build Guide for MSKCC HPC (RHEL 8, No Sudo)

### 1. Understanding Your Build Environment

1.1. **You do not have sudo.** You cannot run `apptainer build` as root. You must use `--fakeroot`.

1.2. **True fakeroot is not available.** Your user is not listed in `/etc/subuid`, so Apptainer falls back to **root-mapped namespace** — a more limited unprivileged build mode. This is sufficient for conda-based builds but imposes hard constraints (see below).

1.3. **The `--ignore-fakeroot-command` flag is mandatory** when using `condaforge/miniforge3` as the base image. The miniforge3 image ships a `fakeroot` binary compiled against GLIBC >= 2.33. RHEL 8's login/compute nodes have GLIBC 2.28 — the `faked` daemon crashes immediately at `%post` start without this flag.

1.4. **The HPC runs RHEL 8 (kernel 4.18, GLIBC 2.28).** Many modern base images assume newer GLIBC. Always test that your chosen base image's binaries work under this constraint.

---

### 2. Choosing a Base Image

2.1. **Always use `condaforge/miniforge3:latest`** (or a specific tag) as the base image. This gives you `mamba`/`conda` for all package management and avoids the need for `apt-get`, `yum`, or any system package manager.

2.2. **Never use Ubuntu/Debian base images** (e.g., `ubuntu:22.04`) unless you have true fakeroot. `apt-get` internally calls `setgroups()` via the `_apt` user — this syscall is blocked in root-mapped namespace. The build will fail silently or with a cryptic permissions error.

2.3. **Never use `nvidia/cuda:*-devel-*` base images** for the same reason — they require `apt-get` to install dependencies.

2.4. **For GPU/CUDA software**, install the CUDA toolkit via conda (`mamba install -c nvidia cuda-toolkit=12.8`) instead of using NVIDIA base images or the `.run` installer.

---

### 3. The .def File — Mandatory Structure

3.1. **Always include `%labels`** with Author, Date, Purpose, Version, and Source URL. This is your container's provenance record.

3.2. **Use `%arguments`** for version numbers and build parameters. This makes the def file reusable. Reference them in `%post` with `{{ ARG_NAME }}` syntax.

3.3. **Every `--build-arg` passed in the build script must have a matching `%arguments` entry.** Apptainer treats unused build-args as a FATAL error (not a warning). If you remove an argument from the def file, remove the corresponding `--build-arg` from the build script.

3.4. **Always include a `%test` section** that verifies the primary tool works. For GPU tools that won't run on CPU-only build nodes, use a fallback: `tool --version || echo "NOTE: may require GPU"`.

3.5. **Always include `%environment`** to set PATH and LD_LIBRARY_PATH so the container works without the user needing to know internal paths.

3.6. **Always include `%runscript`** with `exec tool "$@"` so the container can be invoked directly as `./container.sif <args>`.

---

### 4. The %post Section — Critical Rules

#### 4A. Package Installation

4.1. **Install everything via `mamba` (preferred) or `conda`.** Use `-c conda-forge -c bioconda` for bioinformatics tools. Use `-c nvidia` for CUDA packages. Never use `apt-get`, `yum`, or `pip install` for anything that has a conda package.

4.2. **Pin versions explicitly** for reproducibility. `samtools=1.21` not `samtools`. The container must rebuild identically months later.

4.3. **Run `mamba clean --all --yes` after installation** to remove cached packages and reduce image size. Similarly `pip cache purge` if pip was used.

#### 4B. Things That Will Destroy Your Build (or Worse, Your Host)

4.4. **NEVER `rm -rf /tmp/*` or `rm -rf /var/tmp/*` in `%post`.** Under fakeroot/root-mapped namespace, the container's `/tmp` is a bind mount of the **host's `/tmp`**. This deletes other users' socket files, session data, and active build artifacts. Only remove files you explicitly created by name: `rm -f /tmp/myinstaller.sh`.

4.5. **NEVER use NVIDIA's `.run` installer** (e.g., `cuda_12.8.0_570.86.10_linux.run`). It requires `/dev/tty` for its self-extraction wrapper. Inside fakeroot builds there is no TTY — the installer sends SIGTERM to itself and kills `%post`. The `--silent` flag does not help; the wrapper probes `/dev/tty` before reaching that flag.

4.6. **NEVER use `apt-get`** in fakeroot builds on this HPC. See point 2.2.

#### 4C. Compiler Toolchain (When Building from Source)

4.7. **Install conda compilers**: `gcc_linux-64`, `gxx_linux-64`, and `sysroot_linux-64`. These are cross-compiler packages that are self-contained and do not depend on system headers.

4.8. **Conda compilers are prefixed** (e.g., `x86_64-conda-linux-gnu-gcc`). Many build systems (cmake, setuptools, Cython linking) expect plain `gcc`. **Always create symlinks:**
```bash
ln -sf ${BIN}/x86_64-conda-linux-gnu-gcc ${BIN}/gcc
ln -sf ${BIN}/x86_64-conda-linux-gnu-g++ ${BIN}/g++
ln -sf ${BIN}/x86_64-conda-linux-gnu-cc ${BIN}/cc
ln -sf ${BIN}/x86_64-conda-linux-gnu-ar ${BIN}/ar
ln -sf ${BIN}/x86_64-conda-linux-gnu-ranlib ${BIN}/ranlib
```

4.9. **The conda `compiler_compat/ld` linker expects system libc at `/lib64/libc.so.6` and `/usr/lib64/libc_nonshared.a`.** Inside a fakeroot build from a miniforge3 base, these don't exist. You must symlink from the conda sysroot:
```bash
SYSROOT="${ENV_PREFIX}/x86_64-conda-linux-gnu/sysroot"
mkdir -p /lib64 /usr/lib64
ln -sf ${SYSROOT}/lib64/libc.so.6 /lib64/libc.so.6
ln -sf ${SYSROOT}/usr/lib64/libc_nonshared.a /usr/lib64/libc_nonshared.a
ln -sf ${SYSROOT}/usr/lib64/libc.so /usr/lib64/libc.so
```

4.10. **Verify the compiler works before proceeding** with `gcc --version`. If it's not >= gcc-11, many modern C++ projects (C++17/C++20) will fail.

#### 4D. CUDA Toolkit via Conda

4.11. **Conda's `cuda-toolkit` installs headers and libs in a non-standard location**: `/opt/conda/targets/x86_64-linux/include` and `/opt/conda/targets/x86_64-linux/lib`. CMake's `find_package(CUDAToolkit)` finds this, but downstream cmake scripts (e.g., PyTorch/Caffe2/libtorch) may not.

4.12. **Symlink all CUDA headers and libraries to `/opt/conda/include/` and `/opt/conda/lib/`** so that downstream build systems find them:
```bash
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

4.13. **Set all CUDA environment variables** that various build systems may probe:
```bash
export CUDA_HOME=/opt/conda
export CUDA_PATH=/opt/conda
export CUDA_INCLUDE_DIRS=/opt/conda/targets/x86_64-linux/include
export CUDA_TOOLKIT_ROOT_DIR=/opt/conda
```

4.14. **Pass CUDA hints explicitly to cmake**:
```bash
cmake -DCUDAToolkit_ROOT=/opt/conda \
      -DCUDA_TOOLKIT_ROOT_DIR=/opt/conda \
      -DCUDA_INCLUDE_DIRS=/opt/conda/targets/x86_64-linux/include \
      -DCMAKE_CUDA_COMPILER=/opt/conda/bin/nvcc \
      ...
```

#### 4E. Conda Environments Inside Containers

4.15. **If the tool requires a specific Python version** (e.g., Python 3.6), use `mamba create -n envname python=3.6 ...` to create a named environment. The base miniforge3 image ships a modern Python that you cannot downgrade in-place.

4.16. **To activate a conda env in `%post`**, source the conda profile script:
```bash
. /opt/conda/etc/profile.d/conda.sh
conda activate envname
```
Do not rely on `conda init` — it modifies `.bashrc` which is not sourced during `%post`.

4.17. **In `%environment`, do NOT use `conda activate`.** Instead, prepend the env's bin directory to PATH:
```bash
export PATH="/opt/conda/envs/envname/bin:$PATH"
export CONDA_DEFAULT_ENV="envname"
export CONDA_PREFIX="/opt/conda/envs/envname"
```

#### 4F. Cleanup and Image Size

4.18. **Remove source code after `cmake --install`**: `rm -rf /opt/source-dir`. Build artifacts (object files, cmake caches) can add gigabytes.

4.19. **Use `mamba clean --all --yes`** after every `mamba install` block.

4.20. **Use `pip cache purge`** after pip installs. Guard with `|| true` for older pip versions that don't have this command.

4.21. **Only remove files you created by name.** Never use broad `rm -rf` patterns on system directories inside `%post`.

---

### 5. The Build Script — Mandatory Structure

5.1. **Use `set -euo pipefail`** at the top. But beware: this makes piped commands fail on SIGPIPE (see 5.9).

5.2. **Use an absolute `PROJECT_DIR`**, not `SCRIPT_DIR` derived from `BASH_SOURCE[0]`. When SLURM runs the script, it copies it to `/var/spool/slurmd/jobNNNNN/` — `BASH_SOURCE[0]` resolves to the spool directory, which is not writable for log files and doesn't contain your .def file.
```bash
# WRONG — fails under SLURM:
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# CORRECT:
PROJECT_DIR="/data1/greenbab/users/ahunos/path/to/project"
```

5.3. **Always `unset APPTAINER_BIND SINGULARITY_BIND`** before building. These environment variables are applied during `%post`. If a bind source path doesn't exist inside the base image, the build fails with a fatal mount error.

5.4. **Always set `APPTAINER_CACHEDIR`** to a path on the shared filesystem (e.g., `/data1/greenbab/users/ahunos/apptainer_cache`). The default cache goes to `~/.apptainer/cache` which may exceed home directory quota, especially on compute nodes.

5.5. **The build command template is:**
```bash
apptainer build --fakeroot --ignore-fakeroot-command \
    [--build-arg "KEY=VALUE" ...] \
    output.sif \
    input.def \
    2>&1 | tee -a "$LOG_FILE"
```

5.6. **Always log everything** with `tee -a "$LOG_FILE"`. Capture both stdout and stderr with `2>&1`. Log start time, def path, sif path, and any build-args for reproducibility.

5.7. **Always include a smoke test** after the build. Verify the SIF exists and the primary tool runs:
```bash
if [[ -f "${SIF_FILE}" ]]; then
    apptainer exec "${SIF_FILE}" tool --version 2>&1 | tee -a "$LOG_FILE"
else
    echo "ERROR: SIF file not created"
    exit 1
fi
```

5.8. **For GPU tools, use `--nv` in the smoke test** on GPU nodes: `apptainer exec --nv container.sif tool --version`. On CPU-only nodes, add `|| true` since the tool may fail without GPU access.

5.9. **Guard piped commands with `|| true`** in the smoke test section. Under `set -euo pipefail`, commands like `samtools --version | head -1` cause exit code 141 (SIGPIPE) because `head` closes the pipe early. This makes the entire script report failure even though the build succeeded.

---

### 6. SLURM Submission

6.1. **Resource estimates for container builds:**

| Build type | CPUs | Memory | Time |
|-----------|------|--------|------|
| Simple conda install (samtools) | 2 | 8G | 15 min |
| Python package with Cython compilation | 4 | 16G | 30 min |
| Compile from source (dorado + CUDA) | 8 | 64G | 4 hours |
| Pre-built binary download (dorado prebuilt) | 2 | 8G | 15 min |

6.2. **Memory for compilation**: budget ~1-2 GB per parallel compile thread. For `-j 8`, request at least 16-32G. Large C++ projects with heavy template use (like dorado/libtorch) need 64G.

6.3. **Container builds do not need GPU.** Submit to CPU partitions. GPU is only needed at *runtime* (with `--nv`).

6.4. **`'nodev' mount option set on /tmp`** warning is normal on compute nodes. It doesn't prevent builds.

6.5. **INFO messages about `SINGULARITY_DOCKER_PASSWORD`/`SINGULARITY_DOCKER_USERNAME`** are harmless warnings about preferring `APPTAINER_` prefixed env vars. Ignore them.

6.6. **INFO `gocryptfs not found`** is harmless. It's for encrypted containers, which we don't use.

---

### 7. Three Build Tiers (Decision Framework)

When containerizing a bioinformatics tool, classify it into one of three tiers:

**Tier 1: Conda-installable tool** (e.g., samtools, minimap2, bedtools)
- Simplest. `mamba install -c bioconda tool=version` in `%post`.
- Build time: ~1-2 minutes.
- Example: `samtools.def`

**Tier 2: Python/R package with compiled extensions** (e.g., LocusMasterTE, Telescope, pysam)
- Needs conda compilers (`gcc_linux-64`, `gxx_linux-64`, `sysroot_linux-64`).
- Needs compiler symlinks (`gcc` -> `x86_64-conda-linux-gnu-gcc`).
- Needs sysroot libc symlinks to `/lib64/` and `/usr/lib64/`.
- May need a specific Python version via named conda env.
- Build time: ~2-5 minutes.
- Example: `locusmasterte.def`

**Tier 3: Full C/C++ compilation with CUDA** (e.g., dorado, Clair3, minimap2 from source)
- Needs everything from Tier 2.
- Needs conda `cuda-toolkit` with header/lib symlinks.
- Needs explicit cmake CUDA hints.
- Source downloaded via `git clone --recurse-submodules`.
- Cleanup source after install to reduce image size.
- Build time: 10-60+ minutes.
- Example: `dorado_compile.def`

**Tier 0: Pre-built binary** (e.g., dorado from CDN, IGV, commercial tools)
- Download the tarball with `wget` (install wget via mamba).
- Extract to `/opt/toolname`.
- No compilers needed.
- Build time: ~1-2 minutes.
- Example: `dorado.def` (pre-built version)

---

### 8. Debugging Failed Builds

8.1. **Read the FULL error — especially the last 5 lines of stdout.** The `FATAL: While performing build: while running engine: while running %post section: exit status N` line tells you the section failed, but the actual error is in the lines immediately above it.

8.2. **Common exit codes:**
- `exit status 1` — generic error (command failed). Read the output above the FATAL line.
- `exit status 15` — SIGTERM. Usually means an installer killed itself (e.g., CUDA `.run` installer with no `/dev/tty`).
- `exit status 141` — SIGPIPE. Usually from piped commands in `%test` or smoke test. The build itself may have succeeded — check if the SIF file exists.
- `exit status 255` — Apptainer-level error (unused build-args, missing def file, permission denied).

8.3. **"unused build args: X"** — You're passing `--build-arg X=val` but the def file has no `%arguments` entry for `X`. Either add it to `%arguments` or remove from the build command.

8.4. **"cannot create /dev/tty: No such device or address"** — An installer or tool is trying to open a terminal. It cannot work in fakeroot builds. Find a conda package or pre-built binary instead.

8.5. **"command 'gcc' failed with exit status 1"** — Two possible causes:
- gcc not found: Add `gcc_linux-64` to conda packages and symlink to `gcc`.
- Linker can't find libc: Symlink sysroot libc to `/lib64/` and `/usr/lib64/`.

8.6. **"Could NOT find CUDA (missing: CUDA_INCLUDE_DIRS)"** — Conda CUDA headers are in `/opt/conda/targets/x86_64-linux/include/`, not where cmake expects. Symlink them to `/opt/conda/include/` and pass `-DCUDA_INCLUDE_DIRS` to cmake.

8.7. **"Permission denied" writing log file** — Build script is running from SLURM spool dir. Use absolute `PROJECT_DIR` instead of `SCRIPT_DIR`.

8.8. **Build succeeds on login node but fails on compute node** — Likely a bind mount difference. Check that `APPTAINER_BIND`/`SINGULARITY_BIND` are unset and that the def file and SIF output path are on a shared filesystem visible to compute nodes.

---

### 9. Testing and Validation

9.1. **Test interactively first** (`./build_script.sh` on a login node) before submitting to SLURM. Login node builds are faster to debug.

9.2. **Then test via SLURM** to ensure the build works on compute nodes (different mounts, no TTY, different environment).

9.3. **Smoke test every container** after build: import the main module (Python), run `--version` or `--help`, verify all expected binaries are in PATH.

9.4. **For GPU tools**, run the smoke test on a GPU node with `--nv`: `apptainer exec --nv container.sif tool --version`.

9.5. **Check the SIF file size.** Suspiciously small (<10MB) usually means the build didn't install what you expected. Suspiciously large (>5GB) means you forgot cleanup.

---

### 10. Production Container Management

10.1. **Name SIF files with version**: `toolname_vX.Y.Z.sif`, not `toolname.sif`. Multiple versions should coexist.

10.2. **Store production containers** in `softwares/containers/` under the project, and register them in `profiles/software_configs/softwares_containers_config.yaml`.

10.3. **Keep the .def file alongside the .sif** (or in a version-controlled directory). The def file is the recipe — without it the container is a black box.

10.4. **Keep the build log.** If a container produces unexpected results months later, the build log shows exactly what was installed.

10.5. **Never modify a production SIF in place.** Build a new one, test it, then replace.

---

### 11. Quick Reference — The Apptainer Build Command

```bash
# ALWAYS before building:
unset APPTAINER_BIND SINGULARITY_BIND
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache

# The build:
apptainer build --fakeroot --ignore-fakeroot-command \
    [--build-arg "KEY=VALUE"] \
    output.sif \
    input.def
```

### 12. Quick Reference — Minimum Viable .def Template

```
Bootstrap: docker
From: condaforge/miniforge3:latest

%labels
    Author Samuel Ahuno
    Date YYYY-MM-DD
    Purpose <what this container does>
    Version <tool version>

%post
    mamba install -y -c conda-forge -c bioconda <packages>
    mamba clean --all --yes
    # Do NOT rm -rf /tmp/*

%environment
    export PATH="/opt/conda/bin:$PATH"

%runscript
    exec <tool> "$@"

%test
    <tool> --version
```
