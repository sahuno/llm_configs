---
name: analysis-gotchas
description: |
  Empirically confirmed failure modes in genomics analysis tools that fail
  SILENTLY — producing plausible-looking output that is wrong. Use this skill
  proactively whenever the work involves: DSS / DMLtest / differential
  methylation, parallel R (mclapply, cv.glmnet, BSseq, Seurat per-sample
  loops) on SLURM, regularized cross-validation at small n (n < 50),
  data.table::fread on BED files, Clair3 / ClairS variant calling, Severus
  SV or viral-integration calling, or reporting any aggregated summary
  statistic in a doc, caption, or manuscript. Also consult before trusting
  the output of any long parallel R job that "completed successfully".
  Each reference records the symptom, the confirmed root cause, the fix, and
  a verification step.
version: 1.0.0
---

# Analysis gotchas

Failure modes here were confirmed on real runs, with dates and magnitudes. They
share one property: **the job exits 0 and writes output.** Nothing looks wrong
until the numbers are checked against ground truth.

Read the reference file that matches the tool in play before trusting results.

## When to read what

| If the work involves | Read | The silent failure |
|---|---|---|
| DSS, `DMLtest`, differential methylation | `references/dss.md` | `detectCores()` ignores the SLURM cgroup; OOM-killed forks return NULL, dispersion estimates get recycled onto the wrong CpGs. DMR counts inflated 10–20×. |
| Any `parallel::mclapply` on SLURM | `references/parallel_r_oom.md` | Dropped forks become NULL; the script still prints `=== DONE ===`. |
| `cv.glmnet`, nested CV, n < 50 | `references/cv_at_small_n.md` | Seed-fragile selection, permutation-FDR q-floor, Pearson r degenerate on near-constant LOOCV predictions. |
| `data.table::fread` on BED | `references/fread_bed_quirks.md` | `skip="chr"` does NOT skip a `#chr\tstart...` header; the error surfaces lines later as a type failure. |
| Clair3 / ClairS | `references/clair3.md` | argparse treats `False` as truthy so phasing can't be disabled by flag; ClairS SIF ships an empty `/opt/models`. |
| Severus (SV / viral integration) | `references/severus.md` | `--min-reference-flank` default silently zeroes out every contig < 20 kb; integrations emit as `INS`, not `BND`, so CHROM/ALT filters miss all of them. |
| Reporting any mean / median / rate | `references/numerical_claims.md` | Aggregation method changes the value 5–20 %; an unstated method is not reproducible. |

## The general rule

For any long parallel job on SLURM, exit code 0 is not evidence of success.
Cross-check before using the results:

```bash
sacct -j <jobid> --format=JobID,State,MaxRSS,ExitCode   # State must not be OUT_OF_MEMORY
grep -c 'oom_kill events' <stderr>                       # must be 0
```

Then verify the output's row count or record count against what the input
implies. A result that shrank without an explanation in the log is a dropped
fork, not a filter.
