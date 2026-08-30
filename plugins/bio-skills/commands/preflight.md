---
description: Before scaffolding any pipeline, check whether a validated implementation already exists
argument-hint: <what you are about to build>
---

Do this **before** writing `workflow.smk`, `Snakefile`, `main.nf`, or any
pipeline scaffold. Search in this order and report what you find:

1. **nf-core/modules** — https://github.com/nf-core/modules/tree/master/modules/nf-core
   Common matches: `samtools/*`, `modkit/pileup`, `dorado/basecaller`, `severus`,
   `mosdepth`, `clair3`, `sniffles`, `gatk4/*`, `bwa/*`, `star/*`, `salmon`,
   `featurecounts`, `deseq2`, `multiqc`. These ship with `nf-test`, validated
   container references, and battle-tested invocation flags.
2. **nf-core pipelines** — does an end-to-end pipeline already cover this?
   `rnaseq`, `sarek`, `atacseq`, `methylong`, `taxprofiler`, `viralintegration`,
   `oncoanalyser`, `nanoseq`, `differentialabundance`, `mag`, `smrnaseq`.
3. **Lab-internal** — `ls ~/code/ pipelines/ workflows/`.
4. **Other community sources** — `snakemake-wrappers`, Galaxy ToolShed,
   published workflow repositories.

**Report what exists before writing anything.** Build from scratch only when
nothing suitable exists, the user explicitly asks for it, or the existing option
has a deal-breaking gap — and then name what you rejected and why. Pause for
confirmation before scaffolding.

## The cost of skipping this

Scaffolding `pipelines/modkit_pileup/workflow.smk` from scratch on 2026-05-01
missed that `--cpg` requires `--modified-bases` in modkit 0.6.1. The nf-core
`modkit/pileup` module ships that invocation pre-validated. One wasted batch
dispatch.
