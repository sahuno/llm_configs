# Gather methods — format by format

`cat` is almost never correct. Each format has a tool that handles header reconciliation, sort order, sample alignment, or binary structure. Always regenerate indexes on the gathered output.

## BAM / CRAM

```bash
# Preferred: samtools merge (handles @SQ ordering and @PG dedup)
samtools merge -c -p -@ 8 gathered.bam shards/*.bam
samtools index -@ 8 gathered.bam

# CRAM needs the reference
samtools merge -c -p -@ 8 --reference "${FASTA}" gathered.cram shards/*.cram
samtools index -@ 8 gathered.cram
```

Flags:
- `-c` — combine `@RG` headers from input files with same ID instead of erroring.
- `-p` — combine `@PG` headers with same ID. Without this, each shard's `@PG` chain accumulates and the gathered header explodes.

**Don't use `samtools cat`** unless you can guarantee shards are disjoint AND already coordinate-sorted in compatible order — `cat` does no header reconciliation.

**Sanity checks**:
```bash
samtools quickcheck gathered.bam            # corruption
samtools idxstats gathered.bam | awk '$3+$4>0' | wc -l   # contigs with reads
```

For per-chrom scatter, `idxstats` should list every chromosome in the scatter set with non-zero counts.

## VCF / BCF

Two cases — keep them straight:

### Same samples across shards (per-region scatter of one cohort)

```bash
bcftools concat -a -O z --threads 8 -o gathered.vcf.gz shards/*.vcf.gz
bcftools index --tbi gathered.vcf.gz
```

`-a` allows overlaps (region scatter with padding); for chrom scatter (no overlaps), drop `-a`. Sample columns must match across shards — `bcftools concat` errors otherwise.

### Different samples across shards (cohort merge, not concat)

```bash
bcftools merge -O z --threads 8 -o cohort.vcf.gz \
    sample_A.vcf.gz sample_B.vcf.gz sample_C.vcf.gz
bcftools index --tbi cohort.vcf.gz
```

This is a different operation — union of sample columns at each locus, not concat of loci. Don't confuse.

### gVCF cohort

```bash
# Combine per-sample gVCFs across the cohort (memory-heavy)
gatk GenomicsDBImport --genomicsdb-workspace-path my_db \
    -V s1.g.vcf.gz -V s2.g.vcf.gz -V s3.g.vcf.gz \
    -L scatter_intervals.list

# Then per-region joint genotyping (this is itself scatter-friendly)
gatk GenotypeGVCFs -R "${FASTA}" -V gendb://my_db -L chr1 -O joint.chr1.vcf.gz
# ... gather joint.chrN.vcf.gz with bcftools concat
```

**Sanity checks**:
```bash
bcftools view gathered.vcf.gz > /dev/null && echo "sort OK"
bcftools query -l gathered.vcf.gz | wc -l    # sample count
zcat gathered.vcf.gz | grep -v '^#' | awk '{print $1}' | sort -u   # contigs present
```

## BED / BEDGRAPH / bedMethyl

Plain text, sort + merge.

```bash
# Concat then sort
cat shards/*.bed | sort -k1,1 -k2,2n > gathered.bed

# For region scatter with overlapping tiles, dedupe boundary entries:
sort -k1,1 -k2,2n shards/*.bed | uniq > gathered.bed
# or, for "merge overlapping intervals":
sort -k1,1 -k2,2n shards/*.bed | bedtools merge -i - > gathered.bed
```

**Preserve `#`-prefixed headers** (CLAUDE.md §2 Genomic Output Conventions):
```bash
# Take header from first shard, body from all
HEADER_LINE=$(head -1 shards/$(ls shards/ | head -1))
{ echo "$HEADER_LINE"; \
  for s in shards/*.bed; do tail -n +2 "$s"; done | sort -k1,1 -k2,2n; \
} > gathered.bed
```

For bedMethyl specifically (modkit output): dedupe by `(chr, start, modtype, strand)` — the relevant unique key is wider than just position because the same CpG carries multiple modtype rows (5mC, 5hmC).

For BEDGRAPH being converted to bigwig, sort first then convert:
```bash
sort -k1,1 -k2,2n gathered.bg > gathered.sorted.bg
bedGraphToBigWig gathered.sorted.bg "${SIZES}" gathered.bw
```

**Sanity check**:
```bash
sort -c -k1,1 -k2,2n gathered.bed && echo "sort OK"
wc -l shards/*.bed | tail -1   # sum of shard line counts
wc -l gathered.bed             # gathered count (≈ sum, with boundary tolerance)
```

## bigwig

Use UCSC `bigWigCat` — it concatenates without re-sorting and without going through bedGraph:

```bash
bigWigCat gathered.bw shards/chr1.bw shards/chr2.bw shards/chr3.bw ...
```

Shards must be from non-overlapping regions and in chrom-sorted order. For region scatter with overlaps, you have to round-trip through bedGraph:

```bash
for s in shards/*.bw; do bigWigToBedGraph "$s" "${s%.bw}.bg"; done
sort -k1,1 -k2,2n shards/*.bg | uniq > gathered.bg
bedGraphToBigWig gathered.bg "${SIZES}" gathered.bw
```

**Sanity check**: `bigWigInfo gathered.bw` — check `chromCount`, `basesCovered`.

## FASTQ

Generally not a scatter-gather target — reads aren't naturally partitioned by genomic position pre-alignment. The exception: post-alignment partitioning (BAM → per-chrom BAM → per-chrom BAM-to-FASTQ). For that case:

```bash
cat shards/*.fastq.gz > gathered.fastq.gz   # OK if shards are disjoint reads
```

**Don't shuffle**. If downstream needs paired reads in sync, use `samtools collate` upstream.

## TSV / CSV with header

```bash
# Header from first, body from all
head -1 shards/$(ls shards | head -1) > gathered.tsv
for s in shards/*.tsv; do tail -n +2 "$s"; done >> gathered.tsv
```

Or with awk in one pass:
```bash
awk 'FNR==1 && NR!=1 {next} {print}' shards/*.tsv > gathered.tsv
```

Watch for type promotion across shards (a column that was int in shard 1 and float in shard 17). Common in DataFrame round-trips through pandas.

## HDF5 / Zarr

Format-specific concat. Watch chunking — the chunk axis you concat on should match the chunk dimension, or you'll cause a full rewrite.

```python
# Zarr: concat along an axis
import zarr
import dask.array as da
arrs = [da.from_zarr(f"shards/{c}.zarr") for c in CHROMS]
out = da.concatenate(arrs, axis=0)
out.to_zarr("gathered.zarr")
```

```python
# h5py: copy datasets shard-by-shard
import h5py
with h5py.File("gathered.h5", "w") as out:
    for c in CHROMS:
        with h5py.File(f"shards/{c}.h5", "r") as inp:
            out.create_dataset(c, data=inp["data"][:])
```

For large arrays, prefer Zarr or per-chrom datasets in HDF5 over a single concatenated array — avoids the rewrite.

## Index regeneration

After every gather, regenerate the index. Old shard indexes do not roll forward.

| Format | Index | Command |
|---|---|---|
| BAM | `.bai` / `.csi` | `samtools index -@ 8 gathered.bam` |
| CRAM | `.crai` | `samtools index -@ 8 gathered.cram` |
| VCF.gz | `.tbi` / `.csi` | `bcftools index --tbi gathered.vcf.gz` |
| BED.gz / GFF.gz | `.tbi` | `tabix -p bed gathered.bed.gz` (or `-p gff`) |
| FASTA | `.fai` | `samtools faidx gathered.fa` |
| bigwig | (built-in) | none — already self-indexed |

The freshness check:
```bash
test gathered.vcf.gz.tbi -nt gathered.vcf.gz || echo "STALE INDEX — regenerate"
```
