# Pipeline development: Snakemake and Nextflow conventions

Moved from CLAUDE.md §4 on 2026-09-30. SLURM-executor pitfalls are in the `snakemake` skill (`references/gotchas.md`, `references/slurm_profiles.md`).

### Pipeline Development (Snakemake / Nextflow)

**Snakemake rules**:
- There is no `--reason` argument for snakemake. Do not use it.
- If a rule sets the `singularity:` directive, do NOT add `singularity exec -B ...` inside the shell block. The directive handles container binding.
- Load SLURM profiles from `$SITE_CONFIG/snakemake/slurmConfig/config.yaml` or `slurmMinimal/config.yaml`.
- Load executor settings from `$SITE_CONFIG/executor.yaml`.
- Sample sheet format: TSV with columns `patient, sample, condition, assay, path, genome` (defined in `$USER_CONFIG/setup_preferences.yaml`).

**Snakemake run organization**:
- Pipeline code (Snakefile, rules, profiles) is versioned and reusable. Never write outputs into the pipeline directory.
- **One run = one directory.** All outputs from a run — rule outputs, figures, and logs — live under one named `results/<run>/` directory. This makes runs independently archivable (`tar -czf`) and deletable (`rm -rf`) with zero ambiguity about which run produced which file.
- `output_dir` is the only path key in config. Derive `FIGDIR` and `LOGDIR` from it in the Snakefile: `FIGDIR = f"{OUTDIR}/figures"`. Never add separate `figures_dir` or `log_dir` config keys — separate keys allow paths to diverge and recreate the ambiguity problem.
- One config file per run, named to match the results directory.
- Run naming convention: `{date}_{genome}_{description}` (e.g. `20260305_hg38_differential_methylation`, `20260310_mm10_v1`).

**Nextflow**: the site profile is `$SITE_CONFIG/nextflow.config` — SLURM executor, account, partitions by label (`short`, `long`, `gpu`, `benchmark`), apptainer with `--cleanenv`, OOM retry with escalating memory, and `cache = 'lenient'` for the shared filesystem. A pipeline inherits it with `includeConfig`; `/init-bio-project --engine nextflow` scaffolds that. Run with `-profile slurm -resume`, smoke-test with `-profile test`.

Nextflow emits `timeline`, `report`, `trace` and `dag` into `results/pipeline_info/` by default here. The trace carries `peak_rss` and `%cpu`, which is what makes a runtime-resource study a query rather than a project.
