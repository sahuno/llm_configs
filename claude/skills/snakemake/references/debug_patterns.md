# Common Debug Patterns

## Symptom → Diagnosis → Fix Table

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `improperly formatted strand field 3014751` | Input BED has >6 columns; modkit expects BED3-BED6 | User must provide properly formatted BED (don't auto-fix inputs) |
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8b` | Script using `open()` on a `.gz` file; `0x8b` is gzip magic byte | Use `gzip.open(path, "rt")` for `.gz` files |
| Job completes in <5 seconds (too fast) | Container not activated; rule ran bare on compute node | Check `singularity:` directive on the rule + `--use-singularity` on CLI |
| `SLURM_MEM_PER_NODE` vs `SLURM_MEM_PER_CPU` fatal | Missing `mem_mb: 0` in profile, or coordinator uses `--mem` | Add `mem_mb: 0`; use `--mem-per-cpu` for coordinator |
| `ModuleNotFoundError: No module named 'pandas'` on compute node | Rule missing `singularity: IMG` directive | Add `singularity: IMG` to the rule |
| `pd.read_csv` silently converts "NA" to NaN | pandas auto-parses "NA" as missing | Use `dropna()` for filtering, never `!= "NA"` string comparison |
| `Nothing to be done` but outputs are missing | Outputs exist from a previous run at the same path | Check output paths; use a new `output_dir` for each run |
| `MissingInputException` for a file that exists | Chr prefix mismatch between BED and BAM, or file moved | Check `bed_chr_mode` in config; verify paths haven't changed |
| DAG builds but jobs fail silently | Missing `slurm_account` in default-resources | Add `slurm_account` to default-resources |
| `sacctmgr: not found` | Running Snakemake directly on login node | Submit coordinator as SLURM job |
| Workflow re-runs everything after adding samples | `output_dir` changed between runs | Use the same `output_dir` when adding samples to an existing cohort |
| `benchmark:` file empty or missing | Rule failed before completing | Check the log; benchmark is only written on success |
| `Error: Directory cannot be locked` | Stale lock from killed coordinator | `snakemake --unlock` then resubmit with `--rerun-incomplete` |
| `No rule to produce` for valid targets | Whitespace in sample names or paths in sample sheet | Check sample sheet for whitespace issues |
| Double container invocation | Rule has `singularity:` directive AND `singularity exec` in shell | Remove `singularity exec` from shell — the directive handles it |

## Debugging Workflow

1. **Read the error message completely** before suggesting fixes
2. **Check logs first**: `.snakemake/log/` for Snakemake logs, `{output_dir}/logs/` for rule logs
3. **Check job status**: `sacct -j <jobid> --format=JobID,State,ExitCode,MaxRSS,Elapsed`
4. **Common failure modes**:
   - Out of memory: increase `mem_mb_per_cpu` (not `mem_mb`)
   - Missing input: trace DAG backward to find failed upstream rule
   - Container errors: verify bind paths cover all input/output directories
   - SLURM timeout: check actual runtime with `sacct`, increase time limit
5. **Never re-run entire pipeline** for a single failed step — use `--rerun-incomplete`
6. **Force-rerun a specific rule**: `snakemake --forcerun rule_name`

## Profile Validation Checklist

When debugging SLURM issues, verify the profile has:
- [ ] `mem_mb: 0` in default-resources
- [ ] `slurm_account` in default-resources
- [ ] No `mem:` keys anywhere
- [ ] `singularity-args:` (no `--` prefix)
- [ ] `--use-singularity` on coordinator CLI (not just in profile)
