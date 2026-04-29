# Stage design — choosing factors, levels, replicate counts

How to pick what to vary in each stage so the study produces a useful answer
without wasting compute.

## Generic principles

- **Cover orders of magnitude, not arithmetic ranges.** Threads of {1, 2, 4, 8, 16, 32}
  is informative; {1, 2, 3, 4, 5, 6} is not. Memory of {64M, 128M, 512M, 2G, 8G}
  spans the spill threshold; {1G, 2G, 3G, 4G, 5G} doesn't.
- **Anchor on a baseline that's "near the middle" of expected use.** All OFAT sweeps
  hold others at the baseline; the baseline shouldn't be at a regime boundary.
- **3 reps for OFAT, 3 for factorial, 5+ for build-mode/alt-impl, 3 for validation**.
  Variance grows when comparing alternatives, so build-mode comparisons need more reps
  to detect small effects.
- **Aim for ~50 jobs per stage**. Below that you can't see variance; above that you're
  paying without learning.

## Factor menu by tool class

### Sorting tools (samtools sort, sambamba sort, Picard SortSam)

| Factor | Typical levels | Why it matters |
|---|---|---|
| Threads (`-@`) | 1, 2, 4, 8, 16, 32 | Primary parallelism axis; nearly always the dominant effect |
| Memory per thread (`-m`) | 64M, 128M, 512M, 2G, 8G | Spill / no-spill transition |
| Compression (`-l`) | 0, 1, 6, 9 | Output bgzf level — `-l 9` is a trap on long-read mod-base BAMs |
| Tmp dir (`-T`) | node-local, parallel FS | Affects spill performance only |
| Sort key | coord, name | Different memory profile |
| Output format | BAM, CRAM | CRAM costs CPU |

### Aligners (bwa mem, minimap2, winnowmap, dragmap)

| Factor | Typical levels | Why it matters |
|---|---|---|
| Threads (`-t`) | 1, 4, 8, 16, 32 | Primary parallelism |
| Index in shared mem (`-K` for bwa) | on, off | Critical for fan-out |
| Batch size (`-K`) | 100M, 500M, 5G | Throughput vs latency |
| Output format | SAM, BAM streamed | I/O cost |
| Build mode | container, conda, native | NFS cold-start tax (see `rules/apptainer_vs_conda.md`) |

### Variant callers (DeepVariant, GATK HaplotypeCaller, Clair3, bcftools call)

| Factor | Typical levels | Why it matters |
|---|---|---|
| Threads / shards | 1, 4, 8, 16 | Parallel region processing |
| Region size | 1Mb, 10Mb, 50Mb, full chromosome | Memory vs scheduler overhead trade-off |
| Output format | VCF, GVCF, BCF | I/O |
| Quality threshold | tool-specific | Often pruning input early helps |

### Methylation tools (modkit pileup, methyldackel, nanopolish)

| Factor | Typical levels | Why it matters |
|---|---|---|
| Threads | 1, 4, 8, 16, 32 | Primary parallelism (modkit scales sub-linearly above 16) |
| Region | full genome, chrom subset | Per-chromosome benchmarking is honest |
| Min coverage filter | 1, 5, 10 | Skips low-coverage CpGs early |

## Level selection heuristics

### Threads

- Always test 1, 2, 4, 8, 16, 32 if the tool supports it. Half-octave intervals.
- Stop at the physical core count of the partition (cpushort: 56 cpus, so test up to 32
  or 56).
- Hyperthreaded levels rarely help compute-bound tools (samtools sort showed t=32 still
  scaled, but with widening variance — likely starting to compete for L3 cache).

### Memory

- Span the spill threshold. For samtools sort on long-read BAMs the threshold was at
  `-m × threads ≈ working_set`. For your tool, you may have to find it empirically.
- Use 64M, 128M, 512M, 2G, 8G as a starting set; add levels in the regime where the
  curve bends.

### Compression / serialisation

- Always test `0, 1, 6, 9` (or equivalent extremes). The cost ratio between extremes is
  often surprising — `-l 9` was 8.4× slower than `-l 1` in samtools sort.

### Tmp dir / scratch

- Test node-local (`/tmp` or `$TMPDIR`) vs the parallel FS where the project lives.
- Only worth testing in the spill regime (small `-m`).

### Build mode

- container (SIF) vs conda vs native (if a native build exists).
- 5+ replicates each. The signal is often within noise of conda variance.
- See `rules/apptainer_vs_conda.md` for the cold-start-tax rationale.

### Alternative implementation

- Always include ≥1. Don't optimise inside the wrong well.
- Match the input format and output expectation. If sambamba sort produces a BAM that
  picard would re-sort anyway, the comparison isn't meaningful.

## Replicate-count guide

| Stage | Replicates | Reasoning |
|---|---|---|
| Pilot | 1–2 | Just verifying the pipeline works |
| OFAT (Stage 2) | 3 | Effects are typically large; 3 reps catch CV>20% outliers |
| Factorial (Stage 3) | 3 | Same as OFAT; total job count is the constraint |
| Build mode (Stage 4) | 5+ | Effects are typically small; need power to detect |
| Alt-impl (Stage 4) | 5+ | Same as build mode |
| Input-size scan (Stage 5) | 3 per size | Linear regression handles per-size variance |
| Validation (Stage 6) | 2–3 | One per held-out input; each is independent |

## Calibration input selection

- **Big enough** that the tool isn't dominated by startup overhead. Rule of thumb: the
  tool should take >30s wall at the baseline config.
- **Small enough** to iterate fast. Rule of thumb: <5 min wall at the baseline config.
- For BAMs: chromosome subsets work well (e.g., chr17 of a WG BAM).
- For VCFs: a region subset (`bcftools view -r chr17`).
- For FASTQs: subsample to ~5M reads.
- Document the calibration input in `Stage0_setup.md` so reruns use the same one.

## Sample-size checks

Before launching, sanity-check:

- **Total jobs**: `n_factors × levels × reps` for OFAT, `2^k × reps` for factorial.
  Aim for 30–80 per stage.
- **Total wall time**: `total_jobs / parallelism × per_job_wall`. cpushort has ~50
  idle nodes; if your study is 60 jobs at 30s each, expect ~10 min wall total.
- **SLURM `--time` per job**: 2× expected median wall, capped at the partition's max
  (cpushort: 2 h).
- **SLURM `--mem` per job**: 1.5× predicted RSS (use `rss_model` from a previous study
  if available, otherwise allocate generously and refine).
