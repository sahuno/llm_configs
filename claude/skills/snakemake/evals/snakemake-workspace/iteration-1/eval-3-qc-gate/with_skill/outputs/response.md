# Adding a QC Gate After Alignment in Snakemake

## Approach

The correct pattern is to make the QC check a **first-class Snakemake rule** that produces a `.pass` sentinel file. Downstream rules (variant calling) depend on this sentinel, so Snakemake will not schedule them until the QC gate succeeds. If a sample fails QC, the rule raises an error, the sentinel is never created, and the entire downstream DAG for that sample is blocked.

This is preferable to embedding QC logic inside the alignment rule or the variant calling rule because:

1. **Separation of concerns** -- alignment does alignment, QC does QC, variant calling does variant calling.
2. **Clear failure diagnostics** -- a failed `qc_alignment` rule in the Snakemake log immediately tells you the problem is mapping rate, not a tool crash.
3. **No retries on QC failures** -- QC failures are data issues, not transient SLURM problems. Setting `retries: 0` ensures the pipeline stops immediately rather than wasting compute retrying a sample that will never pass.
4. **Sentinel files are auditable** -- you can inspect `qc/alignment_{sample}.pass` after the run to see every sample's mapping rate.

## Directory Layout

Following the skill's run organization pattern, QC sentinels go under a dedicated `qc/` subdirectory:

```
{output_dir}/
├── results/
│   ├── alignment/{sample}/{sample}.bam
│   ├── alignment/{sample}/{sample}.flagstat
│   ├── variant_calling/{sample}/{sample}.vcf.gz
│   └── annotation/{sample}/{sample}.annotated.vcf.gz
├── qc/
│   └── alignment_{sample}.pass          # <-- sentinel from QC gate
├── logs/
│   ├── align_{sample}.log
│   ├── qc_alignment_{sample}.log
│   ├── call_variants_{sample}.log
│   └── annotate_{sample}.log
└── benchmarks/
```

## Complete Code

Below is the modified Snakefile showing the original 3 rules plus the new QC gate. The key changes are marked with comments.

```python
"""
WGS Variant Calling Pipeline with Alignment QC Gate
Author: Samuel Ahuno (ekwame001@gmail.com)
Date: 2026-03-05
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

# QC thresholds (configurable, with sensible defaults)
MIN_MAPPING_RATE = config.get("min_mapping_rate", 80.0)

# ===========================================================================
# Sample manifest
# ===========================================================================
manifest = pd.read_csv(config["sample_manifest"], sep="\t")
SAMPLE_IDS = manifest["sample"].tolist()

def get_fastq_r1(wildcards):
    row = manifest.loc[manifest["sample"] == wildcards.sample].iloc[0]
    return str(row["fastq_r1"])

def get_fastq_r2(wildcards):
    row = manifest.loc[manifest["sample"] == wildcards.sample].iloc[0]
    return str(row["fastq_r2"])

# ===========================================================================
# Targets
# ===========================================================================
rule all:
    input:
        expand(
            os.path.join(RESULTSDIR, "annotation", "{sample}", "{sample}.annotated.vcf.gz"),
            sample=SAMPLE_IDS,
        ),


# ===========================================================================
# Rule 1: Alignment
# ===========================================================================
rule align:
    """Align reads to reference genome and generate flagstat QC."""
    input:
        r1=get_fastq_r1,
        r2=get_fastq_r2,
        ref=REF,
    output:
        bam=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.bam"),
        bai=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.bam.bai"),
        flagstat=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.flagstat"),
    log:
        os.path.join(LOGDIR, "align_{sample}.log"),
    benchmark:
        os.path.join(BENCHDIR, "align_{sample}.tsv")
    singularity:
        IMG
    retries: 2
    threads: 16
    shell:
        """
        (
        echo "$(date '+%Y-%m-%d %H:%M:%S') === align: {wildcards.sample} ==="
        bwa mem -t {threads} -R '@RG\\tID:{wildcards.sample}\\tSM:{wildcards.sample}' \
            {input.ref} {input.r1} {input.r2} \
        | samtools sort -@ 4 -o {output.bam}
        samtools index {output.bam}
        samtools flagstat {output.bam} > {output.flagstat}
        echo "$(date '+%Y-%m-%d %H:%M:%S') Done: {output.bam}"
        ) &> {log}
        """


# ===========================================================================
# Rule 2: QC Gate -- Alignment Quality Check (NEW)
# ===========================================================================
rule qc_alignment:
    """Fail pipeline for sample if mapping rate < threshold (default 80%).

    Parses samtools flagstat output to extract the mapped read percentage.
    Produces a .pass sentinel file that downstream rules depend on.
    If the check fails, raises ValueError -- no sentinel is created,
    and all downstream rules for this sample are blocked.
    """
    input:
        flagstat=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.flagstat"),
    output:
        qc_pass=os.path.join(QCDIR, "alignment_{sample}.pass"),
    log:
        os.path.join(LOGDIR, "qc_alignment_{sample}.log"),
    retries: 0  # QC failures are data issues, not transient -- fail immediately
    run:
        import re

        with open(input.flagstat) as f:
            text = f.read()

        # samtools flagstat format: "12345 + 0 mapped (95.42% : N/A)"
        match = re.search(r"(\d+\.\d+)%\s+mapped", text)
        if match is None:
            raise ValueError(
                f"QC FAIL: {wildcards.sample} -- could not parse mapping rate "
                f"from {input.flagstat}. File content:\n{text}"
            )

        mapped_pct = float(match.group(1))
        threshold = MIN_MAPPING_RATE

        # Write log regardless of pass/fail
        with open(log[0], "w") as logf:
            logf.write(f"Sample: {wildcards.sample}\n")
            logf.write(f"Mapping rate: {mapped_pct}%\n")
            logf.write(f"Threshold: {threshold}%\n")
            logf.write(f"Result: {'PASS' if mapped_pct >= threshold else 'FAIL'}\n")

        if mapped_pct < threshold:
            raise ValueError(
                f"QC FAIL: {wildcards.sample} mapping rate {mapped_pct}% "
                f"< {threshold}% threshold"
            )

        # Only reached on PASS -- create sentinel
        with open(output.qc_pass, "w") as f:
            f.write(f"PASS\n")
            f.write(f"sample={wildcards.sample}\n")
            f.write(f"mapping_rate={mapped_pct}%\n")
            f.write(f"threshold={threshold}%\n")


# ===========================================================================
# Rule 3: Variant Calling (depends on QC gate)
# ===========================================================================
rule call_variants:
    """Call variants from aligned BAM. Only runs if alignment QC passed."""
    input:
        bam=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.bam"),
        bai=os.path.join(RESULTSDIR, "alignment", "{sample}", "{sample}.bam.bai"),
        ref=REF,
        # --- QC GATE DEPENDENCY ---
        # This sentinel file is only created when qc_alignment passes.
        # If the sample fails QC, this input will never exist and
        # Snakemake will not schedule this rule for that sample.
        qc_pass=os.path.join(QCDIR, "alignment_{sample}.pass"),
    output:
        vcf=os.path.join(RESULTSDIR, "variant_calling", "{sample}", "{sample}.vcf.gz"),
    log:
        os.path.join(LOGDIR, "call_variants_{sample}.log"),
    benchmark:
        os.path.join(BENCHDIR, "call_variants_{sample}.tsv")
    singularity:
        IMG
    retries: 2
    threads: 8
    shell:
        """
        (
        echo "$(date '+%Y-%m-%d %H:%M:%S') === call_variants: {wildcards.sample} ==="
        gatk HaplotypeCaller \
            -R {input.ref} \
            -I {input.bam} \
            -O {output.vcf} \
            --native-pair-hmm-threads {threads}
        echo "$(date '+%Y-%m-%d %H:%M:%S') Done: {output.vcf}"
        ) &> {log}
        """


# ===========================================================================
# Rule 4: Annotation
# ===========================================================================
rule annotate:
    """Annotate variant calls."""
    input:
        vcf=os.path.join(RESULTSDIR, "variant_calling", "{sample}", "{sample}.vcf.gz"),
        ref=REF,
    output:
        vcf=os.path.join(RESULTSDIR, "annotation", "{sample}", "{sample}.annotated.vcf.gz"),
    log:
        os.path.join(LOGDIR, "annotate_{sample}.log"),
    benchmark:
        os.path.join(BENCHDIR, "annotate_{sample}.tsv")
    singularity:
        IMG
    retries: 2
    threads: 4
    shell:
        """
        (
        echo "$(date '+%Y-%m-%d %H:%M:%S') === annotate: {wildcards.sample} ==="
        funcotator \
            -R {input.ref} \
            -V {input.vcf} \
            -O {output.vcf} \
            --output-file-format VCF
        echo "$(date '+%Y-%m-%d %H:%M:%S') Done: {output.vcf}"
        ) &> {log}
        """
```

## How the DAG Changes

Before (no QC gate):
```
align --> call_variants --> annotate
```

After (with QC gate):
```
align --> qc_alignment --> call_variants --> annotate
              |
              v
         .pass sentinel
```

The `qc_alignment` rule reads the `.flagstat` file (produced by `align`), validates the mapping rate, and creates a `.pass` sentinel. The `call_variants` rule lists this sentinel in its `input:` block, so Snakemake enforces the dependency automatically.

## Key Design Decisions

### 1. QC threshold is configurable via config

```yaml
# config.yaml
min_mapping_rate: 80.0   # override default 80% threshold
```

This avoids hardcoding the threshold. Different projects may have different acceptable mapping rates (e.g., FFPE samples might warrant a lower threshold).

### 2. `retries: 0` on the QC rule

QC failures reflect data quality problems, not transient infrastructure issues. Retrying a sample with 40% mapping rate will never produce 80%. Failing immediately saves compute and surfaces the problem in the Snakemake report.

### 3. `run:` block instead of `shell:` for the QC rule

The QC gate is a lightweight Python check (parse text, compare a number). It does not need a container, does not need multiple threads, and benefits from direct Python string manipulation. Per the skill guidelines, `run:` is appropriate for lightweight logic. The log is written manually inside the `run:` block.

**Caveat**: `run:` blocks execute in the Snakemake coordinator process. This is fine for a simple file parse, but if your QC check were computationally expensive (e.g., running a tool), you should use `shell:` with an external script instead.

### 4. Sentinel file contains metadata

The `.pass` file is not empty -- it records the sample name, mapping rate, and threshold used. This makes post-hoc auditing straightforward:

```bash
# Check all QC results at a glance
cat qc/alignment_*.pass
```

### 5. Parsing robustness

The regex `r"(\d+\.\d+)%\s+mapped"` matches the standard samtools flagstat format. If the format cannot be parsed (e.g., corrupt file), the rule raises an error with the full file content for debugging, rather than silently passing.

## Config Addition

Add this to your `config.yaml`:

```yaml
# QC thresholds
min_mapping_rate: 80.0   # minimum % mapped reads to pass alignment QC
```

## Verifying the QC Gate

After adding the rule, validate with a dry-run:

```bash
snakemake -n --snakefile Snakefile --configfile config.yaml
```

You should see `qc_alignment` scheduled between `align` and `call_variants` for every sample in the DAG. To visualize:

```bash
snakemake --dag --snakefile Snakefile --configfile config.yaml | dot -Tpdf > dag.pdf
```
