---
name: analysis-playbooks
description: |
  The lab's standard analysis chains, QC checkpoints and conventions, kept out
  of CLAUDE.md so they load only when the work calls for them. Use when
  planning, running or reviewing: ONT methylation (pod5, dorado basecall or
  align, modkit pileup / dmr, DMRs); variant calling (Clair3, Sniffles2, GATK
  HaplotypeCaller); bulk RNA-seq differential expression (fastp, STAR, salmon,
  featureCounts, DESeq2 / pyDESeq2); single-cell RNA-seq (CellRanger, STARsolo,
  Seurat, Scanpy); Snakemake or Nextflow run organization and site profiles;
  LLM applications or machine learning on genomic data; final manuscript
  figures (Nature sizes, ggplot2 base_size scaling, plate assembly). Also use
  whenever writing an analysis script, for the full logging and audit-trail
  specification.
version: 1.0.0
---

# Analysis playbooks

The standard chain, the QC checkpoints that stop a run, and what "done" looks
like, per domain. These are defaults: the user's instructions and the project's
own `CLAUDE.md` win. Silent tool failures (DSS, Clair3, Severus, deeptools,
liftOver) are a different collection, in the `analysis-gotchas` skill.

Read the reference that matches the work before designing the run.

## When to read what

| If the work involves | Read |
|---|---|
| ONT methylation: pod5 → dorado → modkit → DMRs | `references/ont_methylation.md` |
| SNV / indel / SV calling | `references/variant_calling.md` |
| Bulk RNA-seq differential expression | `references/rnaseq_dge.md` |
| Single-cell RNA-seq | `references/scrnaseq.md` |
| Snakemake or Nextflow: rules, site profiles, one run = one directory | `references/pipeline_development.md` |
| LLM applications, ML on genomic data | `references/ai_engineering.md` |
| Final manuscript figures, ggplot2 sizing, plate assembly | `references/figures.md` |
| Writing any analysis script (what the log must contain) | `references/logging_audit.md` |

IGV screenshots are in the `igv-screenshots` skill, container builds in
`singularity-build`, and SLURM-executor pitfalls in `snakemake`.

## QC checkpoints are stops

Each playbook lists QC checkpoints. When one fails, stop, report the metric to
the user and ask how to proceed. Do not continue past a failed checkpoint on the
grounds that the output looks plausible.
