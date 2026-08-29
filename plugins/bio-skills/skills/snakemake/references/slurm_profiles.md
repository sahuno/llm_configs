# SLURM Profile Templates for Snakemake 9

Three tiers of profiles, from development to production. Default to slurmMinimal
for testing. Sample count alone doesn't determine tier — 4 large ONT BAMs can
require production-level resources.

## Critical Rules for ALL Profiles

1. `mem_mb: 0` in `default-resources` — zeroes out Snakemake's built-in `mem_mb: 1000` default that conflicts with `mem_mb_per_cpu`
2. `slurm_account` in `default-resources` — without it, jobs are silently rejected
3. Never use `mem:` anywhere — it sets `SLURM_MEM_PER_NODE` which conflicts
4. `singularity-args:` (no `--` prefix) — with `--` prefix the key is not recognized
5. `use-singularity: true` — must also pass `--use-singularity` on coordinator CLI

## Tier 1: Dev/Testing (slurmMinimal)

Short queues, minimal resources, tolerant of failures.

```yaml
executor: slurm

default-resources:
    slurm_partition: "cpushort"
    slurm_account: "greenbab"
    mem_mb: 0
    mem_mb_per_cpu: 8000
    cpus_per_task: 4
    nodes: 1
    runtime: 60

set-resources:
    gpu_rule:
        slurm_partition: "gpushort"
        runtime: 120
        slurm_extra: "'--gres=gpu:2'"
        mem_mb_per_cpu: 16000
        cpus_per_task: 4
    heavy_cpu_rule:
        slurm_partition: "cpushort"
        runtime: 120
        mem_mb_per_cpu: 16000
        cpus_per_task: 4

cores: all
jobs: unlimited
keep-incomplete: true
keep-going: true              # tolerate failures during testing
rerun-incomplete: true        # pick up failed jobs automatically
printshellcmds: true
latency-wait: 120             # faster feedback
max-status-checks-per-second: 1

use-singularity: true
singularity-args: "--bind /data1/greenbab/,/data1/collab001/"
```

## Tier 2: Production (slurmConfig)

Generous resources, strict failure handling. No `keep-going` — one bad sample
shouldn't silently propagate.

```yaml
executor: slurm

default-resources:
    slurm_partition: "componc_cpu"
    slurm_account: "greenbab"
    mem_mb: 0
    mem_mb_per_cpu: 32000
    cpus_per_task: 8
    nodes: 1
    runtime: 480

set-resources:
    gpu_rule:
        slurm_partition: "componc_gpu_batch"
        runtime: 3400
        slurm_extra: "'--gres=gpu:4'"
        mem_mb_per_cpu: 34000
        cpus_per_task: 8
    heavy_cpu_rule:
        slurm_partition: "componc_cpu"
        runtime: 2400
        mem_mb_per_cpu: 64000
        cpus_per_task: 12

jobs: unlimited
keep-incomplete: true
printshellcmds: true
latency-wait: 360             # tolerate NFS lag
max-status-checks-per-second: 1
# NOTE: no keep-going, no rerun-incomplete — fail explicitly in production

use-singularity: true
singularity-args: "--bind /data1/greenbab/,/data1/collab001/"
```

## Tier 3: Workflow-Specific (per-workflow)

Minimal defaults, per-rule overrides matching actual resource needs. Use benchmark
data from test runs to set accurate values.

```yaml
executor: slurm

default-resources:
    slurm_partition: "componc_cpu"
    slurm_account: "greenbab"
    mem_mb: 0
    mem_mb_per_cpu: 4000
    cpus_per_task: 1
    nodes: 1
    runtime: 60

set-resources:
    convert_bed_chr:
        slurm_partition: "cpushort"
        runtime: 5
        mem_mb_per_cpu: 2000
        cpus_per_task: 1
    modkit_pileup:
        slurm_partition: "componc_cpu"
        runtime: 240
        mem_mb_per_cpu: 4000
        cpus_per_task: 8
    aggregate_methylation:
        slurm_partition: "cpushort"
        runtime: 30
        mem_mb_per_cpu: 4000
        cpus_per_task: 2

jobs: unlimited
keep-incomplete: true
printshellcmds: true
latency-wait: 360
max-status-checks-per-second: 1

use-singularity: true
singularity-args: "--bind /data1/greenbab/,/data1/collab001/"
```

## Snakemake 9 + SLURM Pitfall Table

| # | Pitfall | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Built-in `mem_mb: 1000` conflicts with `mem_mb_per_cpu` | `SLURM_MEM_PER_NODE` vs `SLURM_MEM_PER_CPU` fatal error | Add `mem_mb: 0` to `default-resources` in every profile |
| 2 | `mem:` in profile sets `SLURM_MEM_PER_NODE` | Same fatal conflict with any `mem_mb_per_cpu` | Never use `mem:` — always use `mem_mb_per_cpu` |
| 3 | Missing `slurm_account` in default-resources | Silent job rejection (no error in Snakemake log) | Always set `slurm_account: "greenbab"` in `default-resources` |
| 4 | `use-singularity: true` in profile doesn't propagate to child SLURM jobs | Jobs run without container; tools not found or wrong Python | Pass `--use-singularity` on the coordinator CLI explicitly |
| 5 | Coordinator submitted with `--mem=XG` (sbatch) | Propagates `SLURM_MEM_PER_NODE` to all child jobs via `--export=ALL` | Use `--mem-per-cpu` for coordinator; add `unset SLURM_MEM_PER_NODE` in submit script |
| 6 | `--singularity-args` in profile (with `--` prefix) | Key not recognized; bind mounts silently missing | Use `singularity-args:` (no `--` prefix) in profile YAML |
| 7 | `software-deployment-method: apptainer` | Wraps ALL rules in apptainer, breaks rules without container directive | Only use when ALL rules have `container:` or `singularity:` directives |
| 8 | Stale lock after killed coordinator | `Error: Directory cannot be locked` | `snakemake --unlock` then resubmit with `--rerun-incomplete` |
| 9 | `--profile` path resolved relative to `--directory` | Profile not found when workflow and experiment are in different dirs | Always pass `--profile` as absolute path |
| 10 | `sacctmgr: not found` when running snakemake on login node | SLURM executor tries account validation but SLURM CLI not in PATH | Submit coordinator as SLURM batch job, not direct CLI on login node |
| 11 | `run:` block executes in coordinator, not on compute node | Missing dependencies or runs single-threaded | Use `run:` only for lightweight cohort-level steps |
| 12 | Rule without `singularity:` directive but workflow uses containers | Rule runs bare on compute node; `ModuleNotFoundError` | Add `singularity: IMG` to every rule needing container packages |
