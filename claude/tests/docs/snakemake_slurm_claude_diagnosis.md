# Why Claude Code Cannot Run Snakemake + SLURM (But You Can)
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: 2026-02-26
# Purpose: Diagnose the structural reasons Claude Code fails at interactive Snakemake/SLURM runs
#          and document solutions for each failure mode.

---

## Executive Summary

The same `snakemake -s ... --workflow-profile .../slurm` command works fine when you run it in
your terminal but fails (or produces unreliable results) when Claude Code runs it via its Bash
tool. There are **five distinct root causes**, ranked by severity.

---

## Failure Mode 1 — Bash Tool Timeout Kills the Snakemake Coordinator (CRITICAL)

### What happens

Claude Code's `Bash` tool has a **default 2-minute (120,000 ms) hard timeout**. After that,
it kills the foreground process and returns.

Snakemake with the SLURM executor is a **long-running coordinator process** that must stay alive
to:
1. Submit jobs via `sbatch`
2. Poll `squeue` every second for job status
3. Wait up to `latency-wait: 360` (6 minutes!) for output files to appear on the filesystem
4. Trigger downstream rules after each job completes

**Timeline from the actual test run (job 11633473, 2026-02-26):**
```
09:32:35 — Snakemake coordinator starts
09:32:35 — sbatch submits job 11633473
09:33:15 — SLURM job completes (40 seconds of actual execution)
~09:33:15–09:39:15 — latency-wait could hold coordinator open up to 6 more minutes
09:33:15 — (this run finished early; filesystem was fast)
```

For this trivial BED-sort test, total wall time was ~40 seconds — just within the 2-minute
default. But:
- Any real analysis job (alignment, basecalling, DESeq2) runs for minutes to hours
- `latency-wait: 360` means even finished jobs hold the coordinator open for up to 6 minutes
- When the timeout fires, the coordinator process is **SIGKILLed mid-run**

### What happens after the timeout kills the coordinator

1. The SLURM job on the compute node **continues running** (SLURM doesn't know the coordinator died)
2. The coordinator never collects the job's exit status
3. Output files may or may not be written
4. Snakemake leaves a **stale lock file** in `.snakemake/locks/`
5. The next run fails immediately: `Error: Directory is locked`
6. Downstream rules never trigger, even if the killed rule produced valid output

### Evidence

```
# From environment diagnostics (2026-02-26):
# Bash tool default timeout = 120,000 ms (2 minutes)
# latency-wait = 360 seconds (profile config)
# This test took 40s — barely within 2 min for trivial jobs only
```

---

## Failure Mode 2 — Claude Code Runs Inside an Apptainer Container (IMPORTANT CONTEXT)

### What the environment shows

```
APPTAINER_CONTAINER=/data1/greenbab/software/images/claude_gemini_container_latest.sif
SLURM_JOBID=11625844  (interactive job, partition=interactive)
SLURM_EXPORT_ENV=NONE
```

Claude Code is already running:
- **Inside** an Apptainer container (`sclaude()` wrapper)
- **Inside** an interactive SLURM job (job 11625844 on node iscc001)

When Snakemake submits via `sbatch`, the new jobs run on compute nodes **outside the container**.
This creates an asymmetry:

| Context | Environment | Working directory |
|---------|-------------|-------------------|
| Claude Code / coordinator | Inside container, interactive SLURM job | `/data1/greenbab/users/ahunos/apps/llm_configs` |
| SLURM compute job | Outside container, fresh batch environment | Inherits from coordinator's sbatch call |

### The `SLURM_EXPORT_ENV=NONE` propagation

The interactive job that runs Claude Code was submitted with `SLURM_EXPORT_ENV=NONE`.
This setting **propagates to child sbatch submissions**. Any job submitted from Claude Code's
shell inherits this constraint: the compute node job starts with a minimal environment (no
inherited PATH, no conda activation, etc.).

Snakemake's executor plugin handles this by embedding the full Python invocation path in the
sbatch script, so conda tools do get found. But any tool that relies on inherited environment
variables (e.g., `APPTAINER_CACHEDIR`, `SINGULARITY_BIND`, or custom `PATH` entries) will be
**missing** on the compute node.

### Why it works when you run it yourself

When you run the command in your own terminal:
- You are NOT inside an Apptainer container
- You are on the login node (or an interactive session you started intentionally)
- Your `~/.bashrc` sets up PATH, conda, etc.
- `SLURM_EXPORT_ENV` is not set (or is set to `ALL`), so your environment propagates
- The coordinator process lives as long as your terminal session

---

## Failure Mode 3 — Working Directory Ambiguity

### The problem

The Snakefile uses a **relative output path**:
```python
OUTPUT_BED = "mm10.mm10.L1_recent_profile.sorted.bed"
```

When Snakemake is called without `--directory`, it uses the shell's current working directory
as the run directory. This is where all relative paths resolve and where `.snakemake/` is created.

**Claude Code's Bash tool working directory** = wherever Claude Code was launched, typically:
```
/data1/greenbab/users/ahunos/apps/llm_configs
```

**Your terminal working directory** when you ran it = `claude/tests/` (confirmed by the output
file location in git status: `claude/tests/mm10.mm10.L1_recent_profile.sorted.bed`).

If Claude Code runs from its own CWD, the output lands at:
```
/data1/greenbab/users/ahunos/apps/llm_configs/mm10.mm10.L1_recent_profile.sorted.bed
                                                ^^^^ WRONG PLACE
```

And `.snakemake/` gets created there too, scattering metadata across the repo.

### Fix

Always pass `--directory` explicitly when using an absolute `-s` path:
```bash
snakemake -s /abs/path/Snakefile \
  --workflow-profile /abs/path/profile \
  --directory /data1/greenbab/users/ahunos/apps/llm_configs/claude/tests
```

---

## Failure Mode 4 — `use-singularity: true` Without Per-Rule Container Directives

### Current profile setting

```yaml
use-singularity: true
singularity-args: "--bind /data1/greenbab/,/data1/collab001/"
```

### The problem

`use-singularity: true` tells Snakemake to run rules inside containers. But the `sort_bed` rule
has **no `singularity:` or `container:` directive**. This creates ambiguity:

- Snakemake 9 + `use-singularity: true` without a per-rule container means the rule runs natively
  (no container wrapping). This is actually fine for this test.
- BUT if `software-deployment-method: apptainer` is ever added to the profile, Snakemake wraps
  ALL rules in `apptainer exec` regardless of whether a container is specified. This breaks rules
  without a `container:` directive.
- Running from INSIDE a container + `use-singularity: true` = potential nested Apptainer
  invocations for any rule that DOES specify a container.

The test works now because `sort_bed` has no container directive. Remove `use-singularity: true`
from profiles where no rules need containers.

---

## Failure Mode 5 — `latency-wait: 360` is Excessively High

### Current setting

```yaml
latency-wait: 360
```

This tells Snakemake to wait **up to 6 minutes** after a SLURM job completes before deciding
the output file is missing. On a well-functioning NFS mount, files appear within 5-30 seconds.
360 seconds is a 6-minute worst-case buffer that was originally designed for very slow NFS or
Lustre mounts.

Combined with failure mode 1 (timeout), this setting is catastrophic: even if a job finishes
in 30 seconds, the coordinator holds open for potentially 6+ minutes waiting to confirm the
output exists.

**Recommended value**: 60–120 seconds for `/data1/greenbab` NFS.

---

## Solutions

### Solution 1 (RECOMMENDED): Submit Snakemake Itself as a SLURM Job

The cleanest fix. Instead of running the Snakemake coordinator interactively (blocking Claude
Code's Bash tool), wrap it in an `sbatch` script. The coordinator runs as its own SLURM job on
a dedicated login/head node and lives until the pipeline completes.

**Script**: `claude/tests/scripts/workflows/wf_snakemake/submit_snakemake.sh`

This is the pattern used in production pipelines everywhere. Claude Code can:
1. Submit the job via `sbatch submit_snakemake.sh`
2. Get back a job ID immediately (non-blocking)
3. Use `squeue -j <jobid>` or the SLURM MCP to monitor progress
4. Read the log file to check results

### Solution 2: Use `run_in_background=True` + Explicit Long Timeout

For Claude Code's Bash tool: run snakemake in background and check log file.

```python
# Claude Code Bash tool call
Bash(
    command="cd /path/to/tests && nohup snakemake -s ... --workflow-profile ... > snakemake_run.log 2>&1 & echo PID:$!",
    run_in_background=True,
    timeout=600000  # 10 minutes
)
```

Then follow with `tail -f snakemake_run.log` to monitor.

### Solution 3: Fix the Profile Config

1. Reduce `latency-wait` from 360 to 60
2. Remove `use-singularity: true` from profiles where no rules use containers
3. Always use `--directory` when invoking with absolute `-s` path

### Solution 4: Use the SLURM MCP Tool (Claude Code Native)

Claude Code has access to SLURM MCP tools. The correct workflow is:
```
slurm_submit_job(
    wrap="cd /path/to/tests && snakemake -s /abs/Snakefile --workflow-profile /abs/profile --cores 1",
    job_name="snakemake_coordinator",
    partition="componc_cpu",
    time="04:00:00",
    ...
)
```
Then use `slurm_job_status(job_id=...)` and `slurm_job_logs(job_id=...)` to monitor.

---

## Quick Reference: Which Situation Uses Which Fix

| Situation | Recommended fix |
|-----------|-----------------|
| Claude Code running any Snakemake pipeline | Solution 1 or Solution 4 |
| Short test runs (<90s total) | Solution 2 with explicit timeout |
| Production analysis pipelines | Solution 1 (always) |
| Fix a currently broken run (stale lock) | `snakemake --unlock` then re-submit |
| Working directory is wrong | Add `--directory /abs/path` |

---

## Failure Mode 6 — Coordinator `--mem` Propagates `SLURM_MEM_PER_NODE` Into Rule Jobs (CONFIRMED BUG)

### What happens

When the coordinator sbatch script is submitted with `#SBATCH --mem=4G`, SLURM sets
`SLURM_MEM_PER_NODE` in the coordinator job's environment. When snakemake-executor-plugin-slurm
then submits rule jobs using `sbatch --mem-per-cpu=2000`, SLURM sets `SLURM_MEM_PER_CPU=2000`
for those jobs. Because `sbatch` inherits the caller's environment (default `--export=ALL`),
the rule job's environment contains **both** `SLURM_MEM_PER_NODE` (inherited) and
`SLURM_MEM_PER_CPU` (from job allocation). When snakemake's worker calls `srun` to execute
the rule shell, `srun` sees the conflict and fatally exits:

```
srun: fatal: SLURM_MEM_PER_CPU, SLURM_MEM_PER_GPU, and SLURM_MEM_PER_NODE are mutually exclusive.
```

### Why this only happens with the wrapper (not your terminal runs)

When you run snakemake interactively from your terminal (a login node or interactive session
without `--mem` overhead), `SLURM_MEM_PER_NODE` is not set in the coordinator's environment.
The conflict never arises. The wrapper script introduced this by using `#SBATCH --mem=4G`.

### Fix (applied)

1. Submit the coordinator with `#SBATCH --mem-per-cpu=4000` instead of `#SBATCH --mem=4G`.
   This sets `SLURM_MEM_PER_CPU` in the coordinator env (consistent with rule jobs), never
   `SLURM_MEM_PER_NODE`.
2. Add `unset SLURM_MEM_PER_NODE` at the top of the coordinator script as a safety net for
   cases where the session that calls `sbatch submit_snakemake.sh` itself has `SLURM_MEM_PER_NODE`
   set.

### Live test result (2026-02-26)

- **First run** (before fix): job 11635449 failed with `srun` memory conflict
- **Second run** (after fix): coordinator job 11635669 → rule job 11635671 → **COMPLETED 0:0**,
  wall time 53s, output `mm10.mm10.L1_recent_profile.sorted.bed` (7.5 MB) correct.

---

## The Three Things to Always Do When Running Snakemake from Claude Code

```bash
# 1. Always set --directory explicitly
--directory /abs/path/to/experiment_dir

# 2. Never run the coordinator as a blocking foreground process
#    Use sbatch wrapper OR nohup background OR SLURM MCP

# 3. After any Claude-killed run, always unlock before retry
snakemake --unlock -s /abs/Snakefile --workflow-profile /abs/profile \
          --directory /abs/experiment_dir
```
