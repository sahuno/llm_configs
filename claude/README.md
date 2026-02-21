# Claude Code Configuration for Computational Biology

Personal Claude Code configuration for bioinformatics analysis, software development, and AI engineering on MSKCC HPC (Greenberg Lab).

## Quick Start

### 1. Copy config files to `~/.claude/`

```bash
cp claude/CLAUDE.md ~/.claude/CLAUDE.md
cp claude/settings.json ~/.claude/settings.json
cp -r claude/profiles ~/.claude/profiles
cp -r claude/hooks ~/.claude/hooks
chmod +x ~/.claude/hooks/*.sh
```

### 2. Launch Claude Code on HPC via Apptainer

Add `sclaude` to your `~/.bashrc`:

```bash
sclaude() {
    local base_mounts="/data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs,/data1/greenbab/users/ahunos/blog,/data1/greenbab/database,/data1/greenbab/software/images,/data1/greenbab/users/ahunos,/data1/greenbab/users/ahunos/apps/containers,/data1/greenbab/users/ahunos/apptainer_cache,/data1/greenbab/projects/triplicates_epigenetics_diyva,/data1/greenbab,/data1/collab001"
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

**Why `~/.bashrc_container`?** Apptainer does not source `~/.bashrc` by default. A dedicated container rc file loads aliases and exports while skipping host-only commands (`module`, conda init) that don't exist inside the container. See `~/.bashrc_container` for details.

Usage:
```bash
# Basic — open Claude shell with standard mounts
sclaude

# With extra bind mounts for a specific project
sclaude /data1/greenbab/projects/my_project
```

## Directory Structure

```
claude/
├── CLAUDE.md              # Main config (domain playbooks, rules, conventions)
├── settings.json          # Claude Code settings + hook wiring
├── hooks/                 # Hook scripts (genomic validation, safety guards)
│   ├── block-dangerous-commands.sh
│   ├── block-hardcoded-contigs.sh
│   ├── block-raw-data-writes.sh
│   ├── enforce-genome-tag.sh
│   ├── validate-reference-genome.sh
│   ├── validate-yaml.sh
│   ├── snakemake-dryrun.sh
│   └── warn-absolute-paths.sh
├── profiles/              # Reference data, containers, SLURM, plot defaults
│   ├── databases/databases_config.yaml
│   ├── software_configs/softwares_containers_config.yaml
│   ├── workflow_profiles/snakemakes/{slurmConfig,slurmMinimal}/
│   └── programming_language_profiles/{python,R}/
├── scripts/               # Helper scripts (project init, validation)
├── prompts/               # Reusable prompt templates
├── skills/                # Claude Code skills (IGV screenshots, heatmaps, barplots)
├── examples/              # Worked examples (methylation pipeline, RNA-seq)
└── agents/                # Custom agent definitions
```

## Active Hooks

All hooks are wired in `settings.json` and fire on `PreToolUse` or `PostToolUse` events.

| Hook | Event | Action | What it catches |
|------|-------|--------|----------------|
| `block-dangerous-commands.sh` | PreToolUse (Bash) | BLOCK | `rm -rf` on data, `snakemake --reason` |
| `block-raw-data-writes.sh` | PreToolUse (Write/Edit) | BLOCK | Any write to `data/raw/` |
| `validate-reference-genome.sh` | PreToolUse (Bash, Write/Edit) | BLOCK | Cross-species mixing, build mixing, chr naming mismatches |
| `enforce-genome-tag.sh` | PreToolUse (Bash, Write/Edit) | BLOCK | Genomic files without build tag in filename |
| `snakemake-dryrun.sh` | PostToolUse (Write/Edit) | WARN | Runs `snakemake -n` after `.smk` edits |
| `block-hardcoded-contigs.sh` | PostToolUse (Write/Edit) | WARN | Hardcoded chromosome lists in scripts |
| `validate-yaml.sh` | PostToolUse (Write/Edit) | WARN | Invalid YAML syntax in config files |
| `warn-absolute-paths.sh` | PostToolUse (Write/Edit) | WARN | Hardcoded `/data1/` or `/home/` in scripts |

## Supported Reference Genomes

Defined in `profiles/databases/databases_config.yaml`:

| Build | Species | Local | S3 |
|-------|---------|-------|----|
| mm10 | Mouse | Yes | Yes |
| mm39 | Mouse | Yes | Yes |
| hg38 | Human | Yes | Yes |
| T2T-CHM13 | Human | Yes | No |
| GRCh37 | Human | Yes | Yes |

## Updating

When you update configs in this repo, sync to local:
```bash
cp claude/CLAUDE.md ~/.claude/CLAUDE.md
cp claude/settings.json ~/.claude/settings.json
cp -r claude/hooks/*.sh ~/.claude/hooks/
cp -r claude/profiles ~/.claude/profiles
```
