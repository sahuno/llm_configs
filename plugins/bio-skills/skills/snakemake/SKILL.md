---
name: snakemake
description: |
  Expert Snakemake workflow engineer for bioinformatics pipelines on SLURM HPC.
  Specializes in creating, debugging, and running Snakemake 9 workflows with
  battle-tested SLURM profiles, proper container integration, and reproducible
  run organization. Use this skill proactively whenever the user asks to:
  create/write/build a Snakemake workflow or pipeline, debug a Snakemake error
  or failed SLURM job, add rules to an existing Snakefile, write or fix a SLURM
  profile for Snakemake, organize pipeline outputs or run directories, convert
  a shell script or ad-hoc analysis into a reproducible Snakemake workflow, or
  troubleshoot Snakemake 9 + SLURM executor issues (memory conflicts, container
  propagation, stale locks). Also trigger when the user mentions snakemake dry-run,
  snakemake DAG, snakemake profile, workflow-profile, SLURM executor plugin,
  modkit pileup pipeline, or any multi-sample bioinformatics pipeline that needs
  per-sample parallelism with a dependency DAG.
  Do NOT trigger for: tasks with <3 steps and no parallelism (bash script is better),
  pure Nextflow workflows, or one-off data exploration.
version: 1.0.0
author: Samuel Ahuno (ekwame001@gmail.com)
---

# Snakemake Workflow Skill

Build production-grade Snakemake 9 workflows on SLURM HPC with reproducible run
organization, container integration, and battle-tested pitfall avoidance.

## When to Use This Skill

**Use when** the user needs:
- A new Snakemake workflow or additional rules for an existing one
- Debugging a Snakemake/SLURM error (check `references/debug_patterns.md`)
- A SLURM profile for Snakemake (check `references/slurm_profiles.md`)
- To convert ad-hoc scripts into a reproducible pipeline

**Don't use when** the task has <3 steps, no per-sample parallelism, and no
dependency DAG. A bash script is simpler and Snakemake overhead isn't free.

## Core Architecture

### 1. One Rule = One Tool

Each rule wraps exactly one tool or operation. Rules compose vertically via `input:`
dependencies. Optional rule blocks are gated by config booleans (`if USE_FEATURE:`).
Adding a rule should never break existing rules.

### 2. Workflow vs Results Separation

The workflow is a **tool**; each run is an **experiment**. Never write outputs into
the workflow directory.

**Workflow directory** (versioned, reusable):
```
workflows/{workflow_name}/
├── Snakefile
├── config_template.yaml
├── scripts/                    # Pluggable scripts with argparse CLI
├── profiles/slurm/config.yaml  # Workflow-specific SLURM profile
├── test/                       # Test fixtures (<5 min on cpushort)
│   ├── test_config.yaml
│   ├── test_manifest.tsv
│   └── test_regions.bed
└── CHANGELOG.md
```

**Run root** (one directory = one experiment):
```
{output_dir}/
├── config.yaml              # COPY of config (frozen at run start)
├── run_snakemake.sh          # Exact reproduction command
├── manifest.tsv              # COPY of sample sheet
├── run_metadata.yaml         # Auto-generated (date, versions, samples)
├── results/{rule_name}/{sample}/   # ALL rule outputs
├── benchmarks/               # benchmark: directive outputs
├── qc/                       # QC gate sentinel files
└── logs/                     # ALL rule logs
```

### 3. Single `output_dir` Config Key

All subdirectories derived internally — never add separate config keys for logs,
figures, or matrices:

```python
OUTDIR     = config["output_dir"]
RESULTSDIR = os.path.join(OUTDIR, "results")
LOGDIR     = os.path.join(OUTDIR, "logs")
BENCHDIR   = os.path.join(OUTDIR, "benchmarks")
QCDIR      = os.path.join(OUTDIR, "qc")
```

### 4. Externalize Complex Logic

Shell one-liners are fine inline (`awk`, `bgzip && tabix`). Externalize when the
shell block needs `if/for/while`, variable manipulation, or multi-step Python.
Rule of thumb: if you can't understand it in 10 seconds, externalize it.

- Scripts go under `workflow_dir/scripts/` with argparse CLI
- Reference via `os.path.join(workflow.basedir, "scripts", "script.py")`
- Never inline complex Python in `run:` blocks for SLURM-submitted rules —
  `run:` executes in the coordinator process, not on the compute node

### 5. Validate Before Every Submission

After any Snakefile edit:
1. `snakemake --lint` — catches style issues
2. `snakemake -n` — dry-run validates the full DAG
3. `snakemake --dag | dot -Tpdf > dag.pdf` — visualize dependencies

Dry-run is the minimum test. A small-data end-to-end test is preferred.

### 6. Built-in Resource Management

| Feature | When to Use |
|---------|-------------|
| `benchmark:` | Every compute-heavy rule — informs production resource allocation |
| `temp()` | Intermediate files (auto-deleted after downstream rules complete) |
| `protected()` | Expensive final outputs (prevents accidental deletion) |
| `retries: 2` | External tool rules (transient SLURM failures) |
| `retries: 0` | Python scripts and QC gates (fail fast on bugs/data issues) |

### 7. QC Gates as Workflow Rules

QC checks are Snakemake rules, not informal post-hoc steps. Pattern: QC rule
produces a `.pass` sentinel; downstream rules depend on it.

```python
rule qc_alignment:
    """Fail if mapping rate < 80%."""
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
```

Gate after: alignment, pileup, DMR calling. Don't gate on soft thresholds — log
and report those instead.

### 8. Config is the Run Manifest

All cohort-specific details (paths, regex patterns, sample ID formats, exclusion
keywords) are config args, never hardcoded. This enables reuse across cohorts
without code changes. Config documents itself with comments.

### 9. Container Discipline

- Never use `:latest` tags — pin exact versions (`onttools_v3.9.sif`)
- Every rule needing container packages must have `singularity: IMG`
- Load container paths from `softwares_containers_config.yaml` — never guess
- If a rule has `singularity:` directive, do NOT add `singularity exec` in `shell:`

### 10. Test Suite

Every workflow ships with `test/` containing test_config.yaml, test_manifest.tsv,
and test_regions.bed. Tests must complete in <5 minutes on cpushort using slurmMinimal profile.

## Snakemake 9 + SLURM Critical Pitfalls

These are battle-tested fixes. Memorize them — they cause the most debugging time:

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Built-in `mem_mb: 1000` | `SLURM_MEM_PER_NODE` vs `SLURM_MEM_PER_CPU` fatal | Add `mem_mb: 0` to `default-resources` |
| `mem:` in profile | Same fatal conflict | Never use `mem:` — use `mem_mb_per_cpu` |
| Missing `slurm_account` | Silent job rejection | Always set `slurm_account` in `default-resources` |
| Coordinator uses `--mem=XG` | Propagates to child jobs via `--export=ALL` | Use `--mem-per-cpu`; add `unset SLURM_MEM_PER_NODE` |
| `--singularity-args` (with `--`) | Key not recognized | Use `singularity-args:` (no `--` prefix) |
| `run:` block on SLURM | Executes in coordinator, not compute node | Use `shell:` + script for heavy work |
| Rule missing `singularity:` | `ModuleNotFoundError` on compute | Add `singularity: IMG` to every rule needing packages |
| Stale lock | `Directory cannot be locked` | `snakemake --unlock` then `--rerun-incomplete` |
| `--profile` with `--directory` | Profile not found | Always use absolute path for `--profile` |
| `sacctmgr: not found` | Login node missing SLURM CLI | Submit coordinator as SLURM batch job |

For the full pitfall table and debug patterns, read `references/debug_patterns.md`.

## Reference Files

Read these when you need detailed templates or troubleshooting:

| File | When to Read |
|------|-------------|
| `references/snakefile_template.md` | Creating a new Snakefile — full template with all conventions |
| `references/slurm_profiles.md` | Writing or debugging SLURM profiles (3 profile tiers) |
| `references/config_template.md` | Creating config files and run scripts |
| `references/script_interface.md` | Writing pluggable Python scripts for `scripts/` |
| `references/debug_patterns.md` | Diagnosing Snakemake/SLURM errors |
| `references/completion_checklist.md` | Before declaring a workflow complete |

## Retry Guidance by Rule Type

| Rule Type | Retries | Reason |
|-----------|---------|--------|
| External tool (modkit, samtools, STAR) | 2 | SLURM nodes can timeout or OOM transiently |
| Python script (aggregate, tensor, plot) | 0 | Code bugs should fail immediately |
| File conversion (awk, bgzip, tabix) | 1 | Rare NFS issues |
| QC gate rules | 0 | QC failures are data issues, not transient |

## Incremental Sample Addition

Adding samples to `sample_manifest` triggers only new per-sample rules (Snakemake
checks output files). Cohort-level rules re-run because the expand list changed.

- Use the **same** `output_dir` when adding samples to an existing cohort
- Force cohort re-run only: `snakemake --forcerun build_cohort_matrices`
- If `output_dir` changes, everything re-runs (no prior outputs)

## Workflow Completion Checklist

Before declaring any workflow complete, run through the checklist in
`references/completion_checklist.md`. The critical items:

1. Dry-run succeeds (`snakemake -n`)
2. Profile has `mem_mb: 0` and `slurm_account` in default-resources
3. All container-dependent rules have `singularity: IMG`
4. Compute-heavy rules have `benchmark:` directive
5. `unset SLURM_MEM_PER_NODE` in run script
6. No hardcoded absolute paths in Snakefile
7. Test suite exists and passes

## Validated Reference Workflow

The `ont_modkit_pileup` workflow serves as the reference implementation:
- 5 conditional rules: convert_bed, pileup, aggregate, cohort_matrices, tensor, correlation
- Key patterns: `--include-bed` for single-pass pileup, chr prefix auto-detection,
  BAM index auto-detection (`.bai`, `.bam.csi`, `.csi`)
- `run:` for lightweight cohort steps; `shell:` + `singularity:` for compute
- Located at: `workflows/ont_modkit_pileup/`
