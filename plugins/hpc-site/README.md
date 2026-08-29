# hpc-site

Site configuration for one SLURM cluster: MSKCC HPC, Greenbaum Lab (`greenbab`),
RHEL 8, Apptainer, no sudo.

**This is the plugin to fork.** The other two are meant to be installed as-is;
this one is a worked example of what a site layer contains. Every path and
partition name is specific to one cluster.

## Install

```
/plugin marketplace add sahuno/llm_configs
/plugin install hpc-site@sahuno
```

Then point `$SITE_CONFIG` at the profiles directory:

```bash
export SITE_CONFIG="$HOME/projects/llm_configs/plugins/hpc-site/profiles"
```

Anything that says `$SITE_CONFIG/...` resolves from there.

## Contents

```
profiles/
├── databases/databases_config.yaml            # genome registry (fasta, gtf, sizes, CpG islands, RepeatMasker)
├── software_configs/softwares_containers_config.yaml   # container image registry
├── workflow_profiles/
│   ├── executor_config.yaml                   # scheduler defaults
│   └── snakemakes/{slurmConfig,slurmMinimal}/ # Snakemake SLURM profiles
├── programming_language_profiles/
│   ├── python/matplotlib/matplotlib_defaults
│   └── R/.Rprofile
├── bash_profiles/bashrc_container             # rc file for the Apptainer shell
└── env/claude_env.template.sh                 # Claude Code env vars (copy to .local.sh)
skills/mskcc-hpc/                              # measured cluster knowledge
sites/example.yaml                             # blank template of the schemas above
```

## Genome builds

| Build | Species | Local | S3 |
|---|---|---|---|
| mm10 | Mouse | yes | yes |
| mm39 | Mouse | yes | yes |
| hg38 | Human | yes | yes |
| T2T-CHM13 | Human | yes | no |
| GRCh37 | Human | yes | yes |

## Standing this up for another cluster

1. Copy `sites/example.yaml` and fill in your paths — it documents the schema
   each `profiles/` file expects.
2. Replace `profiles/databases/databases_config.yaml` with your genome registry.
   Keep the key names; skills read them by name.
3. Replace the partition names in `profiles/workflow_profiles/`. Check which
   partitions your account may actually use first — on the reference cluster the
   *default* partition is denied to the lab account, so a bare `sbatch` fails.
4. Read `skills/mskcc-hpc/SKILL.md` for what else is worth measuring. Its
   findings will not transfer; the list of things to check does.

## Launching Claude Code inside the container

The `sclaude` shell function (Apptainer bind mounts, SLURM binary/library
passthrough, API-key forwarding) lives in the repo root README.
