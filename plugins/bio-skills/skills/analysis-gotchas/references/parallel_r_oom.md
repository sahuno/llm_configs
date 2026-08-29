# Parallel R (mclapply) silent OOM and the per-iteration gc() pattern

Generalizes the DSS-specific lesson in `references/dss.md` to any large parallel-R workload (cv.glmnet sweeps, BSseq smoothing, Seurat per-sample loops, anything `parallel::mclapply`-driven on SLURM with cgroup memory limits).

## The failure mode
- **Symptom**: `mclapply` script writes `=== DONE ===` to stdout but the result has missing rows or NULL entries. SLURM `sacct -j <id>` shows `OOM_KILL` events even though exit status is 0:0.
- **Why**: forks exceeding the cgroup memory limit are SIGKILL'd by the kernel. `mclapply` collects NULL for each killed fork and continues. The parent process completes; the result is silently incomplete.
- **Empirical magnitude**: M5 genome-wide elastic net run 1 (mem-per-cpu 8 G, no per-iter gc): 173 oom_kill events, 3,608 of 15,479 genes missing. Run 2 (mem-per-cpu 16 G + gc): zero OOM, 15,050 genes recovered. Same data, same script logic — only the gc() and mem bump differed.

## The fix (apply both — mem alone doesn't solve it)
1. **Add `gc(verbose = FALSE)` at the END of the per-iteration function** (just before `return`). This is the bigger win — copy-on-write pages otherwise accumulate across iterations within each worker as glmnet/BSseq/etc. write back to "shared" pages.
2. Bump `--mem-per-cpu` (not just `--mem`) — the per-fork memory budget is what the cgroup enforces. 16 G/cpu is a safe baseline for genome-scale per-gene workloads with mid-size matrices.
3. Always cross-check after a "successful" run:
   - `sacct -j <id> --format=State,MaxRSS,ReqMem` — `State` must be `COMPLETED`, not `OOM_KILL` or `OUT_OF_MEMORY`.
   - Post-rbindlist NULL count: any `mclapply` aggregation must check that `nrow(result)` matches `expected_n` per chunk and warn loudly otherwise.
   - Stderr scan for `oom_kill events: N` — N must be 0.

## Anti-patterns
- Trusting only the script's own end-of-run summary. The script can't see its own dropped forks.
- Bumping `--mem` (node-total) without `--mem-per-cpu`. SLURM's cgroup is per-task, not per-node.
- Adding gc() only at the top of the function. The point is to release after each iteration's heavy allocations, not before they happen.
- Setting `mc.preschedule = FALSE` "to make it more reliable" — that re-runs failed forks but doesn't fix the OOM cause; the same fork OOMs again next time.

## Cross-references
- `references/dss.md` — DSS-specific instance of this exact pattern (DMLtest's `mclapply` silently OOMing on whole-genome BSseq, with the additional twist that DSS recycles the short result vector and writes wrong dispersion estimates to wrong CpGs).
- `mskcc-hpc` skill → `references/slurm_mcp.md` — for the `--mem` vs `--mem-per-cpu` interaction with slurm-mcp.
- `references/cv_at_small_n.md` — for why this matters more in small-n CV: a single dropped gene becomes a silent NA in the leaderboard, and seed instability already makes per-gene Q² noisy.
