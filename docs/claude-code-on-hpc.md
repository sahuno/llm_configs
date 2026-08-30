# Running Claude Code on HPC via Apptainer

How to run Claude Code inside an Apptainer container on a SLURM cluster, with
the scheduler still usable from inside it.

Written for MSKCC HPC (RHEL 8, no sudo, Apptainer) but the mechanism is general:
the hard parts are getting SLURM binaries and libraries into a container that was
not built with them, and getting a usable shell environment out of a runtime that
ignores your `~/.bashrc`. Both are solved below.

For "it broke, why" see the **Containers & HPC** and **Troubleshooting** sections
of [the FAQ](../claude/docs/FAQ.md).

---

## The `sclaude` function

Add to `~/.bashrc`. Replace the paths in `base_mounts` and `container` with your
own; everything else auto-detects.

```bash
sclaude() {
    local base_mounts="/data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs,/data1/greenbab/users/ahunos/blog,/data1/greenbab/database,/data1/greenbab/software/images,/data1/greenbab/users/ahunos,/data1/greenbab/users/ahunos/apps/containers,/data1/greenbab/users/ahunos/apptainer_cache,/data1/greenbab/projects/<your-project>,/data1/greenbab,/data1/collab001"
    local container="/data1/greenbab/software/images/claude_gemini_container_latest.sif"

    local appt=$(command -v apptainer || true)
    if [ -z "$appt" ]; then
        echo "Apptainer not found on PATH. Activate your env first (e.g., mamba activate snakemake)." >&2
        return 1
    fi

    # ── SLURM bind mounts ──────────────────────────────────────────────
    # Auto-detect SLURM location (works on any HPC regardless of install method)
    # Binaries → /usr/local/bin/ (already in container PATH, no conflict)
    # Libraries → /usr/lib64/ (default linker search path, no conflict)
    local slurm_mounts=""
    local slurm_bin_dir
    slurm_bin_dir="$(dirname "$(command -v sbatch 2>/dev/null)" 2>/dev/null)"
    if [ -n "$slurm_bin_dir" ]; then
        for cmd in sbatch squeue scancel sacct sinfo scontrol srun salloc sstat sreport sprio; do
            [ -f "${slurm_bin_dir}/${cmd}" ] && slurm_mounts="${slurm_mounts},${slurm_bin_dir}/${cmd}:/usr/local/bin/${cmd}"
        done
    fi
    # SLURM shared libraries — auto-detect lib dir from libslurm location
    local slurm_lib_dir
    slurm_lib_dir="$(dirname "$(readlink -f "$(ldconfig -p 2>/dev/null | awk '/libslurm\.so /{print $NF; exit}')" 2>/dev/null)" 2>/dev/null)"
    [ -z "$slurm_lib_dir" ] && slurm_lib_dir="/usr/lib64"  # fallback to standard RHEL path
    for lib in "${slurm_lib_dir}"/libslurm.so*; do
        [ -e "$lib" ] && slurm_mounts="${slurm_mounts},${lib}"
    done
    for lib in "${slurm_lib_dir}"/libmunge.so*; do
        [ -e "$lib" ] && slurm_mounts="${slurm_mounts},${lib}"
    done
    [ -d "${slurm_lib_dir}/slurm" ] && slurm_mounts="${slurm_mounts},${slurm_lib_dir}/slurm:${slurm_lib_dir}/slurm"
    # Config, munge socket, and user database for SlurmUser resolution
    [ -d "/etc/slurm" ]  && slurm_mounts="${slurm_mounts},/etc/slurm:/etc/slurm"
    [ -d "/run/munge" ]  && slurm_mounts="${slurm_mounts},/run/munge:/run/munge"
    [ -f "/etc/passwd" ] && slurm_mounts="${slurm_mounts},/etc/passwd:/etc/passwd"
    [ -f "/etc/group" ]  && slurm_mounts="${slurm_mounts},/etc/group:/etc/group"
    slurm_mounts="${slurm_mounts#,}"  # strip leading comma

    # Pass API keys from host into container
    local env_flags=""
    [ -n "$ANTHROPIC_API_KEY" ] && env_flags="$env_flags --env ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
    [ -n "$OPENAI_API_KEY" ] && env_flags="$env_flags --env OPENAI_API_KEY=$OPENAI_API_KEY"

    local all_mounts="${base_mounts},${slurm_mounts}"
    local additional_mounts=""
    if [ $# -gt 0 ]; then
        additional_mounts=$(IFS=,; echo "$*")
        all_mounts="${all_mounts},${additional_mounts}"
    fi

    "$appt" exec -B "$all_mounts" $env_flags "$container" \
        /bin/bash --rcfile ~/.bashrc_container -i
}
```

Usage:

```bash
sclaude                                        # standard mounts
sclaude /data1/greenbab/projects/my_proj       # plus extra bind mounts
sclaude /data1/greenbab/projects/p /data1/collab001/shared   # several
```

Activate the environment that provides Apptainer first (e.g.
`mamba activate snakemake`) — the function checks and refuses rather than failing
obscurely later.

---

## Why each part exists

### `exec` with an explicit rc file, not `shell`

`apptainer shell` does not source `~/.bashrc`, so aliases, API keys and PATH
customisations are silently absent. Running
`apptainer exec ... /bin/bash --rcfile ~/.bashrc_container -i` gives a shell that
loads a rc file written for the container.

### A separate `~/.bashrc_container`

Your host `~/.bashrc` is actively harmful inside a Debian-based container on a
RHEL host. A dedicated rc file:

- **Unsets leaked RHEL shell functions** — `which`, `module`, `ml`,
  `_module_raw`. These are functions, not binaries, and they break inside the
  container.
- **Clears polluted environment** — `LD_LIBRARY_PATH`, `CONDA_*`, `PYTHONPATH`,
  `MODULEPATH`, `LMOD_*`. Host library paths pointing at RHEL `.so` files will
  find the wrong ABI.
- **Sets a container-first PATH** — `/opt/venv/bin`, `/opt/npm-global/bin` ahead
  of anything host-mounted, so the container's own tools win.
- **Exports API keys with `${VAR:-}`** — inherits the value, never hardcodes one.
- **Sources `~/.bash_aliases`** for personal shortcuts.

A working copy ships at
`plugins/hpc-site/profiles/sites/mskcc-greenbaum/bashrc_container`.

### SLURM passthrough

The container was not built with SLURM. To make `sbatch` and friends work from
inside it, three things must be bound in:

1. **The binaries** — mounted to `/usr/local/bin/`, which is already on the
   container's PATH, so no PATH edit is needed and nothing shadows a container
   tool of the same name.
2. **The shared libraries** — `libslurm.so*`, `libmunge.so*`, and the
   `slurm/` plugin directory, mounted to their host location, which is on the
   default linker search path.
3. **Identity and authentication** — `/etc/slurm` for config, `/run/munge` for
   the auth socket, and `/etc/passwd` + `/etc/group` so `getpwuid()` can resolve
   the SlurmUser. Without the last of these, SLURM commands fail with
   "Couldn't determine user account information" — see the FAQ.

The lookup is done by `command -v sbatch` and `ldconfig -p` rather than
hardcoded, so the same function works on a cluster that installs SLURM
somewhere else.

### API key passthrough

Keys live in the host `~/.bashrc` and are passed with `--env`. They are never in
the container image and never in this repo. `~/.bashrc_container` inherits them
with `${ANTHROPIC_API_KEY:-}` rather than assigning a literal.

---

## Adapting this to another cluster

The auto-detection covers most of it. What you must change:

| Thing | Where |
|---|---|
| Bind mounts | `base_mounts` — your data roots, not `/data1/...` |
| Container image | `container` — your own SIF |
| Apptainer availability | However your site provides it (module load, conda, system) |

What you should check rather than assume:

- Does your site use **munge**? If not, drop `/run/munge`.
- Is SLURM installed somewhere `ldconfig` does not see? The fallback is
  `/usr/lib64`; adjust if your site differs.
- Does your container already contain SLURM clients? Then skip the binary mounts
  entirely — binding over them can mix client and library versions.

The `mskcc-hpc` skill in the `hpc-site` plugin records what was measured on the
reference cluster, and ends with a checklist of what is worth measuring on a new
one. Its findings will not transfer; the checklist will.

---

## Related

- [FAQ → Containers & HPC](../claude/docs/FAQ.md) — RHEL-to-Debian collisions,
  `APPTAINER_CACHEDIR`, GPU jobs failing silently, available containers
- [FAQ → Troubleshooting](../claude/docs/FAQ.md) — the `unknown userid` fatal,
  `gh auth login` certificate errors, `grep` timing out on data directories
- `singularity-build` skill — building images with `--fakeroot`, and the host
  SSL/CA env leak that crashes httpx clients inside a SIF
- `plugins/hpc-site/` — genome, container and scheduler configuration for this
  cluster
