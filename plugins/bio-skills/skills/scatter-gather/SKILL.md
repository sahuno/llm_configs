---
name: scatter-gather
description: Decide whether and how to scatter genomics workloads across chromosomes or region tiles, then gather the per-shard outputs back together correctly. Use proactively whenever the user mentions parallelizing per-chromosome, sharding by chrom, tiling the genome, splitting a BAM/VCF/BED by region, merging per-chrom outputs, or has a workflow with obvious per-chromosome parallelism (variant calling, methylation pileup/DMR, coverage, liftover, peak calling, SV calling). Also triggers on /scatter-gather, "scatter X across chromosomes", "shard this", "chunked variant calling", "merge per-chrom VCFs", "gather these bedmethyl files", "concat these bigwigs", or any per-region parallelism question. **Trigger even when the user is also using Snakemake or Nextflow** — those skills handle DAG plumbing while this one defines *what* to scatter, *whether* it's even safe to scatter (some computations like DSS DMLtest pool globally and break under naive sharding), and *how* to gather each output format without silent corruption. Especially trigger on questions about merging per-chromosome BAM / VCF / BED / bedMethyl / bigwig outputs, or whether a scatter-gather is equivalent to running on the whole genome.
---

# scatter-gather

Genomics scatter-gather looks trivial until it's silently wrong. The lab has hit several variants of "scattered + concatenated, looked right, was actually corrupt" — DSS DMLtest is the canonical example. This skill is the **decision and validation layer**: figure out whether to scatter, how to scatter, how to gather correctly per format, and how to validate. Implementation goes to the workflow-engine skills.

## When this applies

Use it when the user wants to:
- Parallelize a per-locus / per-region computation across chromosomes or region tiles (variant calling, methylation pileup, coverage, peak calling, liftover, base-level QC).
- Merge per-chrom outputs back into a single file (BAM, VCF, BED, bedMethyl, bigwig, etc.).
- Decide *whether* a step is even safe to scatter (some computations pool globally — see poolability check below).
- Choose between chromosome scatter and region tiling, and figure out per-shard resources.
- Add sanity checks before declaring a gather successful.

Skip when the parallelism is purely per-sample with no per-chromosome dimension — that's normal pipeline parallelism and the `snakemake` skill covers it.

## What this skill adds (and what it defers to)

This skill leans on the lab's existing infrastructure rather than restating it. Things to consult here vs there:

| Question | Where to look |
|---|---|
| Should I scatter at chromosome / region / 2D granularity? | `references/scatter_strategies.md` (this skill) |
| Per-shard memory/time scaling formulas | `references/scatter_strategies.md` |
| How do I gather format X correctly? | `references/gather_methods.md` (this skill) |
| Is tool X poolable / shardable? | `references/poolability.md` (this skill) — for **DSS**, see also `analysis-gotchas` skill → `references/dss.md` |
| How do I derive the contig list? | `block-hardcoded-contigs.sh` hook + CLAUDE.md §2 (lab rules) |
| Why does my Snakemake job fail with srun memory conflict? | `snakemake` skill → `references/gotchas.md` (lab rules) |
| Which partition / nodes? | `mskcc-hpc` skill → `references/mskcc_partitions.md` (lab rules) |
| Why does DSS silently corrupt under SLURM memory pressure? | `analysis-gotchas` skill → `references/dss.md` (lab rules — read this whenever DSS is involved) |
| `#`-header convention on BED-like outputs | CLAUDE.md §2 Genomic Output Conventions |

## Decision flow

Answer in order. Stop at the first "no" or "needs work" and resolve it.

1. **Is this step poolable, or is it shardable?** Some computations pool across all data: DSS dispersion priors (see `analysis-gotchas` skill → `references/dss.md`), DESeq2 size factors, GATK BQSR table, joint genotyping, CNV segmentation, salmon index. Sharding+gathering ≠ whole-genome for these. See `references/poolability.md` for the per-tool catalogue and the "two-phase" pattern.

2. **What's the right scatter granularity?** Chromosome (~24 shards, simple, unbalanced), region tiles (balanced but boundary effects), per-sample × per-chromosome (2D). See `references/scatter_strategies.md`.

3. **What's the gather method for this output format?** `cat` is almost never correct. BAM, VCF, BED, bedMethyl, bigwig each have a format-aware merge tool with its own pitfalls. See `references/gather_methods.md`.

4. **Who runs the DAG?** Hand off: `snakemake` skill for Snakemake (`expand`, `checkpoint`, per-shard resource lambdas), `nextflow-development` / `nfcore-module` skills for Nextflow channels and pre-built nf-core scatter-gather modules.

5. **What proves it worked?** Run the sanity checks below.

## Five things easy to overlook

These are the failure modes the lab has hit. Each one has cost real time at least once.

1. **The chromosome list is not a constant.** Hardcoding `chr1..22,X,Y` silently drops alts/decoys and breaks across builds (`chrM` ↔ `MT`). Always derive at runtime from `<ref>.fa.fai` or chrom.sizes (paths in `$SITE_CONFIG/databases.yaml`). The contig **subset** (autosomes only? +X/Y? +MT? +`_random`/`_alt`/decoys?) is a config decision the user must approve, not a default. The `block-hardcoded-contigs.sh` hook will catch the worst version of this.

2. **Load imbalance is the silent killer.** chr1 is ~5× chrY. One-job-per-chromosome looks parallel but is bounded by the longest shard, and identical resource asks waste cluster capacity. Region tiling solves balance; per-shard resource lambdas solve waste. Recipes and formulas in `references/scatter_strategies.md`. When benchmarking scatter speedup, look at the **longest-shard wall time**, not the mean.

3. **Some steps are not shardable.** Anything that computes a global parameter from the full dataset (empirical-Bayes prior, size factor, BQSR table, salmon index) cannot be reproduced by sharding + concatenating. The `analysis-gotchas` skill → `references/dss.md` incident is the canonical lab example: per-chrom DSS runs are *not* the same as the same-chr slice of a whole-genome run. The fix is the **two-phase pattern**: run the global step on all data first, then scatter the local step using the global parameter. See `references/poolability.md` for the catalogue.

4. **The gather is not a `cat`.** Format-aware merge is required: `samtools merge` (preserve `@SQ`, dedupe `@PG`), `bcftools concat -a` (sorted, sample columns aligned), `sort` + `bedtools merge` (BED), `bigWigCat`, etc. Plain `cat` of compressed shards almost always produces something that *looks* fine, fails downstream tools (tabix can't index, IGV won't load), and forces a debug session. Full per-format table with commands and pitfalls in `references/gather_methods.md`. **Always** regenerate indexes (`.bai`/`.tbi`/`.csi`) on the gathered output.

5. **Failure granularity needs a DAG engine.** A scatter of 24 jobs where 1 fails should re-run 1, not 24. Use Snakemake or Nextflow — never an ad-hoc bash for-loop, which loses provenance and forces full reruns. Trigger the `snakemake` or `nextflow-development` skill for the actual mechanics. Cap shard count: tens to low hundreds is the sweet spot; >1000 shards is scheduler-hostile.

## Sanity checks (run before declaring success)

These are cheap and catch ~all silent gather bugs.

```bash
# 1. Contig coverage matches the scatter list
zcat gathered.vcf.gz | grep -v '^#' | awk '{print $1}' | sort -u \
  | diff - <(sort -u scatter.contigs.txt)

# 2. Per-shard line counts sum to gathered line count (within boundary tolerance)
shard_lines=$(for s in shards/*.vcf.gz; do zcat "$s" | grep -vc '^#'; done | paste -sd+ | bc)
gather_lines=$(zcat gathered.vcf.gz | grep -vc '^#')
echo "shards=$shard_lines gather=$gather_lines"

# 3. Sort order valid
bcftools view gathered.vcf.gz > /dev/null && echo "VCF sort OK"

# 4. Index regenerated and current
test gathered.vcf.gz.tbi -nt gathered.vcf.gz || echo "STALE INDEX"
```

For BAM:
- `samtools quickcheck gathered.bam` — corruption check.
- `samtools idxstats gathered.bam` — every expected contig present.
- Sum of per-shard `flagstat` totals ≈ gathered `flagstat` (small drift from `@PG` dedupe is normal).

For BED-like:
- Line count matches sum across shards (allow boundary-dedupe drift in region scatter).
- `sort -c -k1,1 -k2,2n gathered.bed` returns success.
- For modkit bedMethyl: `LC_ALL=C` is mandatory (RHEL UTF-8 default breaks tabix); preserve the `#` header per CLAUDE.md §2.

For bigwig:
- `bigWigInfo gathered.bw` reports expected number of contigs.
- Spot-check 2-3 random regions in IGV or by `bigWigAverageOverBed`.

For DSS specifically: `analysis-gotchas` skill → `references/dss.md` lists the post-run verification triple (sacct state, recycling-warning grep, per-chrom row-count parity). Run all three.

## Hand-off to workflow engines

This skill defines *what* and *how to validate*. Implementation goes elsewhere:

- **Snakemake**: trigger the `snakemake` skill. Use `expand()` for static chromosome scatter; use `checkpoint` for region tiles computed at runtime. Resource scaling via `mem_mb_per_cpu = lambda wc: f(wc.chrom)`. Mind the Snakemake 9 `srun` memory conflict (use `mem_mb_per_cpu`, not `mem_mb`) — see `snakemake` skill → `references/gotchas.md`.

- **Nextflow / nf-core**: trigger the `nextflow-development` or `nfcore-module` skills. Channel idioms: `.combine()`, `.groupTuple()`. Many nf-core modules already implement scatter-gather correctly (`gatk4/scatterintervalsbyns`, `bcftools/concat`, `samtools/merge`) — prefer these over reimplementing.

## References

- `references/scatter_strategies.md` — chromosome vs region tiling vs 2D grid; boundary handling; resource scaling formulas; shard-count caps.
- `references/gather_methods.md` — format-by-format gather recipes (BAM, CRAM, VCF, gVCF, BED, BEDGRAPH, bedMethyl, bigwig, FASTQ, HDF5/Zarr, TSV).
- `references/poolability.md` — per-tool catalogue: fully shardable / two-phase / not shardable, with examples for GATK BQSR, DESeq2, salmon, modkit, deeptools. For DSS specifics, see `analysis-gotchas` skill → `references/dss.md`.
