# bio-skills

Genomics and computational-biology skills for Claude Code. Portable — nothing
here requires a particular cluster, though a few references mention the site
they were measured on.

## Install

```
/plugin marketplace add sahuno/llm_configs
/plugin install bio-skills@sahuno
```

## What you get

### Skills (13)

| Skill | Use it for |
|---|---|
| `snakemake` | Writing, debugging, and running Snakemake 9 workflows on SLURM |
| `nfcore-module` | Authoring nf-core-compliant Nextflow modules |
| `singularity-build` | Building Apptainer/Singularity containers with `--fakeroot`, no sudo |
| `docker-hpc` | Docker images intended to run under an HPC container runtime |
| `scatter-gather` | Deciding whether a step is shardable, poolable, or two-phase |
| `runtime-resource-study` | Designing a runtime/memory/cost study across a parameter grid |
| `analysis-gotchas` | Silent-failure modes: DSS, parallel R, small-n CV, `fread`, Clair3, Severus |
| `chimeric-read-validation` | Validating SV / viral-integration calls from split reads |
| `cohort-overview` | Cohort-wide sample × feature overview heatmaps |
| `heatmap-dimensions` | Publication heatmaps sized to journal specs |
| `barplot-long-labels` | Barplots whose category labels don't fit |
| `igv-screenshots` | Batch IGV/igver screenshots, including methylation coloring |
| `journal-club` | Paper ingest → quiz → critique → slides → write-up |

### Command

`/init-bio-project` — scaffold a project (config, sample sheet, immutable
`data/raw/`, genome-tagged `data/processed/`, workflow dirs, logs).

### Agent

`scientific-illustrator` — assembles raw plots into publication-ready
multipart figures.

## Lives elsewhere

`igv-reports` was split into its own repository once it grew a driver, cohort
mode, verifiers and CI: **https://github.com/sahuno/igv-reports-skill**. Clone it
and symlink into `~/.claude/skills/` if you want it.

## Site-dependent bits

Most skills are site-neutral. These reference a specific cluster's paths and
will need adjusting elsewhere — they are marked in-file:

- `snakemake/references/slurm_profiles.md` — example SLURM profiles
- `singularity-build/` — build script generation, image paths
- `runtime-resource-study/` — SLURM submit templates
- `chimeric-read-validation/examples/` — example invocations

Where a skill needs a genome or container path it should read it from
`$SITE_CONFIG` (see the `hpc-site` plugin) rather than hardcoding.

## Pairs with

- `bio-guardrails` — enforces the raw-data and genome-tagging conventions these
  skills assume
- `hpc-site` — supplies genome, container, and executor paths
