# Poolability — what's safe to shard, what isn't

Three categories. The middle one is the trap: tools that *look* shardable but compute a global parameter you must materialize before scattering.

For DSS specifically: see `rules/dss.md` for the empirical-Bayes prior story, the `mclapply + detectCores()` silent-corruption incident, and post-run verification. Don't restate; just consult that file whenever DSS is in the loop.

## Fully shardable (scatter + gather is exact)

These compute per-locus / per-region quantities with no global dependency. Sharding by chromosome or region tiles produces results bit-identical to whole-genome (modulo region-scatter boundary effects for stateful tools).

| Tool / step | Why it's safe | Boundary caveat for region scatter |
|---|---|---|
| `modkit pileup` | per-CpG counts only | none for chrom; for region tiles, motif may straddle |
| `samtools depth` / `samtools coverage` | per-base | none |
| `bcftools call` | per-locus likelihood | none for chrom; indels at boundary in region |
| `deepvariant` (per-region) | per-locus inference | regions explicitly bounded; haplotype phasing within region |
| GATK `ApplyBQSR` | apply pre-computed table | none |
| GATK `HaplotypeCaller` (single-sample, GVCF mode) | per-region | none for chrom; `--interval-padding 100` for region |
| `liftOver` | per-feature | none |
| `bedtools intersect`/`coverage` | per-feature | none |
| `samtools markdup` (per-chrom) | within-chrom only | safe — duplicates can't span chroms |
| Per-read alignment (post-mapping filtering, `view -b`) | per-read | none |
| `featureCounts` (per-region) | per-feature counting | gene-spanning reads at boundary need padding |

## Two-phase: compute the global parameter first, then scatter

These tools can be parallelized, but only after a non-shardable preparation step. Run the global step on all data first; the per-shard step takes the global parameter as input. This is the most common pattern.

| Tool / step | Phase 1 (global, runs once) | Phase 2 (per-shard, scatter freely) |
|---|---|---|
| GATK BQSR | `BaseRecalibrator` on the whole BAM (or a downsample); produces recalibration table | `ApplyBQSR -bqsr <table>` per region |
| GATK joint genotyping | `GenomicsDBImport` (combine all gVCFs into a workspace) | `GenotypeGVCFs` per interval |
| GATK CNV (germline) | `CollectReadCounts` per sample → `CreateReadCountPanelOfNormals` (cohort) | `DenoiseReadCounts` + `ModelSegments` per sample (still needs full chrom for segmentation — see "not shardable") |
| salmon | `salmon index` (per-transcriptome) | `salmon quant` (per-sample, NOT per-region) |
| DESeq2 | `estimateSizeFactors` + `estimateDispersions` on full counts matrix | per-gene Wald test (already vectorized; sharding rarely helpful) |
| deepTools `bamCoverage` (with normalization) | compute scaling factor across genome | apply per-region |
| modkit `dmr` | bedMethyl pileup (per-sample, fully shardable upstream) | DMR call per region (modkit dmr accepts a regions BED) |

The Snakemake skeleton:
```python
rule global_step:
    input: expand("data/processed/{genome}/{sample}.bam", sample=SAMPLES)
    output: "data/processed/{genome}/global_param.tsv"

rule per_shard_step:
    input:
        bam="data/processed/{genome}/{sample}.bam",
        param="data/processed/{genome}/global_param.tsv"
    output: "data/processed/{genome}/{sample}.{chrom}.out"
```

## Not shardable (at the algorithmic level)

These tools compute a global quantity that cannot be reconstructed from per-shard outputs. Running them on a chromosome and concatenating across chromosomes produces a *different result* than running on the whole genome. The fix is usually to run on the full data; sometimes you can shard at a coarser unit (per-sample) but not per-region.

| Tool / step | What's global | Lab-specific notes |
|---|---|---|
| **DSS `DMLtest`** | Empirical-Bayes prior on all CpGs | **See `rules/dss.md`.** Per-chrom DSS ≠ same-chr slice of whole-genome. Real 2026-04-24 incident: 10–20× DMR inflation under SLURM memory pressure when `ncores` defaulted via `detectCores()`. |
| BSmooth (`bsseq` smoothing) | Window kernel crosses chromosome boundaries within kernel width | Per-chrom safe if kernel ≪ chrom length |
| CNV segmentation (CBS, HMM) | Within-chromosome state shared across chromosome | Per-chrom safe; sub-chr region scatter breaks segment continuity |
| PCA / clustering | Eigenvectors over full matrix | Sharding meaningless; always run on full matrix |
| STAR / salmon index build | Whole reference graph | One-shot; query is per-sample, not per-region |
| Allele-frequency / Hardy-Weinberg in cohort | Cohort denominator | Compute once on joint-called VCF |
| Cohort PCA on genotypes | Cross-sample structure | Run on all samples × all variants together |
| Joint variant calling (multi-sample) | Cross-sample posterior | Use the two-phase pattern (GATK GenomicsDBImport → GenotypeGVCFs) |
| Polygenic scoring | Cross-locus score sum | Per-chrom partial scores OK if summed at end with consistent missingness handling |
| edgeR / limma TMM normalization | Library-size factors | Compute once on full counts matrix |

## How to figure out if a new tool is poolable

Three questions, in order:

1. **Does the tool's docs mention "library size", "normalization", "background", "prior", "global mean", "training", "fit"?** If yes, suspect a global step.
2. **Does running on chr1-only and on chr2-only and concatenating give the same output as running on chr1+chr2?** If you can quickly test this on a small input, you have your answer.
3. **Does the tool have an `--intervals` / `--region` flag documented as "for parallelization"?** That's the maintainer telling you it's safely shardable at that boundary.

When in doubt, treat as two-phase. Run the global step on a small sample and confirm sharded outputs match.
