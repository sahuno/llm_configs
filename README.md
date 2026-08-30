# llm_configs

Claude Code plugins for computational biology — genomics skills, safety
guardrails, and HPC site configuration.

Maintained by Samuel Ahuno (Greenbaum Lab, MSKCC). Built for bioinformatics on a
SLURM cluster, but the skills and guardrails are usable anywhere.

## Install

```
/plugin marketplace add sahuno/llm_configs
/plugin install bio-skills@sahuno
```

Three plugins, install what you want:

| Plugin | Contents | Portable? |
|---|---|---|
| **bio-skills** | 13 skills, `/init-bio-project`, figure agent | Yes |
| **bio-guardrails** | 9 hooks — raw-data protection, genome-build tagging | Yes, if you adopt the layout |
| **hpc-site** | Genome + container registries, SLURM profiles, cluster knowledge | No — fork it |

`bio-skills` stands alone. `bio-guardrails` assumes the project layout that
`/init-bio-project` creates. `hpc-site` is one cluster's configuration, kept
public as a worked example of what a site layer holds — see its README for how
to stand one up elsewhere.

Installing merges into your Claude Code config. Nothing overwrites your
`settings.json`.

## Repository layout

```
.claude-plugin/marketplace.json   # marketplace manifest
plugins/
├── bio-skills/                   # skills/, commands/, agents/, scripts/
├── bio-guardrails/               # hooks/ + hooks.json
└── hpc-site/                     # profiles/, skills/, sites/
claude/                           # personal config, not shipped as a plugin
├── CLAUDE.md                     # author's memory file
├── settings.json                 # author's Claude Code settings
├── docs/, examples/, prompts/, mcps/
cli_coding_agents_setups/         # non-Claude agent setups (Gemini, Codex)
docs/superpowers/                 # dated design records
```

## Site and user profiles

Skills never hardcode genome or container paths. They read them from a
**profile**, and profiles come in two independent axes:

- **`sites/`** — cluster facts: reference genomes, container images, SLURM
  partitions, bind mounts. These change when you change institution.
- **`users/`** — person facts: plot defaults, sample-sheet conventions,
  `DO_NOT` rules. These follow you across institutions.

```bash
source plugins/hpc-site/profiles/resolve.sh
export SITE_PROFILE=mskcc-greenbaum   # or your own
export USER_PROFILE=$USER
profiles_export                       # -> $SITE_CONFIG, $USER_CONFIG
```

Both auto-select when there is exactly one real profile, and fail loudly rather
than guessing when ambiguous.

| File | Axis | Holds |
|---|---|---|
| `paths.yaml` | site | Roots, container cache, tool checkouts, bind-mount sets |
| `databases.yaml` | site | Reference genomes — fasta, gtf, chrom.sizes, CpG islands |
| `containers.yaml` | site | Container images |
| `executor.yaml` | site | SLURM partitions, scheduler defaults |
| `setup_preferences.yaml` | user | Sample-sheet format and analysis preferences |
| `DO_NOT.md` | user | Prohibited actions — read before anything destructive |
| `matplotlib_defaults`, `.Rprofile` | user | Plot defaults |

`profiles/sites/example/` and `profiles/users/example/` are fill-in templates.
Adding a new cluster means adding a profile, not forking the plugin.

## Running Claude Code on HPC via Apptainer

Add to `~/.bashrc`:

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

Apptainer does not source `~/.bashrc`, so the function uses a dedicated
`~/.bashrc_container` (template in
`plugins/hpc-site/profiles/bash_profiles/bashrc_container`) that loads aliases
and exports while skipping host-only commands like `module` and conda init.

```bash
sclaude                                    # standard mounts
sclaude /data1/greenbab/projects/my_proj   # plus extra bind mounts
```

## Contributing a skill

Skills live in `plugins/bio-skills/skills/<name>/SKILL.md`. The filename is
case-sensitive on Linux — `skill.md` will not load. Keep site-specific paths out
of `SKILL.md`; read them from `$SITE_CONFIG` instead.


#########CLAUDE: DONOT DELETE##########################
FEATURE REQUEST
1. Transition to nextflow
 a. ease resume of failed workflow 
 b. detail logging and workflow metadata
 c. intgration with seqera AI
2. Logging of tasks completed and pending; logging of daily taks done 
3. use `UV` for python package management
#######################################################
