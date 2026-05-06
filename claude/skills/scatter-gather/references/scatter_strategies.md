# Scatter strategies — how to split the work

Three patterns cover almost everything. Pick by answering: how stateful is the per-region computation, and how imbalanced are the natural shards?

## Pattern 1: Chromosome scatter

One shard per chromosome (or per chromosome subset). ~24 shards on hg38/mm10.

**When to use**: stateful tools where boundaries matter (SV calling, CNV segmentation, smoothing, phasing). Chromosome boundaries are biologically real — calls cannot span them — so chrom scatter is always safe.

**Pros**: simple, no boundary concerns, naturally bounded shard count.

**Cons**: chr1 (~250 Mb) is ~5× chrY (~57 Mb). Wall time bounded by chr1; cluster utilization poor.

**Build the contig list**:
```bash
# autosomes + X/Y/M from the fasta index
awk '$1 ~ /^chr([0-9]+|X|Y|M)$/ {print $1}' "${FASTA}.fai" > scatter.contigs.txt
```

**Decide subset explicitly** — defaults vary by analysis:
- Variant calling: usually autosomes + X + Y (and M as separate run with ploidy=1)
- Methylation pileup: autosomes + X + Y; M optional; alts/decoys often kept
- CNV: autosomes only typical
- Liftover / BED ops: everything in the fasta index

## Pattern 2: Region tiling

Equal-size tiles across the genome, e.g. 10 Mb. ~300 shards on hg38 at 10 Mb.

**When to use**: stateless per-locus computations where load balance matters more than boundary purity. Variant calling (per-region), modkit pileup, coverage.

**Pros**: near-uniform shard wall time. Cluster utilization much better than chromosome scatter for compute-heavy steps.

**Cons**: boundary effects for any stateful operation (an indel at position 9,999,998 in tile 1 is the same site as an indel at position 10,000,002 in tile 2 — needs deduping at gather, or pad shards with overlap).

**Build the tile list**:
```bash
bedtools makewindows -g "${SIZES}" -w 10000000 > tiles.bed
# For overlap-padded tiles (boundary safety):
bedtools makewindows -g "${SIZES}" -w 10000000 -s 9990000 > tiles.padded.bed
# Then in gather, dedupe by exact position+allele.
```

**Tile size selection**:
- Compute-bound step (variant calling): aim for shards of ~10-20 minutes wall time. 10 Mb is a good starting point on Ice Lake-SP.
- I/O-bound step (BAM slicing, depth): tiles can be larger; per-job overhead dominates.
- Memory-bound step: tile size is set by memory, not time.

## Pattern 3: Per-sample × per-chromosome (2D grid)

Cohort jobs: scatter over both samples and chromosomes simultaneously.

**When to use**: large cohort with per-sample computation that's also per-region (e.g., per-sample GVCF generation, per-sample methylation pileup).

**Pros**: maximum parallelism. ~N_samples × N_chroms shards.

**Cons**: shard count explodes. 100 samples × 24 chroms = 2400 shards. SLURM scheduler hates this.

**Mitigation**: cap at one dimension. For a 100-sample cohort, prefer per-sample parallelism with whole-genome processing per sample, unless per-sample wall time is intolerable.

```python
# Snakemake 2D scatter
rule per_sample_per_chrom:
    output: "data/processed/{genome}/{sample}.{chrom}.bedmethyl.gz"
    ...

rule gather_sample:
    input: lambda wc: expand("data/processed/{genome}/{sample}.{chrom}.bedmethyl.gz",
                             genome=wc.genome, sample=wc.sample, chrom=CHROMS)
    output: "data/processed/{genome}/{sample}.bedmethyl.gz"
```

## Per-shard resource scaling

Default Snakemake behavior asks for the same resources for every shard, which is wrong if shards are imbalanced. Scale by chromosome size:

```python
# Build chrom→size map at Snakefile load
CHROM_SIZES = {l.split()[0]: int(l.split()[1])
               for l in open(config["sizes"]) if l.strip()}

def chrom_mem_mb_per_cpu(wc):
    # scale linearly with chrom length, with a floor and ceiling
    mb = max(1000, min(8000, int(CHROM_SIZES[wc.chrom] / 1e6 * 20)))
    return mb

rule per_chrom:
    output: "data/processed/{genome}/{sample}.{chrom}.bam"
    resources:
        mem_mb_per_cpu=chrom_mem_mb_per_cpu,
        # NB: use mem_mb_per_cpu, NOT mem_mb — see rules/snakemake.md
    threads: 8
```

Same pattern for `runtime`:
```python
def chrom_runtime_min(wc):
    return max(30, int(CHROM_SIZES[wc.chrom] / 1e6 * 1.5))
```

## Shard count caps and overhead

Per-job SLURM overhead on MSKCC HPC is roughly 5-15 s (queue → start → cleanup), depending on partition. Rule of thumb:

- **< 100 shards**: no concern.
- **100-1000 shards**: monitor scheduler load; consider `--latency-wait 60`.
- **> 1000 shards**: scheduler overhead becomes meaningful relative to work. Either coarsen tiles or batch them into composite shards within Snakemake.

If a tile takes < 30 s of work, you're spending more time on scheduling than computing. Coarsen.

## Boundary handling for region tiles

Stateful tools at region boundaries:

1. **Variant callers**: an indel at the boundary may be called twice (once per tile) or split (called as two separate variants). Mitigations:
   - Pad tiles with overlap, then dedupe by `chr:pos:ref:alt` in the gather.
   - Use the caller's native interval-padding (GATK `--interval-padding 100`).

2. **SV callers**: SVs spanning a tile boundary are catastrophic; either skip region tiling for SV calling (use chrom scatter) or use SV-aware scattering (split at low-complexity regions).

3. **Smoothing / windowed stats**: kernel windows truncate at tile boundaries → edge artefacts. Pad with overlap equal to the kernel half-width, then crop the gather to non-overlapping regions.

4. **Phasing**: read-backed phasing breaks at tile boundaries. Use long-read aware tools (whatshap, longshot) with explicit chromosome scatter, not region tiling.

When in doubt, prefer chromosome scatter over region tiling for stateful tools — the load imbalance cost is usually less than the correctness debt.
