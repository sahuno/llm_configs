# CLAUDE.md — Samuel Ahuno (ekwame001@gmail.com)
# Computational Biologist, Greenberg Lab (greenbab), MSKCC
# Languages: Python, R, Bash | HPC: SLURM | Organisms: Mouse & Human

---

## 1. Session Initialization

On every new conversation, do the following in order:

1. **Ask the user** to classify the session:
   - **Domain**: Bioinformatics Analysis | Software Development | AI Engineering
   - **Status**: Fresh project or continuation of existing project
   - **Aim**: Ask for a clear, numbered list of objectives
2. **If continuing**, read the relevant project file from `~/projects/` before proceeding.
3. **If fresh**, create a project markdown file at `~/projects/<slug>.md` with date, domain, and aims.
4. **Search `~/memories/`** for any notes relevant to the current query before answering.
5. **For analysis projects**, scaffold the directory structure automatically:
   ```
   <project_root>/
   ├── data/inbox/         # Staging area for receiving data — review before promoting to raw/
   ├── data/raw/           # IMMUTABLE — never write here after initial deposit
   ├── data/processed/
   ├── src/
   ├── results/
   ├── figures/{png,pdf,svg}/
   ├── workflows/{wf_snakemake,wf_nextflow}/
   └── docs/
   ```
   Create these directories safely (mkdir -p). Place every generated file in the appropriate subdirectory.
   **Each directory must have a `README.md`** describing its purpose, contents, and any scripts within it. Keep READMEs up to date as files are added or changed — especially in `src/` and `workflows/`, where each script should be listed with a one-line description.
6. **Append progress** to the project file at `~/projects/` as work proceeds — record decisions, parameters, and paths so a future session can resume without re-discovery.

### Project File Content Requirements (minimum for resumption)
Every project file update must include:
1. **What was done** — completed steps with specifics, not just "worked on X"
2. **Key file paths** — absolute paths to files created or modified
3. **Commands that worked** — copy-paste ready for the next session
4. **Known issues / blockers** — what failed and why
5. **Exact next steps** — numbered, actionable items for the next session

---

## 2. Universal Rules (Apply to ALL Work)

### Data Integrity
- **Never modify raw data.** All transformations produce new files in `data/processed/`.
- **Never overwrite input files.** Read from source, write to a new path.
- **Set random seeds** for every stochastic operation (default seed: 42 unless user specifies otherwise).
- **Use relative paths** in all scripts and configs. Never hardcode absolute paths.

### Naming and Variables
- **Forbidden variable names** (clash with builtins): `conditions`, `counts`, `results`, `sum`, `median`, `mean`.
- **Script naming**: Use numbered prefixes for sequential steps: `01_download.py`, `02_align.sh`, `03_call_variants.py`.
- **File naming**: lowercase, underscores, no spaces. Include organism/genome build when relevant.

### Genomics-Specific
- **Never hardcode contig names or sizes.** Always parse them from the user-supplied genome sizes file or the reference FASTA index.
- **Reference data**: Load paths from `profiles/databases/databases_config.yaml`. Supported genomes: mm10, mm39, hg38, T2T-CHM13, GRCh37. Each entry has fasta, gtf, chrom.sizes, and CpG island paths (local + S3).

### Multi-Genome-Build Projects
- Some integrative analyses require data from different genome builds (e.g., RNA in mm39, methylation in mm10).
- Always use **liftOver** for coordinate conversion. Store both original and lifted coordinates.
- Name intermediate files with BOTH builds when applicable: `{sample}.mm39_to_mm10.lifted.bed`
- Keep a **coordinate mapping manifest** to track which genome build each file uses.
- When merging data across builds, always verify that the liftOver was successful (check for unmapped regions) before proceeding.

### Genome Build Tagging (Mandatory for all genomic output files)
- **Every genomic output file must include the genome build in both the filename and parent directory.**
  - Directory: `data/processed/{genome_build}/`
  - Filename: `{sample}.{genome_build}.{description}.{ext}` — tag goes immediately after the sample name.
  - Example: `data/processed/hg38/patient01.hg38.sorted.bam`, `data/processed/mm10/sample3.mm10.methylation.bed`
- **Valid genome tags**: `mm10`, `mm39`, `GRCm39`, `hg38`, `GRCh38`, `hg19`, `GRCh37`, `t2t`, `chm13`.
- **File types that require tagging**: `.bam`, `.cram`, `.bai`, `.bed`, `.bedgraph`, `.bedMethyl`, `.narrowPeak`, `.broadPeak`, `.vcf`, `.vcf.gz`, `.bcf`, `.bigwig`, `.bw`, `.bigbed`, `.gtf`, `.gff` (processed copies), count matrices.
- **File types exempt from tagging**: raw data (`.fastq`, `.fq`, `.pod5`), figures, scripts, configs, logs, summary reports.

### Documentation
- **Every script**: Add author (`Samuel Ahuno`), date, and a one-line purpose comment at the top.
- **Every function**: Docstring with parameters, returns, and a minimal example.
- **Every directory**: If the user requests documentation, provide a README. Do not create READMEs proactively.

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
   - For figures: `"Saved: figures/pdf/volcano_CKi_vs_DMSO.pdf (+ png, svg)"`

8. **Warnings and errors**:
   - Catch and log warnings (don't suppress them): `tryCatch(..., warning = function(w) message("WARNING: ", w$message))`
   - On error, log the full error message before stopping

9. **Session footer** (last lines of log):
   - Total runtime: `"Completed in 4m 32s"`
   - `sessionInfo()` (R) or `pip freeze` equivalent (Python) for full reproducibility

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

### Persistent Directories
| Purpose  | Path                    |
|----------|-------------------------|
| Scripts  | `~/code/claude-scripts` |
| Memory   | `~/memories`            |
| Journal  | `~/journal`             |
| Ideas    | `~/ideas`               |
| Todos    | `~/todos`               |
| Projects | `~/projects`            |

---

## 3. Domain Playbook: Bioinformatics Analysis

### 3A. ONT Methylation Pipeline (pod5 to DMRs)

**Standard chain**: pod5 -> dorado basecall -> dorado align (or minimap2) -> samtools sort/index -> modkit pileup -> modkit dmr

**Tool references**: Load containers from `profiles/software_configs/softwares_containers_config.yaml`.

**QC checkpoints** (stop and report if any fail):
1. After basecalling: Check read N50, total bases, pass/fail ratio from dorado summary.
2. After alignment: Confirm mapping rate >80%, check flagstat for unexpected supplementary/secondary rates.
3. After modkit pileup: Verify bedMethyl has expected chromosomes, spot-check coverage distribution.
4. After DMR calling: Sanity-check DMR count; fewer than 10 or more than 100k warrants review.

**Common pitfalls**:
- Dorado models must match the chemistry/flowcell. Always confirm with the user.
- modkit pileup `--ref` must match the alignment reference exactly.
- For mouse samples, CpG islands from `profiles/databases/databases_config.yaml` are essential context for DMR interpretation.

**"Done" looks like**: bedMethyl files per sample, DMR bed file with statistics, summary plots of methylation distributions, and a manifest CSV linking sample metadata to output paths.

**ONT Processing Infrastructure**:
- **Chemistry detection**: ONT runs may have mixed chemistries (4kHz and 5kHz). Always check and process separately. Dorado model must match chemistry exactly — mismatches produce silent garbage.
- **Apptainer cache**: Set `APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache` to avoid home directory quota issues on compute nodes.
- **Primary containers**: `onttools_v2.0.sif` (dorado + samtools), `sahuno/onttools:v3.0` (adds bedtools). Always load from `profiles/software_configs/softwares_containers_config.yaml`.
- **Methylation context**: Standard ONT methylation call string is `5mCG_5hmCG@latest,6mA@latest`.
- **Multi-run samples**: Some patients have multiple sequencing runs. These must be basecalled independently, then merged after alignment — never concatenate raw pod5 files across runs.

### 3B. Variant Calling

| Type | Tool | Notes |
|------|------|-------|
| SNV/Indel (ONT) | Clair3 | Requires model matched to chemistry; use `--platform=ont` |
| SV (ONT) | Sniffles2 | Use `--tandem-repeats` BED when available |
| SNV/Indel (short-read) | GATK HaplotypeCaller | Follow GATK best practices; BQSR then HC then GenotypeGVCFs |

**QC checkpoints**: Check Ti/Tv ratio for SNVs (~2.0-2.1 for WGS, ~2.8 for exome). Check SV size distribution. Filter by QUAL and read support.

**Common pitfalls**: Clair3 model mismatch causes silent garbage. Always verify model version. GATK requires read groups; fail early if missing.

### 3C. RNA-seq / DGE

**Standard chain**: fastp QC -> STAR align (or salmon quant) -> featureCounts -> DESeq2 (R) or pyDESeq2 (Python)

**QC checkpoints**: Verify >70% uniquely mapped (STAR), check PCA for batch effects before DGE, confirm replicate correlation >0.9.

**Defaults**: padj < 0.05, log2FC threshold = 1.0. Always generate MA plot, volcano plot, and PCA. Prompt user about which contrasts to test.

**Common pitfalls**: GTF and genome version mismatch. Salmon index must match the transcriptome version. Always declare the design formula explicitly.

### 3D. scRNA-seq

**Seurat (R)** or **Scanpy (Python)** — ask user which framework unless context is clear.

**Standard chain**: CellRanger (or STARsolo) -> Load counts -> QC filtering (mito%, nFeature, nCount) -> Normalize -> HVG -> PCA -> Harmony/integration if multi-sample -> UMAP -> Clustering -> Marker genes -> Annotation

**QC checkpoints**: Report cells before/after filtering. Show violin plots of QC metrics. Check doublet rate with scrublet or DoubletFinder.

**Common pitfalls**: Over-filtering kills rare populations. Under-filtering adds noise. Always show QC distributions before applying thresholds and get user confirmation. Resolution parameter for clustering should be explored at multiple values.

### 3E. IGV Visualization

Use the igver tool for non-interactive screenshots:
```bash
singularity exec --bind /data1/greenbab \
  /data1/greenbab/software/images/igver_latest.sif igver \
  --input <bams_or_txt_file> \
  -r regions.txt \
  -o "results_IGV_plots" \
  --dpi 600 -d expand -p 1000 \
  --genome '<mm10|hg38|etc>' --no-singularity \
  && touch results_IGV_plots/done.txt
```
Regions file format: `chr1:start-end\tUID-label` (tab-separated, one region per line).

---

## 4. Domain Playbook: Software Development

### Pipeline Development (Snakemake / Nextflow)

**Snakemake rules**:
- There is no `--reason` argument for snakemake. Do not use it.
- If a rule sets the `singularity:` directive, do NOT add `singularity exec -B ...` inside the shell block. The directive handles container binding.
- Load SLURM profiles from `profiles/workflow_profiles/snakemakes/slurmConfig/config.yaml` or `slurmMinimal/config.yaml`.
- Load executor settings from `profiles/workflow_profiles/executor_config.yaml`.
- Sample sheet format: TSV with columns `patient, sample, condition, path, genome` (defined in `profiles/setup_preferences.yaml`).

**Nextflow**: Profiles are in `profiles/workflow_profiles/nextflow/`.

### CLI Tools and Packages
- Use `argparse` (Python) or `optparse` (R) with clear help text for every argument.
- Include a `--version` flag. Use semantic versioning.
- Write unit tests with `pytest` (Python) or `testthat` (R). Minimum: test each public function with at least one normal case and one edge case.
- Package structure: `pyproject.toml` for Python, `DESCRIPTION` for R packages.

### Testing and CI
- Run tests before declaring any task complete.
- For pipelines: dry-run (`snakemake -n`) counts as a minimum test. A small-data end-to-end test is preferred.
- For Python packages: `pytest --tb=short` with coverage report.

### Snakemake Troubleshooting (Lessons Learned)
- **"No rule to produce" for valid targets**: Check for whitespace in sample names or paths in the sample sheet. As a workaround, extract the failing step into a standalone shell script.
- **Double-container invocation**: If a rule sets the `singularity:` directive, do NOT also add `singularity exec -B` inside the `shell:` block. The directive handles container execution automatically.
- **Config access**: When using `--configfile`, values are accessed as `config["key"]`, not `config.key`.
- **Cluster profile conflicts**: When using `--workflow-profile` with SLURM, ensure resource keys (`mem_mb`, `threads`, `runtime`) do not conflict with the cluster profile's own defaults. Check `.snakemake/log/` for the actual submitted job command if jobs fail silently.

---

## 5. Domain Playbook: AI Engineering

### LLM Applications
- **Frameworks**: Claude API, OpenAI API, LangChain, LlamaIndex — ask user which unless context is clear.
- **Prompt versioning**: Store prompts as separate text/yaml files, never inline long prompts as string literals.
- **Evaluation**: Define at least one quantitative metric before building. Log all LLM calls with input/output/latency/cost.
- **Experiment tracking**: Use MLflow, Weights & Biases, or a structured JSON log. Never rely on terminal output alone.

### ML for Genomics / Classical ML
- **Train/val/test split**: Always hold out a test set that is never touched until final evaluation. For genomic data, split by chromosome or patient to avoid data leakage.
- **Hyperparameter search**: Use Optuna or sklearn GridSearchCV. Log all trials.
- **Deployment**: Containerize models. Provide a predict script with clear input/output schema.
- **Reproducibility**: Pin all library versions. Export conda environment or requirements.txt at experiment completion.

---

## 6. Environment Reference

### Compute Awareness (SLURM)

| Task | CPUs | Memory | GPU | Time Estimate |
|------|------|--------|-----|---------------|
| Dorado basecalling | 4 | 16G | 1x A100/V100 required | ~1h per 10Gb pod5 |
| Minimap2 alignment | 8-16 | 32G | No | ~30min per 10M reads |
| Clair3 variant calling | 8 | 32G | Optional (faster with) | ~2h per 30x WGS |
| STAR alignment | 8 | 40G | No | ~30min per sample |
| CellRanger | 16 | 64G | No | ~2-4h per sample |
| DESeq2 / DGE | 4 | 16G | No | Minutes |
| Scanpy/Seurat | 4-8 | 32-64G | No | 10-60min depending on cell count |
| LLM fine-tuning | 4 | 32G | 1-4x GPU | Hours to days |

When writing SLURM job headers or snakemake resource directives, use these as starting estimates. Scale memory with data size — 2x safety margin for unknown inputs.

### SLURM GPU Jobs
- GPU jobs (`--gres=gpu:N`) can conflict with explicit `--mem` requests on some partitions. If GPU jobs fail silently, try removing the `mem_mb` resource or use `--mem=0` (all available memory on the node).
- Use `software-deployment-method: apptainer` in Snakemake SLURM profiles.
- Bind mounts must cover ALL input/output directories when using containers on compute nodes — compute nodes may not have the same mounts as login nodes.

### Large Data Directories
- ONT data directories can be massive (hundreds of pod5s, multi-GB BAMs). Text search tools (ripgrep, grep) will timeout on these.
- **Strategy**: Use `find` for filename searches. Restrict `grep` with `--include='*.py' --include='*.sh'` etc. to text file types only. For comprehensive searches, write a standalone script.
- **Never** attempt recursive grep on directories containing BAM, pod5, fast5, or CRAM files without file-type filtering.

### Containers
All container paths are in `profiles/software_configs/softwares_containers_config.yaml`. Always load paths from this file rather than hardcoding image locations.

### Reference Genomes
All genome paths (fasta, gtf, chrom.sizes, CpG islands) are in `profiles/databases/databases_config.yaml`. Supported builds: mm10, mm39, hg38, T2T-CHM13, GRCh37. Each has both local disk and S3 paths.

---

## 7. Figures and Visualization

### Standard Requirements (All Figures)
- **Output 3 formats**: Save every figure as PNG, PDF, and SVG in their respective subdirectories (`figures/png/`, `figures/pdf/`, `figures/svg/`).
- **Font**: Arial (fall back to Helvetica if Arial unavailable). Minimum size 20pt. Headers bold.
- **Axes**: Must be legible at final print size. Minimum tick label size 16pt.
- **Multi-panel figures**: Fix the y-axis range across panels to enable direct visual comparison.
- **Statistical tests**: Always prompt the user about including statistical annotations (e.g., t-test with p-values for group comparisons).
- **Figure size**: Default to the largest reasonable size for the context.

### Matplotlib Defaults
Load from `profiles/programming_language_profiles/python/matplotlib/matplotlib_defaults`.

### R / ggplot2
Load theme and font settings from `profiles/programming_language_profiles/R/`.

### ggplot2 Font Size Scaling Reference
The `theme()` element sizes are multiplied from `base_size`:

| Element | Multiplier | For 20pt final text |
|---------|-----------|---------------------|
| `axis.text` | base_size × 0.8 | base_size = 25 |
| `axis.title` | base_size × 1.0 | base_size = 20 |
| `plot.title` | base_size × 1.2 | base_size = 17 |
| `legend.text` | base_size × 0.8 | base_size = 25 |

- **Key insight**: For 20pt axis labels at Nature final size, use `base_size = 25` (since 25 × 0.8 = 20pt).
- **Default colorblind-safe palette**: Okabe-Ito — `#0072B2` (blue), `#E69F00` (orange), `#D55E00` (vermillion), `#999999` (grey).

### Nature Magazine Specifications (Final Manuscript Figures Only)
- Single column: 90 mm wide. Double column: 180 mm wide. Full page depth: 170 mm.
- Font: Arial or Helvetica, 20pt at final size.
- Apply these only when the user explicitly requests publication-quality or Nature-format figures.

---

## 8. Statistics Defaults

| Parameter | Default |
|-----------|---------|
| Significance threshold (p-value) | 0.05 |
| Adjusted p-value threshold | 0.05 |
| Multiple testing correction | Bonferroni |
| Effect size reporting | Always report alongside p-values |

Override any default when the user specifies different thresholds.

---

## 9. Error Recovery

### Pipeline Failures
1. **Read the error message completely** before suggesting fixes. Do not guess.
2. **Check logs first**: Snakemake logs are in `.snakemake/log/`, Nextflow logs in `.nextflow.log` and `work/` subdirectories.
3. **Common failure modes**:
   - Out of memory: Increase `mem_mb` in resources, resubmit only the failed job.
   - Missing input: Trace the DAG backward to find which upstream rule failed or which file path is wrong.
   - Container errors: Verify bind paths cover all input/output directories.
   - SLURM timeout: Check actual runtime of the failed job with `sacct`, increase time limit with margin.
4. **Never re-run an entire pipeline** to fix a single failed step. Use `--rerun-incomplete` (Snakemake) or `-resume` (Nextflow).

### Analysis Errors
- If a statistical test fails (convergence, singular matrix): Report the error, suggest an alternative test, and ask the user before proceeding.
- If QC fails a checkpoint: Stop, report metrics, and ask the user for guidance. Do not silently continue.

---

## 10. Quality Gates (Pre-Completion Checklist)

Before declaring any task complete, verify:

- [ ] All output files exist and are non-empty
- [ ] No hardcoded absolute paths in delivered scripts
- [ ] Random seeds are set where applicable
- [ ] Raw data is untouched
- [ ] Figures are saved in all 3 formats (png, pdf, svg)
- [ ] Project file at `~/projects/` is updated with what was done
- [ ] For pipelines: dry-run succeeds (`snakemake -n`)
- [ ] For analysis: QC checkpoints passed and were reported to user
- [ ] Variable names do not use forbidden names
- [ ] Contig names/sizes are parsed from reference files, not hardcoded
- [ ] Script produces a timestamped log file in `logs/` with data dimensions, filter counts, and output confirmations
- [ ] Log captures both stdout and stderr (R: `sink` + `globalCallingHandlers`; Python: `logging` with dual handlers)
