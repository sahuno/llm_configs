# Snakefile Template

Use this template when creating a new Snakemake workflow. Replace `{placeholders}`
with actual values.

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

## Key Conventions

1. **Header**: docstring with workflow name, author, date
2. **Config section**: derive ALL paths from `config["output_dir"]`
3. **Sample manifest**: TSV with `sample` and `bam_path` columns minimum
4. **Targets list**: build `_targets` list, conditionally extend for optional features
5. **Rule anatomy**:
   - Docstring (one-line description)
   - `input:` — declare dependencies explicitly
   - `output:` — under `RESULTSDIR/{rule_name}/{sample}/`
   - `log:` — under `LOGDIR/{rule_name}_{sample}.log`
   - `benchmark:` — under `BENCHDIR/{rule_name}_{sample}.tsv`
   - `singularity:` — `IMG` for rules needing container packages
   - `retries:` — 2 for tools, 0 for scripts/QC
   - `shell:` — wrap in `( ... ) &> {log}` for log capture
6. **QC gates**: produce `.pass` sentinel files under `QCDIR`
7. **Optional rules**: wrap in `if USE_FEATURE:` block
8. **run_metadata rule**: always include, auto-documents each run
