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

Then select a profile. There are two independent axes:

```bash
source .../plugins/hpc-site/profiles/resolve.sh
export SITE_PROFILE=mskcc-greenbaum   # cluster facts
export USER_PROFILE=sahuno            # personal defaults (defaults to $USER)
profiles_export                       # sets $SITE_CONFIG and $USER_CONFIG
```

`*_PROFILE` selects **by name**; `*_CONFIG` is the **resolved directory** that
`$SITE_CONFIG/...` references in `CLAUDE.md` point at. Both axes auto-select when
there is exactly one real profile (the `example/` templates are ignored), and
`USER_PROFILE` falls back to `$USER`. When the choice is ambiguous, resolution
fails and lists the candidates rather than guessing.

**Why two axes.** Genome paths and partitions change when you change cluster;
plot defaults and sample-sheet conventions do not. Keeping them separate means
moving institution does not mean rebuilding your figure settings, and a labmate
can adopt your site profile without inheriting your `DO_NOT.md`. The `.Rprofile`
here already does macOS/Linux/Windows font detection — user profiles were always
written to travel.

## Contents

```
profiles/
├── resolve.sh                    # profile resolution (source this)
├── sites/                        # CLUSTER facts — change when you change institution
│   ├── mskcc-greenbaum/
│   │   ├── paths.yaml            # roots, container cache, tool checkouts, bind mounts
│   │   ├── databases.yaml        # reference genomes
│   │   ├── containers.yaml       # container image registry
│   │   ├── executor.yaml         # scheduler defaults
│   │   ├── snakemake/            # Snakemake SLURM profiles
│   │   ├── nextflow.config       # Nextflow SLURM profile (labels, retry, reporting)
│   │   └── bashrc_container      # rc file for the Apptainer shell
│   └── example/                  # fill-in template + what to measure
└── users/                        # PERSON facts — follow you across institutions
    ├── sahuno/
    │   ├── setup_preferences.yaml
    │   ├── DO_NOT.md
    │   ├── matplotlib_defaults
    │   ├── .Rprofile
    │   └── env/                  # Claude Code env var template
    └── example/
skills/mskcc-hpc/                 # measured cluster knowledge
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

1. `cp -r profiles/sites/example profiles/sites/<your-site>` and fill it in —
   its README documents every file a complete site profile holds.
2. Replace `$SITE_CONFIG/databases.yaml` with your genome registry.
   Keep the key names; skills read them by name.
3. Replace the partition names in your site profile's `executor.yaml` and
   `snakemake/`. Check which
   partitions your account may actually use first — on the reference cluster the
   *default* partition is denied to the lab account, so a bare `sbatch` fails.
4. Read `skills/mskcc-hpc/SKILL.md` for what else is worth measuring. Its
   findings will not transfer; the list of things to check does.

## Launching Claude Code inside the container

The `sclaude` shell function (Apptainer bind mounts, SLURM binary/library
passthrough, API-key forwarding) lives in the repo root README.
