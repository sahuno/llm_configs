# CLAUDE.md — Samuel Ahuno (ekwame001@gmail.com)
# Computational Biologist, Greenbaum Lab (greenbab), MSKCC
# Languages: Python, R, Bash | HPC: SLURM | Organisms: Mouse & Human
# v0.3.0 — hook-enforced rules condensed, init_project.py integrated

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

- paths to genome references hg38:@/data1/greenbab/database/hg38/v0/Homo_sapiens_assembly38.fasta; mm10@/data1/greenbab/database/mm10/mm10.fa; For all other refenerce files check @/data1/greenbab/users/ahunos/apps/llm_configs/claude/profiles/databases/databases_config.yaml
- preserve file headers, don't make up headers at runtime
- Route long processes/jobs to compute node (default: componc_cpu) via slurm-mcp.  Use nexflow for pipelines on compute nodes
   ```
   <project_root>/
   ├── config.yaml                 # project parameters, genome paths
   ├── sample_sheet.tsv            # patient/sample/condition/assay/path/genome
   ├── data/
   │   ├── inbox/                  # staging area — review before promoting to raw/
   │   ├── raw/                    # IMMUTABLE — never write here after initial deposit
   │   └── processed/{genome}/     # all transformed outputs, tagged by genome build
   ├── src/                        # analysis scripts (numbered: 01_, 02_, ...)
   ├── results/
   │   └── {date}_{genome}_{description}/  # one dir per run
   │       └── figures/{png,pdf,svg}/
   ├── workflows/wf_snakemake/     # configs, profiles/slurm, rules, scripts
   ├── softwares/containers/       # .def files and container images
   ├── logs/                       # timestamped script logs
   └── docs/
   ```
   Use `~/.claude/scripts/init_project.py` to scaffold projects:
   ```bash
   # Scaffold in current directory (default — uses cwd name as project name):
   python ~/.claude/scripts/init_project.py --type analysis --genome hg38

   # Create a new subdirectory:
   python ~/.claude/scripts/init_project.py --name my_project --type pipeline --engine snakemake --genome mm10
   ```
   Project types: `analysis` (default workflow dirs), `pipeline` (engine-specific layout, requires `--engine snakemake|nextflow`), `ml` (adds notebooks, model dirs).
   A top-level `README.md` is generated with project metadata, directory tree, and aims. Additional READMEs only when the user requests them.
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
- **Never modify raw data.** _(Enforced by `block-raw-data-writes.sh` hook.)_
- **Never overwrite input files.** Read from source, write to a new path.
- **Set random seeds** for every stochastic operation (default seed: 42 unless user specifies otherwise).
- **Use relative paths** in all scripts and configs. _(Enforced by `warn-absolute-paths.sh` hook.)_

### Naming and Variables
- **Forbidden variable names** (clash with builtins): `conditions`, `counts`, `results`, `sum`, `median`, `mean`.
- **Script naming**: Use numbered prefixes for sequential steps: `01_download.py`, `02_align.sh`, `03_call_variants.py`.
- **File naming**: lowercase, underscores, no spaces. Include organism/genome build when relevant.

### Genomics-Specific
- **Never hardcode contig names or sizes.** Parse from genome sizes file or reference FASTA index. _(Enforced by `block-hardcoded-contigs.sh` hook.)_
- **Reference data**: Load paths from `profiles/databases/databases_config.yaml`. Supported genomes: mm10, mm39, hg38, T2T-CHM13, GRCh37.

### Multi-Genome-Build Projects
- Some integrative analyses require data from different genome builds (e.g., RNA in mm39, methylation in mm10).
- Always use **liftOver** for coordinate conversion. Store both original and lifted coordinates.
- Name intermediate files with BOTH builds when applicable: `{sample}.mm39_to_mm10.lifted.bed`
- Keep a **coordinate mapping manifest** to track which genome build each file uses.
- When merging data across builds, always verify that the liftOver was successful (check for unmapped regions) before proceeding.

### Genome Build Tagging _(Enforced by `enforce-genome-tag.sh` hook)_
- **Directory**: `data/processed/{genome_build}/`
- **Filename pattern**: `{sample}.{genome_build}.{description}.{ext}`
- **Example**: `data/processed/hg38/patient01.hg38.sorted.bam`
- **Valid tags**: `mm10`, `mm39`, `GRCm39`, `hg38`, `GRCh38`, `hg19`, `GRCh37`, `t2t`, `chm13`.
- **Exempt from tagging**: raw data (`.fastq`, `.fq`, `.pod5`), figures, scripts, configs, logs.

### Genomic Output Conventions

- **BED-like output files must have a `#`-prefixed header line.**
  - First line of every `.bed`, `.bedgraph`, `.bedMethyl`, or equivalent tabular output must start with `#` followed by tab-separated column names.
  - Example: `#chr\tstart\tend\tname\tscore\tstrand`
  - Reason: Python (`pd.read_csv(comment='#')`), R (`read.table(comment.char='#')`), and bedtools all skip `#` lines automatically, so tools never need special handling.
  - Exempt: files in strict BED format consumed directly by UCSC Genome Browser or IGV where a `track` header is expected instead.

- **Genomic locus IDs follow the format `{chr}:{start}-{end}.{name}.{score|index}.{strand}`.**
  - `{chr}:{start}-{end}` — UCSC-style coordinates (0-based start, half-open); unambiguous and greppable.
  - `{name}` — biological label (e.g. repeat subfamily, gene name, feature type).
  - `{score|index}` — use the relevant numeric score when one exists (e.g. SW score, MAPQ); use a per-name running integer index when no score applies. If both are needed, join with `|` (e.g. `36206|2`).
  - `{strand}` — `+` or `-`.
  - Separators: `.` between all fields; `:` only between chr and coordinates; `-` between start and end; `|` only inside the score|index field.
  - Examples:
    ```
    chr1:3014747-3021072.L1MdF_I.36206|1.-    # repeat locus — SW score + per-subfamily index
    chr1:3014747-3021072.L1MdF_I.1.-           # same locus — index only (score in separate column)
    chr7:117548628-117548729.CpG_island.42.+   # CpG island — feature index
    chrX:42920694-42927131.L1Base2.UID-5.+     # L1Base-only entry — UID as name, no index needed
    ```
  - This format is self-describing: the locus can be identified, sorted, and cross-referenced from the ID alone without consulting additional columns.

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
   - For figures: `"Saved: results/20260302_v1/figures/pdf/volcano_CKi_vs_DMSO.pdf (+ png, svg)"`

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

## 2A. Tool gotchas

Tool-specific lessons live in `/data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/`. Refer to these whenever the matching tool is involved — they capture non-obvious failure modes, fixes, and verification steps that are easy to miss otherwise.

- @/data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/snakemake.md — Snakemake 9 + SLURM executor pitfalls (mem_mb_per_cpu, srun memory conflict, cluster profile conflicts, stale locks)
- @/data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/dss.md — DSS Bioconductor silent corruption from `mclapply + detectCores()` ignoring SLURM cgroup limits; mandatory `ncores` arg, post-run verification
- @/data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/igv.md — IGV / igver hang on large ONT BAMs with `--methylation` preset; bigwig-mode autoscale fix via `setDataRange 0,100`; `modkit bedmethyl tobigwig` chrom.sizes mismatch (Rust SendError panic)

When you create a new rules file, add an entry here so it's loaded into every session.

---

## 3. Domain Playbook: Bioinformatics Analysis

### 3A. ONT Methylation Pipeline (pod5 to DMRs)

**Standard chain**: pod5 -> dorado basecall -> dorado align (or minimap2) -> samtools sort/index -> modkit pileup -> modkit dmr

**Tool references**: Load containers from `~/.claude/profiles/software_configs/softwares_containers_config.yaml`.

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
- Sample sheet format: TSV with columns `patient, sample, condition, assay, path, genome` (defined in `profiles/setup_preferences.yaml`).

**Snakemake run organization**:
- Pipeline code (Snakefile, rules, profiles) is versioned and reusable. Never write outputs into the pipeline directory.
- **One run = one directory.** All outputs from a run — rule outputs, figures, and logs — live under one named `results/<run>/` directory. This makes runs independently archivable (`tar -czf`) and deletable (`rm -rf`) with zero ambiguity about which run produced which file.
- `output_dir` is the only path key in config. Derive `FIGDIR` and `LOGDIR` from it in the Snakefile: `FIGDIR = f"{OUTDIR}/figures"`. Never add separate `figures_dir` or `log_dir` config keys — separate keys allow paths to diverge and recreate the ambiguity problem.
- One config file per run, named to match the results directory.
- Run naming convention: `{date}_{genome}_{description}` (e.g. `20260305_hg38_differential_methylation`, `20260310_mm10_v1`).

**Nextflow**: Profiles are in `~/.claude/profiles/workflow_profiles/nextflow/`.

### CLI Tools and Packages
- Use `argparse` (Python) or `optparse` (R) with clear help text for every argument.
- Include a `--version` flag. Use semantic versioning.
- Write unit tests with `pytest` (Python) or `testthat` (R). Minimum: test each public function with at least one normal case and one edge case.
- Package structure: `pyproject.toml` for Python, `DESCRIPTION` for R packages.

### Testing and CI
- Run tests before declaring any task complete.
- For pipelines: dry-run (`snakemake -n`) counts as a minimum test. A small-data end-to-end test is preferred.
- For Python packages: `pytest --tb=short` with coverage report.

### Snakemake Troubleshooting
See §2A Tool gotchas → `rules/snakemake.md`.

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
###TODO: create a database of memory requirements for common workflows or create slurm templates, implement tags like `highCompute_highTime`, `lowTime_lowCompute`. slurm-mcp has snapshot of resource limitations like componc_onc <= 7days

When writing SLURM job headers or snakemake resource directives, use these as starting estimates. Scale memory with data size — 2x safety margin for unknown inputs.

### SLURM GPU Jobs
- GPU jobs (`--gres=gpu:N`) can conflict with explicit `--mem` requests on some partitions. If GPU jobs fail silently, try removing the `mem_mb` resource or use `--mem=0` (all available memory on the node).
- Use `software-deployment-method: apptainer` in Snakemake SLURM profiles **only when all rules use `container:` or `singularity:` directives**. Omit it entirely for conda-based pipelines — it wraps every rule in `apptainer exec` and breaks any rule without an explicit container directive.
- Bind mounts must cover ALL input/output directories when using containers on compute nodes — compute nodes may not have the same mounts as login nodes.

### Large Data Directories
- ONT data directories can be massive (hundreds of pod5s, multi-GB BAMs). Text search tools (ripgrep, grep) will timeout on these.
- **Strategy**: Use `find` for filename searches. Restrict `grep` with `--include='*.py' --include='*.sh'` etc. to text file types only. For comprehensive searches, write a standalone script.
- **Never** attempt recursive grep on directories containing BAM, pod5, fast5, or CRAM files without file-type filtering.

### Containers
All container paths are in `profiles/software_configs/softwares_containers_config.yaml`. Always load paths from this file rather than hardcoding image locations.

#### Container Build Rules (Apptainer / Singularity `%post`)

- **Never `rm -rf /tmp/*` or `rm -rf /var/tmp/*` in `%post`.**
  Under `--fakeroot` / root-mapped namespace, the container's `/tmp` is a bind mount of
  the **host's `/tmp`**. This deletes other users' sockets/files and aborts the build.
  Only remove files you explicitly created by name (`rm -f /tmp/myinstaller.sh`).
  Use tool-specific cache cleaners instead: `mamba clean --all --yes`, `apt-get clean`,
  `pip cache purge`.

- **`condaforge/miniforge3` base requires `--ignore-fakeroot-command` on MSKCC HPC (RHEL 8).**
  The miniforge3 image ships a `fakeroot` binary compiled against GLIBC ≥ 2.33. The RHEL 8
  login node has GLIBC 2.28 — the `faked` daemon crashes immediately at `%post` start.
  Always add `--ignore-fakeroot-command` when building from a miniforge3/conda base image:
  `apptainer build --fakeroot --ignore-fakeroot-command output.sif input.def`

- **Never `apt-get` in `--fakeroot` builds on MSKCC HPC.**
  apt drops to the `_apt` user internally via `setgroups()` — this syscall is blocked in
  root-mapped namespace. Use a conda-ready base image (`condaforge/miniforge3`) and install
  everything via `mamba` to avoid this entirely.

- **Always `unset APPTAINER_BIND SINGULARITY_BIND` before building.**
  These env vars are applied during `%post`. If a bind source path doesn't exist inside the
  base image yet, the build fails with a fatal mount error.

### Reference Genomes
All genome paths (fasta, gtf, chrom.sizes, CpG islands) are in `profiles/databases/databases_config.yaml`. Supported builds: mm10, mm39, hg38, T2T-CHM13, GRCh37. Each has both local disk and S3 paths.

---

## 7. Figures and Visualization

### Standard Requirements (All Figures)
- **Output 3 formats**: Save every figure as PNG, PDF, and SVG under `results/{date}_{genome}_{description}/figures/{png,pdf,svg}/`. _(Dirs auto-created by `ensure_results_figures.sh` hook.)_
- **Font**: Arial (fall back to Helvetica if Arial unavailable). Minimum size 20pt. Headers bold.
- **Axes**: Must be legible at final print size. Minimum tick label size 16pt.
- **Multi-panel figures**: Fix the y-axis range across panels to enable direct visual comparison.
- **Statistical tests**: Always prompt the user about including statistical annotations (e.g., t-test with p-values for group comparisons).
- **Figure size**: Default to the largest reasonable size for the context.

### Two Figure Locations
- **`results/{run}/figures/{png,pdf,svg}/`** — individual analysis figures generated per run. This is where scripts save figures during analysis.
- **`docs/manuscript/figures/`** — final multi-panel publication figures assembled from individual figures (created when preparing a manuscript, not during analysis). These are composited in Illustrator from the per-run figures above.

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
   - Out of memory: Increase `mem_mb_per_cpu` in resources (not `mem_mb` for Snakemake 9 + SLURM executor — see Snakemake SLURM pitfalls in §4). Resubmit only the failed job.
   - Missing input: Trace the DAG backward to find which upstream rule failed or which file path is wrong.
   - Container errors: Verify bind paths cover all input/output directories.
   - SLURM timeout: Check actual runtime of the failed job with `sacct`, increase time limit with margin.
4. **Never re-run an entire pipeline** to fix a single failed step. Use `--rerun-incomplete` (Snakemake) or `-resume` (Nextflow).

### Analysis Errors
- If a statistical test fails (convergence, singular matrix): Report the error, suggest an alternative test, and ask the user before proceeding.
- If QC fails a checkpoint: Stop, report metrics, and ask the user for guidance. Do not silently continue.

---

### Philosophy of research publication with figures (stream of thought)
- Generate 3 figure formats (.png, .pdf, .svg) per figure. rasterize the .pdf  with `RASTERISE_DPI` of 50dpi and  png_dpi=70 (local machine)
- keep a figure index per script. Helps track down where each figure came from per script (Host and local machine)
- download figures onto OneDrive research/institutional folder (local machine)
- place figures (.pdf) on illustrator artboard and save accordingly as Figure 1, 2, .... # or Supplementary Figure 1, 2,...,n (local machine)
- write script to autodownload figures with higher dpi when ready (local machine)
- adobe illustrator should can be resaved with high dpi figures and exported as .pdf (local machine)

---

## 10. Quality Gates (Pre-Completion Checklist)

### Enforced by hooks (automatic — no manual check needed)
- Raw data untouched (`block-raw-data-writes.sh`)
- No hardcoded absolute paths (`warn-absolute-paths.sh`)
- No hardcoded contig names/sizes (`block-hardcoded-contigs.sh`)
- Genome build tags on genomic files (`enforce-genome-tag.sh`)
- Snakemake dry-run on Snakefile edits (`snakemake-dryrun.sh`)
- YAML validation (`validate-yaml.sh`)
- Reference genome paths validated (`validate-reference-genome.sh`)

### Manual checks (still required)
- [ ] All output files exist and are non-empty
- [ ] Random seeds are set where applicable
- [ ] Figures saved in all 3 formats under `results/{run}/figures/{png,pdf,svg}/`
- [ ] Variable names do not use forbidden names
- [ ] Script produces a timestamped log file in `logs/` with data dimensions, filter counts, and output confirmations
- [ ] Log captures both stdout and stderr (R: `sink` + `globalCallingHandlers`; Python: `logging` with dual handlers)
- [ ] Project file at `~/projects/` is updated with what was done
- [ ] For analysis: QC checkpoints passed and were reported to user
