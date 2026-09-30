---
tool: deeptools
version_observed: "3.5.6"
date: 2026-09-17
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  # a '#' first line in a BED passed to computeMatrix becomes a group separator
  awk 'NR==1 && /^#/ {print "BED starts with a # line: computeMatrix will split groups"; exit 1}' regions.bed
---
# deeptools gotchas

Established 2026-09-17 during the TSS-profiling filter build
(`REP_locusSpecDE/results/20260917_mm10_tss_profiling`). Each item below cost a
failed run or would have silently corrupted a result.

## Silent-corruption traps

- **A `#` line inside a BED passed to `computeMatrix` is a REGION GROUP SEPARATOR,
  not a comment.** This directly contradicts the house rule that BED-like outputs
  carry a `#`-prefixed header. Adding the house header to a region BED silently
  splits it into bogus groups and every group-wise mean afterwards is wrong, with
  no error. Region BEDs fed to deeptools must have **no** header line. Document the
  exemption in the script that writes them.

- **`plotHeatmap --kmeans` exposes no random seed.** Cluster *numbering* — and at
  poorly separated k, membership — shifts between reruns. Never re-run `--kmeans`
  to regenerate a figure in a second format (png then pdf then svg gives three
  different clusterings). Run it once, treat `--outFileSortedRegions` as the
  authoritative record, and build every downstream figure and join from that file.

- **`--skipZeros` drops all-zero regions at the `computeMatrix` stage**, so the
  matrix can have fewer rows than the input BED and any join keyed on "all N
  regions" breaks. Always log `input_rows -> retained_rows`. In a misattribution
  analysis the dropped rows are exactly the interesting ones, so the drop count
  belongs in the result, not just the log.

## Flags and syntax

- **`--region` takes `chr:start:end` (colon-separated), not `chr:start-end`.**
  The samtools-style form fails with a confusing
  `ValueError: invalid literal for int() with base 10: '142900000-142910000'`
  from `mapReduce.getUserRegion`.

- **`--filterRNAstrand` assumes a dUTP / fr-firststrand library** (read1 antisense
  to the transcript). If the library really is fr-firststrand, use the flag as-is
  with **no inversion**: `forward` gives transcripts from (+)-strand features,
  `reverse` from (−)-strand. Verify the library empirically rather than trusting a
  config — count read1 orientation over highly expressed genes of known strand:
  `samtools view -c -f 65 -F 3868` (read1 forward) vs `-f 81 -F 3852` (read1 reverse).
  **Watch the mask:** `-F 3868` contains `0x10`, so it excludes reverse-strand reads;
  using it for both counts makes every gene look 100% one-sided, and using `-f 65`
  alone applies no strand filter at all and returns the total.

- **`--filterRNAstrand` forces a full BAM pass** to compute the normalization factor,
  so stranded `bamCoverage` runs are much slower than unstranded ones. Do not size
  the wall-time from an unstranded benchmark. On MSKCC HPC this rules out `cpushort`
  (2 h limit) for genome-wide `--binSize 1` on multi-GB BAMs — use `componc_cpu`.

- **`computeMatrixOperations rbind`** is the way to build a strand-aware matrix:
  compute `(+)`-strand regions against the `forward` bigWigs and `(−)`-strand
  regions against the `reverse` bigWigs, then `rbind`. Pass identical
  `--samplesLabel` to both halves or the rbind is rejected.

## Environment

- **`mamba create ... deeptools` now resolves to 4.0.0.** For work reproducing a
  paper from the 3.5.x era, pin explicitly (`deeptools=3.5.6`). All the flags used
  by the Savytska 2022 method (`--filterRNAstrand`, `--kmeans`, `--silhouette`,
  `--skipZeros`, `--missingDataAsZero`) exist in both, so a version drift would not
  error — it would just quietly not be the same software.

- `bigwigAverage` and `computeMatrixOperations` require deeptools ≥ 3.5.4.

- The deeptools conda env's `python` may not win on `PATH` after `conda activate`
  if another env is already active; inline `python -c` then imports from the wrong
  env and `pyBigWig` appears "missing". Call `"$CONDA_PREFIX/bin/python"` explicitly
  in scripts. The deeptools entry points themselves are unaffected (they carry an
  absolute shebang).

## bigWig comparisons across bin sizes

- **Never compare `pyBigWig.stats(type="mean")` between tracks of different bin size.**
  On a 1-bp track it averages only *covered* bases; on a binned track, uncovered
  positions inside a bin count as zeros. Over a long, sparsely covered region (an
  RNA-seq gene body) this alone produced a spurious 12.7% discrepancy that looked like
  a `bigwigAverage` bug. Compare at matched resolution, or compare the computeMatrix
  output instead — `computeMatrix --binSize` re-bins every input to a common
  resolution, so matrices built from 1-bp and from pre-binned tracks agree (verified to
  within 2%).

- `bigwigAverage` on genome-wide mm10 tracks: ~9 min per condition with 8 cpus on a
  dedicated `componc_cpu` node, ~70 min for the same work on a contended login/
  interactive node. Do not size SLURM allocations from interactive-node timings.
