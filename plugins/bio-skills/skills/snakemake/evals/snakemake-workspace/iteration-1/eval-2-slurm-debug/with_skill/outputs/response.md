# Diagnosis: SLURM_MEM_PER_NODE vs SLURM_MEM_PER_CPU Conflict

## Root Cause

Snakemake 9 has a **built-in default** of `mem_mb: 1000` that is always injected into every job's resource set, even if you never declare it in your profile. When the SLURM executor plugin translates resources to sbatch flags, it maps:

- `mem_mb` --> `--mem` (per-node) --> sets `SLURM_MEM_PER_NODE`
- `mem_mb_per_cpu` --> `--mem-per-cpu` --> sets `SLURM_MEM_PER_CPU`

SLURM considers these two environment variables **mutually exclusive**. Because your profile specifies `mem_mb_per_cpu: 16000` but does NOT explicitly zero out Snakemake's built-in `mem_mb: 1000`, both flags are passed to sbatch simultaneously, and SLURM rejects the job with the fatal error:

```
Fatal: SLURM_MEM_PER_NODE and SLURM_MEM_PER_CPU are mutually exclusive
```

## What Is Missing From Your Profile

1. **`mem_mb: 0` in `default-resources`** -- This zeroes out the built-in default, preventing `--mem` from being passed alongside `--mem-per-cpu`. This is the direct fix for your error.

2. **`slurm_account`** -- Without this, SLURM will silently reject jobs on clusters that require an account (like MSKCC/iris). Not the cause of your current error, but will cause silent failures once the memory issue is fixed.

## Additional Issues (not causing this error, but important)

- Your profile has no `runtime` default. SLURM will use the partition's default time limit, which may be shorter than your jobs need.
- No `latency-wait` setting. On NFS-based HPC systems, output files can take seconds to appear. Without latency-wait, Snakemake may falsely report missing outputs.

## The Fix

Add `mem_mb: 0` to your `default-resources` block. This tells Snakemake "do not pass `--mem` to sbatch", so only `--mem-per-cpu` is used.

## Corrected Profile

```yaml
executor: slurm

default-resources:
  slurm_partition: componc_cpu
  slurm_account: greenbab
  mem_mb: 0
  mem_mb_per_cpu: 16000
  cpus_per_task: 4
  nodes: 1
  runtime: 240

jobs: unlimited
keep-incomplete: true
printshellcmds: true
latency-wait: 360
max-status-checks-per-second: 1
```

## Coordinator Script Warning

If you submit the Snakemake coordinator itself as a SLURM batch job (common practice), make sure the coordinator's sbatch header uses `--mem-per-cpu` and NOT `--mem`. If the coordinator is launched with `--mem=XG`, the environment variable `SLURM_MEM_PER_NODE` propagates to all child jobs via `--export=ALL`, causing the exact same conflict. Add `unset SLURM_MEM_PER_NODE` at the top of your coordinator submit script as a safety measure:

```bash
#!/bin/bash
#SBATCH --mem-per-cpu=4000
#SBATCH -c 2
#SBATCH -p componc_cpu
#SBATCH --account=greenbab

unset SLURM_MEM_PER_NODE

snakemake --snakefile /path/to/Snakefile \
    --configfile /path/to/config.yaml \
    --workflow-profile /absolute/path/to/profiles/slurm \
    --use-singularity
```
