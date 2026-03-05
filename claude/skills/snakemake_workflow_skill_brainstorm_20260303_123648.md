# Snakemake Workflow Skill — Brainstorm (v2)
# Date: 2026-03-03 (updated 2026-03-05)
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Purpose: Design document for a Claude Code skill that encodes best practices
#          for creating, debugging, and running Snakemake workflows on SLURM HPC.
# Scope: Snakemake-only (Nextflow is a separate skill if needed later)

---

## 1. Skill Trigger

When the user asks to:
- Create/write/build a Snakemake workflow or pipeline
- Debug a Snakemake error or failed SLURM job
- Add rules to an existing Snakefile
- Write or fix a SLURM profile for Snakemake
- Organize pipeline outputs or run directories
- Convert a shell script / ad-hoc analysis into a reproducible workflow

**When NOT to trigger** (anti-scope):
- If the task has <3 steps, no per-sample parallelism, and no dependency DAG — a bash script is better. Snakemake overhead isn't free.
- Pure Nextflow workflows (separate skill)
- One-off data exploration (Jupyter notebook or standalone script is better)

---

## 2. Core Principles

### P1. Leverage community-validated workflows
- Check nf-core, snakemake-workflows catalog, and bioconda before writing from scratch
- Wrap existing tools (modkit, samtools, bedtools, STAR, etc.) — don't reimplement their logic
- When wrapping, match the tool's exact CLI — don't invent wrapper abstractions

### P2. Modular workflows always win
- One rule = one tool/operation
- Optional rule blocks gated by config booleans: `if USE_AGGREGATE:`, `if USE_TENSOR:`
- Rules compose vertically: each downstream rule declares its dependency via `input:`
- New features are additive — adding a rule should never break existing rules

### P3. Externalize complex logic; keep simple commands inline
- Shell one-liners and short pipelines are fine inline: `awk '{print "chr"$0}'`, `bgzip && tabix`, etc.
- **Externalize when**: the shell block needs `if/for/while` logic, variable manipulation, multi-step Python processing, or would benefit from standalone testing
- External scripts go under `workflow_dir/scripts/` with argparse CLI so they're testable standalone
- Reference via `os.path.join(workflow.basedir, "scripts", "my_script.py")`
- Never inline complex Python in `run:` blocks for rules that get submitted to SLURM — use `shell:` calling a script instead (the `run:` block executes in the coordinator process, not on the compute node)
- **Rule of thumb**: if you can't understand the shell block in 10 seconds, externalize it

### P4. Validate before every submission
- `snakemake --lint` catches style issues and anti-patterns
- `snakemake -n` (dry-run) validates the full DAG without running anything
- `snakemake --dag | dot -Tpdf > dag.pdf` visualizes the DAG — use this when debugging rule dependencies or explaining workflow structure
- Always dry-run after any Snakefile edit — catches missing inputs, circular dependencies, typos
- Dry-run is the minimum test; a small-data end-to-end test is preferred (see P10)

### P5. Separate workflow (code) from results
- Workflow code (Snakefile, scripts/, profiles/) is versioned and reusable
- Never write outputs into the workflow directory
- The workflow is a **tool**; each run is an **experiment**
- Workflow directory structure:
  ```
  workflows/{workflow_name}/
  ├── Snakefile
  ├── config_template.yaml        # Documented template — copy for each run
  ├── scripts/                    # Pluggable scripts called by rules
  │   ├── aggregate_regions.py
  │   ├── build_tensor.py
  │   └── plot_correlation.py
  ├── profiles/slurm/config.yaml  # Workflow-specific SLURM profile
  ├── test/                       # Test fixtures (see P10)
  │   ├── test_config.yaml
  │   ├── test_manifest.tsv
  │   └── test_regions.bed        # Small subset (~10-100 loci)
  └── CHANGELOG.md                # Version history (see P12)
  ```

### P6. Output directory = the run root (results + reproducibility metadata)
- One `output_dir` config key — this is the **run root**, not just the results directory
- All subdirectories derived internally in the Snakefile:
  ```python
  OUTDIR     = config["output_dir"]
  RESULTSDIR = os.path.join(OUTDIR, "results")
  LOGDIR     = os.path.join(OUTDIR, "logs")
  BENCHDIR   = os.path.join(OUTDIR, "benchmarks")
  QCDIR      = os.path.join(OUTDIR, "qc")
  ```
- Never add separate `figures_dir`, `log_dir`, `matrix_dir` config keys — separate keys allow paths to diverge
- **Run root structure**:
  ```
  {output_dir}/                              # = outputs/v1_mm10_DMSO_L1/ (the run root)
  ├── config.yaml                            # COPY of config used (frozen at run start)
  ├── run_snakemake.sh                       # Exact command to reproduce the run
  ├── manifest.tsv                           # COPY of sample sheet used
  ├── run_metadata.yaml                      # Auto-generated: snakemake version, image hash, date, git commit
  ├── results/                               # ALL rule outputs go here
  │   ├── {rule_name}/{sample}/{outputs}     # Per-sample rule outputs grouped by rule
  │   │   ├── modkit_pileup/
  │   │   │   ├── sample_A/sample_A.modkit_pileup.bedmethyl.gz
  │   │   │   ├── sample_A/sample_A.modkit_pileup.bedmethyl.gz.tbi
  │   │   │   └── sample_A/sample_A.modkit_pileup_perRegion.tsv
  │   │   └── ...
  │   ├── cohort_matrices/                   # Cross-sample aggregations
  │   │   ├── cohort_mean_methylation_matrix.tsv
  │   │   ├── cohort_weighted_mean_methylation_matrix.tsv
  │   │   └── dname_rna_tensor/
  │   │       ├── DNAme_RNA_tensor.npy
  │   │       ├── tensor_loci.txt
  │   │       ├── tensor_samples.txt
  │   │       └── correlation/
  │   │           ├── per_locus_correlation.tsv
  │   │           └── figures/{png,pdf,svg}/
  │   └── ref/                               # Copied/generated reference files
  ├── benchmarks/                            # benchmark: directive outputs (per-rule resource usage)
  │   ├── modkit_pileup_sample_A.tsv
  │   └── aggregate_sample_A.tsv
  ├── qc/                                    # QC gate outputs
  │   └── modkit_pileup_flagstat_{sample}.tsv
  └── logs/                                  # ALL rule logs
      ├── modkit_pileup_sample_A.log
      ├── aggregate_sample_A.log
      └── build_cohort_matrices.log
  ```
- **Key insight**: One run = one directory. The config, manifest, run script, and metadata travel with the results. Independently archivable (`tar -czf`) and deletable (`rm -rf`) with zero ambiguity.
- **Separation**: `config.yaml` and `run_snakemake.sh` live at the run root (reproducibility layer). Actual data products live under `results/`. This means you can `ls results/` to see only data, or `ls .` to see the full run context.

### P7. Config is the run manifest
- Config filename matches the run: `config.mm10_DMSO_LINE1.yaml`
- All cohort-specific details (paths, regex patterns, sample ID formats, exclusion keywords) are config args, never hardcoded
- This enables reuse across cohorts without code changes
- Config documents itself: use comments to explain each key

### P8. Use Snakemake's built-in resource management features
- **`benchmark:`** — track walltime, memory, CPU per rule. Use on every computationally non-trivial rule. Benchmark data from test runs informs production `set-resources` values.
  ```python
  rule modkit_pileup:
      benchmark:
          os.path.join(BENCHDIR, "modkit_pileup_{sample}.tsv")
      ...
  ```
- **`temp()`** — mark intermediate files for automatic cleanup after all downstream rules complete. Critical for ONT workflows where intermediate BAMs/bedmethyls eat disk.
  ```python
  output:
      temp_bed = temp(os.path.join(RESULTSDIR, "ref", "regions_chrPrefixed.bed")),
  ```
- **`protected()`** — prevent accidental deletion of expensive outputs (e.g., final cohort matrices after a 42-sample run).
  ```python
  output:
      matrix = protected(os.path.join(RESULTSDIR, "cohort_matrices", "cohort_methylation_matrix.tsv")),
  ```
- **`retries:`** — per-rule retry count for transient SLURM failures (node timeout, NFS hiccup). Set on rules that call external tools but NOT on rules with logic bugs (those should fail fast).
  ```python
  rule modkit_pileup:
      retries: 2   # transient SLURM failures
      ...
  ```
- **`resources:`** — define custom resource constraints to throttle rules (e.g., limit concurrent disk-heavy jobs).

### P9. QC gates as explicit workflow steps
- QC checks should be **Snakemake rules**, not informal post-hoc steps
- A QC rule reads metrics from upstream output and fails explicitly if thresholds are not met
- QC outputs go to `{output_dir}/qc/` and serve as both validation records and DAG dependencies
- Pattern: QC rule produces a `.pass` sentinel file; downstream rules depend on it
  ```python
  rule qc_alignment:
      """Fail if mapping rate < 80% for any sample."""
      input:
          flagstat = os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.flagstat"),
      output:
          qc_pass = os.path.join(QCDIR, "alignment_{sample}.pass"),
      run:
          import re
          with open(input.flagstat) as f:
              text = f.read()
          mapped_pct = float(re.search(r"(\d+\.\d+)% mapped", text).group(1))
          if mapped_pct < 80.0:
              raise ValueError(f"QC FAIL: {wildcards.sample} mapping rate {mapped_pct}% < 80%")
          with open(output.qc_pass, "w") as f:
              f.write(f"PASS: mapping_rate={mapped_pct}%\n")

  rule downstream_analysis:
      input:
          bam = ...,
          qc = os.path.join(QCDIR, "alignment_{sample}.pass"),  # gate
      ...
  ```
- **When to gate**: After alignment (mapping rate), after pileup (expected chromosomes, coverage), after DMR calling (count sanity check). Match the QC checkpoints from the CLAUDE.md domain playbooks.
- **When NOT to gate**: Don't gate on warnings or soft thresholds — those should be logged and reported, not workflow-blocking.

### P10. Every workflow ships with a test suite
- A `test/` directory inside the workflow with:
  - `test_config.yaml` — points to toy data, minimal sample count (1-4 samples)
  - `test_manifest.tsv` — subset of real samples or synthetic test samples
  - `test_regions.bed` — small region file (~10-100 loci) for fast execution
- **Test runs must complete in <5 minutes on cpushort**
- When to test: after any Snakefile edit, before production submission
- The test config uses slurmMinimal profile
- Test validation: dry-run + full end-to-end with the test config
- Test fixtures are version-controlled alongside the workflow code

### P11. Incremental sample addition
- Adding new samples to `sample_manifest` → only new per-sample rules execute (Snakemake handles this automatically via output file checking)
- **Problem**: Cohort-level rules (matrices, tensor, correlation) won't re-trigger because their inputs are `expand(...)` over `SAMPLE_IDS` — Snakemake sees the expand list changed and will re-run them. However, if you've added samples but the old per-sample outputs are still present, only the new per-sample rules run + all cohort rules re-run. This is the correct behavior.
- **Gotcha**: If you rename the output_dir for a new run, ALL rules re-run (no prior outputs). Use the same output_dir when adding samples to an existing cohort.
- **Force cohort re-run only**: `snakemake --forcerun build_cohort_matrices` — re-runs cohort rules without re-running per-sample rules.

### P12. Version and changelog discipline
- **Workflow versioning**: Tag workflow releases with `{workflow_name}-v{major}.{minor}` (e.g., `ont_modkit_pileup-v1.2`)
- **CHANGELOG.md** in the workflow directory:
  ```markdown
  # Changelog — ont_modkit_pileup

  ## v1.2 (2026-03-05)
  - Added benchmark: directive to all compute rules
  - Added QC gate for modkit pileup coverage
  - Fixed: temp() wrapper on chr-prefixed BED to save disk

  ## v1.1 (2026-03-01)
  - Added RNA tensor + correlation plotting rules
  - Added --bgzf + tabix indexing in modkit_pileup rule

  ## v1.0 (2026-02-25)
  - Initial release: convert_bed, modkit_pileup, aggregate, cohort_matrices
  ```
- **Container pinning**: Never use `:latest` tags. Always pin exact versions (e.g., `onttools_v3.9.sif`). Record the image path in the run config. If the image is rebuilt, bump the tag version.
- **Run metadata rule**: Auto-generate `run_metadata.yaml` at the start of each run:
  ```python
  rule write_run_metadata:
      output:
          os.path.join(OUTDIR, "run_metadata.yaml"),
      params:
          img = IMG,
      run:
          import datetime, shutil
          meta = {
              "date": datetime.datetime.now().isoformat(),
              "snakemake_version": workflow.snakemake_version if hasattr(workflow, "snakemake_version") else "unknown",
              "container_image": params.img,
              "config_file": workflow.configfiles[0] if workflow.configfiles else "unknown",
              "output_dir": OUTDIR,
              "n_samples": len(SAMPLE_IDS),
              "sample_ids": SAMPLE_IDS,
          }
          import yaml
          os.makedirs(os.path.dirname(output[0]), exist_ok=True)
          with open(output[0], "w") as f:
              yaml.dump(meta, f, default_flow_style=False)
  ```

### P13. Error tolerance: retries vs fail-fast
- **Transient failures** (node timeout, NFS hiccup, SLURM preemption): `retries: 2` on the rule
- **Deterministic failures** (bad input, code bug, missing dependency): `retries: 0` (fail fast)
- **Rule-level guidance**:
  | Rule type | Retries | Reasoning |
  |-----------|---------|-----------|
  | External tool (modkit, samtools, STAR) | 2 | SLURM nodes can timeout or OOM transiently |
  | Python script (aggregate, tensor, plot) | 0 | Code bugs should fail immediately |
  | File conversion (awk, bgzip, tabix) | 1 | Rare NFS issues |
  | QC gate rules | 0 | QC failures are data issues, not transient |
- **Profile-level**: slurmMinimal uses `keep-going: true` (continue past failures to see full picture). slurmConfig uses no `keep-going` (fail explicitly in production — one bad sample shouldn't silently propagate).

---

## 3. Snakemake 9 + SLURM Pitfalls (battle-tested)

| # | Pitfall | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Built-in `mem_mb: 1000` conflicts with `mem_mb_per_cpu` | `SLURM_MEM_PER_NODE` vs `SLURM_MEM_PER_CPU` fatal error | Add `mem_mb: 0` to `default-resources` in every profile |
| 2 | `mem:` in profile sets `SLURM_MEM_PER_NODE` | Same fatal conflict with any `mem_mb_per_cpu` | Never use `mem:` — always use `mem_mb_per_cpu` |
| 3 | Missing `slurm_account` in default-resources | Silent job rejection (no error in Snakemake log) | Always set `slurm_account: "greenbab"` in `default-resources` |
| 4 | `use-singularity: true` in profile doesn't propagate to child SLURM jobs | Jobs run without container; tools not found or wrong Python | Pass `--use-singularity` on the coordinator CLI explicitly |
| 5 | Coordinator submitted with `--mem=XG` (sbatch) | Propagates `SLURM_MEM_PER_NODE` to all child jobs via `--export=ALL` | Use `--mem-per-cpu` for coordinator; add `unset SLURM_MEM_PER_NODE` in submit script |
| 6 | `--singularity-args` in profile (with `--` prefix) | Key not recognized; bind mounts silently missing | Use `singularity-args:` (no `--` prefix) in profile YAML |
| 7 | `software-deployment-method: apptainer` | Wraps ALL rules in apptainer, breaks rules without container directive | Only use when ALL rules have `container:` or `singularity:` directives; omit entirely for conda-based pipelines |
| 8 | Stale lock after killed coordinator | `Error: Directory cannot be locked` | `snakemake --unlock` then resubmit with `--rerun-incomplete` |
| 9 | `--profile` path resolved relative to `--directory` | Profile not found when workflow and experiment are in different directories | Always pass `--profile` as absolute path |
| 10 | `sacctmgr: not found` when running snakemake on login node | SLURM executor tries account validation but SLURM CLI not in PATH | Submit coordinator as SLURM batch job, not direct CLI on login node |
| 11 | `run:` block executes in coordinator, not on compute node | Missing dependencies (e.g., pandas not on coordinator) or runs single-threaded | Use `run:` only for lightweight cohort-level steps; use `shell:` + external script for heavy work |
| 12 | Rule without `singularity:` directive but workflow uses containers | Rule runs bare on compute node; `ModuleNotFoundError` for pandas/numpy/etc. | Add `singularity: IMG` to every rule that needs container packages |

---

## 4. SLURM Profile Templates

### 4a. Dev/Testing Profile (slurmMinimal)
```yaml
# Short queues, minimal resources, tolerant of failures
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

### 4b. Production Profile (slurmConfig)
```yaml
# Generous resources, strict failure handling
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

### 4c. Workflow-Specific Profile (per-workflow)
```yaml
# Minimal profile for a specific workflow (e.g., ont_modkit_pileup)
# Only overrides rules that exist in THIS workflow
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

**Note on profile selection**: Default to slurmMinimal for development/testing. Use slurmConfig for production runs. Sample count alone doesn't determine this — 4 large ONT BAMs can require production-level resources.

---

## 5. Snakefile Template

```python
"""
{workflow_name} — {one-line description}
Author: Samuel Ahuno (ekwame001@gmail.com)
Date: {date}
"""

import os
import pandas as pd

# ===========================================================================
# Config
# ===========================================================================
OUTDIR     = config["output_dir"]
RESULTSDIR = os.path.join(OUTDIR, "results")
LOGDIR     = os.path.join(OUTDIR, "logs")
BENCHDIR   = os.path.join(OUTDIR, "benchmarks")
QCDIR      = os.path.join(OUTDIR, "qc")
REF        = config["ref_fasta"]
IMG        = config["img"]

# Optional features (gated by config presence)
OPTIONAL_SCRIPT = config.get("optional_script", None)
USE_OPTIONAL    = OPTIONAL_SCRIPT is not None

# Validation
if USE_OPTIONAL and not config.get("required_prereq"):
    raise ValueError(
        "Config error: 'optional_script' requires 'required_prereq' to be set."
    )

# ===========================================================================
# Sample manifest
# ===========================================================================
manifest = pd.read_csv(config["sample_manifest"], sep="\t")
SAMPLE_IDS = manifest["sample"].tolist()

# Helper functions
def get_bam(wildcards):
    row = manifest.loc[manifest["sample"] == wildcards.sample].iloc[0]
    return str(row["bam_path"])

# ===========================================================================
# Targets
# ===========================================================================
_targets = [
    # Run metadata (always generated)
    os.path.join(OUTDIR, "run_metadata.yaml"),
] + expand(
    os.path.join(RESULTSDIR, "rule_a", "{sample}", "{sample}.output.gz"),
    sample=SAMPLE_IDS,
)

if USE_OPTIONAL:
    _targets += [os.path.join(RESULTSDIR, "optional_output", "result.tsv")]


rule all:
    input:
        _targets,


# ===========================================================================
# Rule: run metadata (always runs first)
# ===========================================================================
rule write_run_metadata:
    """Auto-generate run metadata for reproducibility."""
    output:
        os.path.join(OUTDIR, "run_metadata.yaml"),
    params:
        img = IMG,
    run:
        import datetime, yaml
        meta = {
            "date": datetime.datetime.now().isoformat(),
            "container_image": params.img,
            "config_file": workflow.configfiles[0] if workflow.configfiles else "unknown",
            "output_dir": OUTDIR,
            "n_samples": len(SAMPLE_IDS),
            "sample_ids": SAMPLE_IDS,
        }
        os.makedirs(os.path.dirname(output[0]), exist_ok=True)
        with open(output[0], "w") as f:
            yaml.dump(meta, f, default_flow_style=False)


# ===========================================================================
# Rule: rule_a (per-sample)
# ===========================================================================
rule rule_a:
    """One-line description of what this rule does."""
    input:
        bam=get_bam,
        ref=REF,
    output:
        out=os.path.join(RESULTSDIR, "rule_a", "{sample}", "{sample}.output.gz"),
    log:
        os.path.join(LOGDIR, "rule_a_{sample}.log"),
    benchmark:
        os.path.join(BENCHDIR, "rule_a_{sample}.tsv")
    singularity:
        IMG
    retries: 2    # transient SLURM failures
    threads: 8
    params:
        extra_flag="--some-flag" if config.get("use_flag", False) else "",
    shell:
        """
        (
        echo "$(date '+%Y-%m-%d %H:%M:%S') === rule_a: {wildcards.sample} ==="
        tool_name \
            --input {input.bam} \
            --ref {input.ref} \
            --output {output.out} \
            --threads {threads} \
            {params.extra_flag}
        echo "$(date '+%Y-%m-%d %H:%M:%S') Done: {output.out}"
        ) &> {log}
        """


# ===========================================================================
# Rule: QC gate (per-sample, depends on rule_a)
# ===========================================================================
rule qc_rule_a:
    """Validate rule_a output meets quality thresholds."""
    input:
        out=os.path.join(RESULTSDIR, "rule_a", "{sample}", "{sample}.output.gz"),
    output:
        qc_pass=os.path.join(QCDIR, "rule_a_{sample}.pass"),
    log:
        os.path.join(LOGDIR, "qc_rule_a_{sample}.log"),
    retries: 0    # QC failures are data issues, not transient
    run:
        # Example: check file is non-empty and meets a threshold
        import os as _os
        size = _os.path.getsize(input.out)
        if size < 100:
            raise ValueError(f"QC FAIL: {wildcards.sample} output too small ({size} bytes)")
        with open(output.qc_pass, "w") as f:
            f.write(f"PASS: file_size={size}\n")


# ===========================================================================
# Rule: optional_step (conditional, cohort-level)
# ===========================================================================
if USE_OPTIONAL:
    rule optional_step:
        """Only runs when optional_script is set in config."""
        input:
            files=expand(
                os.path.join(RESULTSDIR, "rule_a", "{sample}", "{sample}.output.gz"),
                sample=SAMPLE_IDS,
            ),
            qc=expand(
                os.path.join(QCDIR, "rule_a_{sample}.pass"),
                sample=SAMPLE_IDS,
            ),
        output:
            result=os.path.join(RESULTSDIR, "optional_output", "result.tsv"),
        log:
            os.path.join(LOGDIR, "optional_step.log"),
        benchmark:
            os.path.join(BENCHDIR, "optional_step.tsv")
        singularity:
            IMG
        retries: 0    # Script logic — fail fast
        params:
            script=os.path.join(workflow.basedir, "scripts", "optional_script.py"),
            out_dir=os.path.join(RESULTSDIR, "optional_output"),
        shell:
            """
            (
            echo "$(date '+%Y-%m-%d %H:%M:%S') === optional_step ==="
            python3 {params.script} \
                --input-dir {RESULTSDIR}/rule_a \
                --output-dir {params.out_dir}
            echo "$(date '+%Y-%m-%d %H:%M:%S') Done."
            ) &> {log}
            """
```

---

## 6. Script Interface Convention

Every pluggable script under `scripts/` follows this pattern:

```python
#!/usr/bin/env python3
"""
{script_name} — {one-line description}

Author: Samuel Ahuno (ekwame001@gmail.com)
Date: {date}

Usage:
    python3 {script_name}.py \\
        --input  <input_file> \\
        --output <output_file> \\
        --sample-id <sample_name> \\
        [--extra-arg value]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def log(msg):
    """Print timestamped message to stdout (captured by Snakemake &> {log})."""
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--input", required=True, help="...")
    parser.add_argument("--output", required=True, help="...")
    parser.add_argument("--sample-id", default="unknown", help="...")
    args = parser.parse_args()

    log(f"=== {Path(__file__).stem} ===")
    log(f"input:     {args.input}")
    log(f"output:    {args.output}")
    log(f"sample_id: {args.sample_id}")

    # ... processing ...

    # Handle gzip transparently
    import gzip
    opener = gzip.open if args.input.endswith(".gz") else open
    with opener(args.input, "rt") as fh:
        pass  # read data

    # ... save output ...

    log(f"=== DONE: {Path(__file__).stem} completed successfully ===")


if __name__ == "__main__":
    main()
```

**Key conventions:**
- argparse with `--help` for all arguments
- Timestamped log messages to stdout (captured by Snakemake `&> {log}`)
- Ends with `"=== DONE: script_name completed successfully ==="` — if this line is missing from the log, the script crashed
- Handles gzip transparently: `gzip.open if path.endswith(".gz") else open`
- Uses `"rt"` mode for gzip (text mode, not bytes)
- Validates input files exist before processing
- Uses `pd.read_csv(..., na_values=["NA"])` and `dropna()` — never string comparison with "NA"

---

## 7. Run Script Template (`run_snakemake.sh`)

```bash
#!/usr/bin/env bash
# run_snakemake.sh — Reproduce this workflow run
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: {date}
#
# Usage:
#   bash run_snakemake.sh        # execute
#   bash run_snakemake.sh -n     # dry-run
#   bash run_snakemake.sh --forcerun rule_name  # force-rerun a specific rule

set -euo pipefail

# Prevent SLURM memory variable conflicts when coordinator is an sbatch job
unset SLURM_MEM_PER_NODE

export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache

SNAKEFILE="/abs/path/to/workflows/{workflow_name}/Snakefile"
CONFIGFILE="$(dirname "$0")/config.yaml"
PROFILE="/abs/path/to/workflows/{workflow_name}/profiles/slurm"

snakemake \
    --snakefile "$SNAKEFILE" \
    --configfile "$CONFIGFILE" \
    --workflow-profile "$PROFILE" \
    --use-singularity \
    --singularity-args "--bind /data1/greenbab/,/data1/collab001/" \
    --rerun-incomplete \
    --jobs 4 \
    "$@"
```

**Key conventions:**
- `unset SLURM_MEM_PER_NODE` at the top prevents the coordinator's memory setting from propagating to child jobs
- `CONFIGFILE` is relative to the script location (`$(dirname "$0")/...`) so it works from any directory
- `SNAKEFILE` and `PROFILE` are absolute paths (workflow code lives elsewhere)
- `"$@"` passes extra flags (like `-n`, `--forcerun`, `--until`)
- `APPTAINER_CACHEDIR` avoids home directory quota issues on compute nodes

---

## 8. Config Template Convention

```yaml
# config_template.yaml — {workflow_name}
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: {date}
#
# Usage:
#   1. Copy to your run directory:
#        mkdir -p outputs/{run_name} && cp config_template.yaml outputs/{run_name}/config.yaml
#   2. Fill in REQUIRED fields
#   3. Dry-run: bash run_snakemake.sh -n

# =============================================
# REQUIRED
# =============================================

output_dir: "FILL_ME"            # Run root — all outputs go under this directory
sample_manifest: "FILL_ME"       # TSV: sample, bam_path [, bam_index]
ref_fasta: "FILL_ME"
img: "FILL_ME"                   # Singularity/Apptainer image path (pinned version, never :latest)

# =============================================
# OPTIONAL — Feature A
# =============================================

# Set to enable feature A (null = skip)
feature_a_script: null
feature_a_extra_args: ""

# =============================================
# OPTIONAL — Feature B (requires Feature A)
# =============================================

# Set both to enable (null = skip)
feature_b_input: null
feature_b_map: null
```

---

## 9. Common Debug Patterns

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `improperly formatted strand field 3014751` | Input BED has >6 columns; modkit expects BED3-BED6 | User must provide properly formatted BED (don't auto-fix inputs) |
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8b` | Script using `open()` on a `.gz` file; `0x8b` is gzip magic byte | Use `gzip.open(path, "rt")` for `.gz` files |
| Job completes in <5 seconds (too fast) | Container not activated; rule ran bare on compute node | Check `singularity:` directive on the rule + `--use-singularity` on CLI |
| `SLURM_MEM_PER_NODE` vs `SLURM_MEM_PER_CPU` fatal | Missing `mem_mb: 0` in profile, or coordinator uses `--mem` | Add `mem_mb: 0`; use `--mem-per-cpu` for coordinator |
| `ModuleNotFoundError: No module named 'pandas'` on compute node | Rule missing `singularity: IMG` directive | Add `singularity: IMG` to the rule |
| `pd.read_csv` silently converts "NA" to NaN | pandas auto-parses "NA" as missing | Use `dropna()` for filtering, never `!= "NA"` string comparison |
| `Nothing to be done` but outputs are missing | Outputs exist from a previous run at the same path | Check output paths; use a new `output_dir` for each run |
| `MissingInputException` for a file that exists | Chr prefix mismatch between BED and BAM, or file moved | Check `bed_chr_mode` in config; verify paths haven't changed |
| DAG builds but jobs fail silently | Missing `slurm_account` in default-resources | Add `slurm_account` to default-resources |
| `sacctmgr: not found` | Running Snakemake directly on login node | Submit coordinator as SLURM job |
| Workflow re-runs everything after adding samples | `output_dir` changed between runs | Use the same `output_dir` when adding samples to an existing cohort |
| `benchmark:` file empty or missing | Rule failed before completing | Check the log; benchmark is only written on success |

---

## 10. Checklist: Before Declaring a Workflow Complete

### Workflow code
- [ ] Dry-run succeeds (`snakemake -n`)
- [ ] Lint passes (`snakemake --lint`)
- [ ] DAG renders correctly (`snakemake --dag | dot -Tpdf > dag.pdf`)
- [ ] All output files exist and are non-empty after a test run
- [ ] Test suite exists (`test/test_config.yaml` + test data) and completes in <5 minutes

### SLURM profile
- [ ] Profile has `mem_mb: 0` in default-resources
- [ ] Profile has `slurm_account` in default-resources
- [ ] No `mem:` keys anywhere (use `mem_mb_per_cpu` only)
- [ ] `singularity-args:` has no `--` prefix

### Rules
- [ ] All rules that need container packages have `singularity: IMG`
- [ ] Compute-heavy rules have `benchmark:` directive
- [ ] External tool rules have `retries: 2`; script rules have `retries: 0`
- [ ] Intermediate files use `temp()` where appropriate
- [ ] Expensive final outputs use `protected()` where appropriate
- [ ] QC gate rules exist for critical checkpoints

### Scripts
- [ ] Scripts handle `.gz` input transparently
- [ ] Each script ends with `"=== DONE: ... completed successfully ==="`
- [ ] Scripts are testable standalone via argparse CLI

### Config and reproducibility
- [ ] Config template is documented with REQUIRED/OPTIONAL sections
- [ ] `run_snakemake.sh` is saved in the output directory
- [ ] Config file is copied to the output directory
- [ ] `run_metadata.yaml` is auto-generated
- [ ] `unset SLURM_MEM_PER_NODE` in run script
- [ ] Container image uses pinned version (never `:latest`)
- [ ] No hardcoded absolute paths in the Snakefile (all from config)

### Structure
- [ ] Wildcard-dependent paths use `{sample}` consistently
- [ ] Logs go to `{output_dir}/logs/` with rule name in the filename
- [ ] Benchmarks go to `{output_dir}/benchmarks/`
- [ ] QC outputs go to `{output_dir}/qc/`
- [ ] Rule outputs go to `{output_dir}/results/{rule_name}/`
- [ ] CHANGELOG.md updated with changes

---

## 11. Reference: Validated Workflow (ont_modkit_pileup)

This workflow was built, debugged, and validated across multiple sessions:

- **Workflow code**: `workflows/ont_modkit_pileup/`
  - `Snakefile` — 5 conditional rules (convert_bed, pileup, aggregate, cohort_matrices, tensor, correlation)
  - `scripts/` — 4 pluggable Python scripts
  - `profiles/slurm/config.yaml` — workflow-specific SLURM profile
  - `config_template.yaml` — documented config template
- **Test run**: `outputs/L1_promoter_monomer_DNAme/`
  - 4 samples, 100-locus test BED, full pipeline including tensor + correlation plots
  - All rules completed successfully via SLURM
- **Key design decisions**:
  - `--bgzf` flag in modkit for direct bgzipped output + `tabix` indexing in same rule
  - `--include-bed` for single-pass region-restricted pileup (1,483x faster than per-region)
  - `build_cohort_matrices` uses `run:` block (executes in coordinator, needs pandas)
  - `build_dname_rna_tensor` and `plot_dname_rna_correlation` use `shell:` + `singularity: IMG` (needs numpy/scipy on compute node)
  - BAM index auto-detection: checks `.bai`, `.bam.csi`, `.csi` in order
  - Chr prefix auto-detection: reads first non-comment BED line

---

## 12. Resolved Design Decisions

| Question | Decision | Reasoning |
|----------|----------|-----------|
| Scope: Snakemake + Nextflow? | Snakemake-only | Different idioms; joint skill would be shallow at both. Separate Nextflow skill later if needed. |
| Profile auto-selection? | No auto-selection | Sample count doesn't determine resource needs (4 large ONT BAMs need production resources). User picks explicitly. |
| Bundle ont_modkit_pileup as example? | Yes, as reference | Proven, battle-tested workflow. Cite in section 11. |
| Container awareness? | Check `softwares_containers_config.yaml` | Skill should suggest correct image from the config, never guess. |
| Validation hooks? | Deferred | Pre-commit hooks for `--lint` are nice-to-have but not critical for initial skill. |
| `output_dir` = results only, or run root? | Run root | Config, run script, metadata, benchmarks all travel with the results. `results/` subdirectory holds data products. Reproducibility and data are co-located. |
| Externalize scripts threshold? | Complexity, not line count | Short pipelines (awk, bgzip+tabix) are fine inline. Externalize when logic requires if/for/while or would benefit from standalone testing. |
