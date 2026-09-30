# Logging and audit trail: full specification

Moved from CLAUDE.md §2 on 2026-09-30. The rule itself (every analysis script writes a timestamped log with these categories) stays in CLAUDE.md.

### Logging and Audit Trail (Mandatory for all analysis scripts)

Every analysis script must produce a **timestamped log file** that captures enough detail to reproduce or debug the run without re-executing it. Log files go in a `logs/` directory relative to the script's output location.

**Log infrastructure setup** (do this at the top of every script, after argument parsing):
- **R**: Use `sink(log_con, type = "output", split = TRUE)` + `globalCallingHandlers(message = ...)` to capture both `cat()`/`print()` output and `message()` to a single log file while still printing to console. Always close with `on.exit({ sink(type = "output"); close(log_con) }, add = TRUE)`.
- **Python**: Use `logging` module with a `FileHandler` (to log file) + `StreamHandler` (to console). Set format: `"[%(asctime)s] %(levelname)s: %(message)s"`. Never use bare `print()` for status updates — use `logger.info()`.
- **Bash**: Redirect with `exec > >(tee -a "$LOG_FILE") 2>&1` at script start. Define a `log_msg()` function: `log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }`.

**Log file naming**: `logs/{script_name}_{YYYYMMDD_HHMMSS}.log`

**What to log** — every script must emit these categories:

1. **Session header** (first lines of log):
   - Timestamp, language version, working directory, log file path
   - Script name and all command-line arguments / parameter values used
   - Key library versions (e.g., DESeq2, Seurat, pandas version)

2. **Data loading and dimensions**:
   - After every `read`/`fread`/`pd.read_*`: log file path, rows, columns
   - Example: `"Loaded counts matrix: 32,415 genes x 12 samples from data/counts.tsv"`

3. **Filtering and data drops** (the most critical category):
   - **Before and after counts** for every filter operation
   - What was filtered and why (threshold, criterion)
   - Example: `"Filtering low-count genes (min 50 reads in ≥3 samples): 32,415 → 18,203 genes (14,212 removed)"`
   - Example: `"Dropping samples: R.S.2, R.C.3 | Remaining: 10 samples"`
   - For QC filters: log the distribution of the metric before filtering (min, median, max)

4. **Merges and joins**:
   - Log both input dimensions and result dimensions
   - Log any rows lost (anti-join) or gained (many-to-many)
   - Example: `"Inner join metadata × counts: 12 × 12 → 10 matched (2 metadata-only, 0 counts-only)"`

5. **Sanity checks and validation**:
   - Alignment of sample order between matrices (critical for DESeq2, Seurat)
   - Cross-checks (e.g., "All count matrix columns match metadata rows: TRUE")
   - Expected vs actual value ranges (e.g., log2FC range, p-value distribution)

6. **Analysis milestones** (use section markers: `=== Section Name ===`):
   - Major steps: `"=== Running DESeq2 for CKi vs DMSO contrast ==="`
   - Result dimensions: `"CKi vs DMSO results: 18,203 x 7"`
   - Key summary stats: number of DEGs at threshold, GSEA term counts, cluster counts

7. **Output file confirmation**:
   - After every file write: log path, dimensions, and file size if practical
   - Example: `"Saved: data/processed/deseq2_results.tsv (18,203 genes x 7 columns)"`
   - For figures: `"Saved: results/20260302_v1/figures/pdf/volcano_CKi_vs_DMSO.pdf (+ png, svg)"`

8. **Warnings and errors**:
   - Catch and log warnings (don't suppress them): `tryCatch(..., warning = function(w) message("WARNING: ", w$message))`
   - On error, log the full error message before stopping

9. **Session footer** (last lines of log):
   - Total runtime: `"Completed in 4m 32s"`
   - `sessionInfo()` (R) or `uv pip freeze` / the `uv.lock` file (Python) for full reproducibility

10. **End-of-script marker** (mandatory — the very last line of every script):
    - Every script must end with an explicit completion message so it is unambiguous whether the script ran to the end or died silently mid-execution.
    - **R**: `message("[", Sys.time(), "] === DONE: {script_name} completed successfully ===")`
    - **Python**: `logger.info("=== DONE: {script_name} completed successfully ===")`
    - **Bash**: `log_msg "=== DONE: $(basename "$0") completed successfully ==="`
    - If this line is absent from the log file, the run did not finish.

**Anti-patterns — do NOT**:
- Use bare `print()` or `cat()` without routing to the log file
- Log only to console (everything must also reach the log file)
- Skip logging for "small" filtering steps — every row/column change matters
- Hardcode log paths — accept `--log_dir` as a command-line argument with default `"logs"`

Close a session with `/wrapup`, which appends the five required fields below to
the project's `PROGRESS.md` ledger and updates its header.
