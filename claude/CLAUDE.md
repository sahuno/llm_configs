# CLAUDE.md — Samuel Ahuno (ekwame001@gmail.com)
# Computational Biologist, Greenbaum Lab (greenbab), MSKCC
# Languages: Python, R, Bash | HPC: SLURM | Organisms: Mouse & Human
# v0.4.0 — PROGRESS.md ledger; domain playbooks and long specs moved to the analysis-playbooks skill

---

## 0. Site and user profiles

Reference genomes, container images, SLURM profiles, and personal plot defaults
are **not** hardcoded in this file. They live in the `hpc-site` plugin under
`profiles/`, split across two independent axes:

- **`$SITE_CONFIG`** — the active *site* profile. Cluster facts: genomes,
  containers, partitions, bind mounts. Changes when the cluster changes.
- **`$USER_CONFIG`** — the active *user* profile. Person facts: plot defaults,
  sample-sheet conventions, `DO_NOT` rules. Travels with me between clusters.

Set once per machine:

```bash
source ~/projects/llm_configs/plugins/hpc-site/profiles/resolve.sh
export SITE_PROFILE=mskcc-greenbaum   # selects by name
export USER_PROFILE=sahuno            # defaults to $USER
profiles_export                       # resolves $SITE_CONFIG and $USER_CONFIG
```

Both auto-select when exactly one real profile exists. When either is unset and
ambiguous, resolution **fails and lists the candidates** — it never guesses a
path. If a key or file is missing from a profile, add it there; never fall back
to a literal path in a script.

| Read this | From |
|---|---|
| Reference genomes | `$SITE_CONFIG/databases.yaml` |
| Container images | `$SITE_CONFIG/containers.yaml` |
| Scheduler defaults | `$SITE_CONFIG/executor.yaml` |
| Roots, caches, bind mounts | `$SITE_CONFIG/paths.yaml` |
| Sample-sheet conventions | `$USER_CONFIG/setup_preferences.yaml` |
| Prohibited actions | `$USER_CONFIG/DO_NOT.md` |
| Plot defaults | `$USER_CONFIG/matplotlib_defaults`, `$USER_CONFIG/.Rprofile` |

---

## 1. Session Initialization

**Prefer the working directory over interrogation.** A scaffolded project carries
its own `CLAUDE.md` naming the domain, genome build, aims, status, and progress
log. Claude Code loads it automatically, so a session in a project directory
already knows what it is working on — do not ask the user to restate it.

1. **If the project root has a `CLAUDE.md`**, that is the classification. Read its
   ledger (`PROGRESS.md`, see "Project ledger" below) and resume from the "Exact
   next steps". Say what you resumed from. Ask only what the file leaves genuinely
   open — typically the aim for *this* session, not the domain.
2. **If it does not**, then ask:
   - **Domain**: Bioinformatics Analysis | Software Development | AI Engineering | Writing
   - **Aim**: a clear, numbered list of objectives

   For work that will outlive the session, offer `/init-bio-project` — it writes
   the project `CLAUDE.md` so this is the last time the question is needed.
3. **For analysis projects**, scaffold the standard layout with `/init-bio-project`: `config.yaml`,
   `sample_sheet.tsv`, `data/{inbox,raw,processed/{genome}}` (`inbox/` is staging, reviewed before promoting to
   `raw/`; `raw/` is **immutable** after the initial deposit), `src/` (numbered scripts), `results/{date}_{genome}_{description}/figures/{png,pdf,svg}/`
   (one dir per run), `workflows/`, `softwares/containers/`, `logs/`, `docs/`.
   Use the `/init-bio-project` command (bio-skills plugin) to scaffold projects:
   ```bash
   # Scaffold in current directory (default — uses cwd name as project name):
   /init-bio-project --type analysis --genome hg38

   # Create a new subdirectory:
   /init-bio-project --name my_project --type pipeline --engine snakemake --genome mm10
   ```
   Project types: `analysis` (default workflow dirs), `pipeline` (engine-specific layout, requires `--engine snakemake|nextflow`), `ml` (adds notebooks, model dirs).
   A top-level `README.md` is generated with project metadata, directory tree, and aims. Additional READMEs only when the user requests them.
4. **Record progress in the project ledger** (`PROGRESS.md`, see "Project ledger" at the end) as work proceeds — decisions, parameters, and paths, so a future session can resume without re-discovery.

### Ledger entry content (minimum for resumption)
Every ledger entry must include:
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
- **Preserve file headers.** Carry through the header that came with the data; never invent one at runtime.
- **Set random seeds** for every stochastic operation (default seed: 42 unless user specifies otherwise).
- **Use relative paths** in all scripts and configs. _(Enforced by `warn-absolute-paths.sh` hook.)_

### Naming and Variables
- **Forbidden variable names** (clash with builtins): `conditions`, `counts`, `results`, `sum`, `median`, `mean`.
- **Script naming**: Use numbered prefixes for sequential steps: `01_download.py`, `02_align.sh`, `03_call_variants.py`.
- **File naming**: lowercase, underscores, no spaces. Include organism/genome build when relevant.

### Genomics-Specific
- **Never hardcode contig names or sizes.** Parse from genome sizes file or reference FASTA index. _(Enforced by `block-hardcoded-contigs.sh` hook.)_
- **Reference data**: Load paths from `$SITE_CONFIG/databases.yaml`. Supported genomes: mm10, mm39, hg38, T2T-CHM13, GRCh37. Never hardcode a fasta/gtf path in a script or config.

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

Every analysis script writes a **timestamped log** to `logs/{script_name}_{YYYYMMDD_HHMMSS}.log`
(accept `--log_dir`, default `logs`) that captures console output too: R `sink(split = TRUE)` +
`globalCallingHandlers`; Python `logging` with a FileHandler and a StreamHandler, never bare `print()`;
Bash `exec > >(tee -a "$LOG_FILE") 2>&1`. The log records: a session header (versions, arguments),
dimensions after every load, **before/after counts for every filter** and every merge, sanity checks,
`=== Section ===` milestones, every output written, warnings and errors, a footer with runtime and
`sessionInfo()` / `pip freeze`, and last, `=== DONE: {script_name} completed successfully ===`. If
that line is missing, the run did not finish. Full specification with examples: `analysis-playbooks`
skill → `references/logging_audit.md`.

Close a session with `/wrapup`, which appends the five required fields below to
the project's `PROGRESS.md` ledger and updates its header.

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

Tool-specific failure modes are no longer `@`-imported here. They now live in
skills shipped by this repo's plugins, and load **on demand** when the matching
tool is in play:

| Skill | Plugin | Covers |
|---|---|---|
| `analysis-gotchas` | bio-skills | DSS, parallel R / mclapply OOM, small-n CV, `fread` on BED, Clair3/ClairS, Severus, deeptools, liftOver chains, reporting aggregated statistics, declaring work done |
| `snakemake` → `references/gotchas.md` | bio-skills | Snakemake 9 + SLURM executor pitfalls |
| `igv-screenshots` → `references/gotchas.md` | bio-skills | IGV / igver on large ONT BAMs, bigwig autoscale, chrom.sizes mismatch |
| `singularity-build` → `references/env_leak.md` | bio-skills | Host SSL/CA env vars leaking into apptainer SIFs |
| `mskcc-hpc` | hpc-site | Partition access, slurm-mcp quirks, GNU time, SIF-vs-conda, vLLM on iris |

**Why the change.** The old block `@`-imported 15 absolute `/data1/...` paths.
Those resolve only on the HPC — on any other machine every import silently
failed — and where they did resolve they pulled ~15k tokens into *every*
session regardless of topic. As skills they load only when relevant, and the
paths travel with the plugin.

To add a new gotcha: drop a file in the owning skill's `references/` and add a
row to that skill's SKILL.md table. No edit here is needed.

---

## 3. Domain Playbook: Bioinformatics Analysis

Standard chains, QC checkpoints and "done" criteria live in the `analysis-playbooks` skill
(bio-skills), one reference per domain: ONT methylation (pod5 → dorado → modkit → DMRs), variant
calling (Clair3, Sniffles2, GATK), bulk RNA-seq DGE, scRNA-seq. IGV screenshots: the
`igv-screenshots` skill. A failed QC checkpoint is a stop: report the metric and ask.

- **Dorado models must match the chemistry/flowcell** (4 kHz vs 5 kHz runs are processed
  separately). Always confirm with the user; a mismatch produces silent garbage.
- **Multi-run samples**: basecall each run independently, merge after alignment — never
  concatenate raw pod5 files across runs.

---

## 4. Domain Playbook: Software Development

### Pre-flight check before scaffolding ANY pipeline (Snakemake or Nextflow)

Before writing `workflow.smk`, `Snakefile`, `main.nf`, or any pipeline scaffold for a standard bioinformatics step, ALWAYS first check whether an established, validated implementation exists:

1. **nf-core/modules** — search the registry: `https://github.com/nf-core/modules/tree/master/modules/nf-core`. Common matches: `samtools/*`, `modkit/pileup`, `modkit/bedmethyltobigwig`, `dorado/basecaller`, `severus`, `mosdepth`, `clair3`, `sniffles`, `gatk4/*`, `bwa/*`, `star/*`, `hisat2/*`, `salmon/*`, `featurecounts`, `deseq2`, `multiqc`. nf-core modules ship with `nf-test`, validated container references, and battle-tested invocation flags.
2. **nf-core pipelines** — does an end-to-end pipeline cover this workflow? `rnaseq`, `sarek`, `atacseq`, `methylong`, `taxprofiler`, `viralintegration`, `oncoanalyser`, `nanoseq`, `differentialabundance`, `mag`, `smrnaseq`. End-to-end pipelines bundle their own modules + tested-together default configs.
3. **Lab-internal pipelines** — `ls ~/code/ pipelines/ workflows/` for an existing implementation in this lab.
4. **Other community sources** — `snakemake-wrappers`, Galaxy ToolShed, published workflow repositories.

Run **`/preflight`** to do this search. **REPORT what you found before scaffolding new code.** Build from scratch ONLY when:
- No suitable existing solution exists, OR
- The user explicitly says "build from scratch", OR
- The existing solution has a deal-breaking gap (document the gap)

If you choose to build new, the report must name what existed and why you rejected it. Pause for confirmation before writing the workflow.

The cost of skipping this check is concrete: when I (Claude) scaffolded `pipelines/modkit_pileup/workflow.smk` from scratch on 2026-05-01, I missed that `--cpg` requires `--modified-bases` in modkit 0.6.1 — an nf-core `modkit/pileup` module would have shipped with the right invocation pre-validated. Wasted one batch dispatch.

### Pipeline Development (Snakemake / Nextflow)

Rules, site profiles (`$SITE_CONFIG/snakemake/`, `$SITE_CONFIG/nextflow.config`) and run
organization: `analysis-playbooks` skill → `references/pipeline_development.md`; SLURM-executor
pitfalls: the `snakemake` skill. The two conventions that apply everywhere: **one run = one
directory** (`results/<run>/` holds rule outputs, figures and logs; `output_dir` is the only path key,
`FIGDIR`/`LOGDIR` derive from it), and never write outputs into the pipeline directory.

### CLI Tools and Packages
- Use `argparse` (Python) or `optparse` (R) with clear help text for every argument.
- Include a `--version` flag. Use semantic versioning.
- Write unit tests with `pytest` (Python) or `testthat` (R). Minimum: test each public function with at least one normal case and one edge case.
- Package structure: `pyproject.toml` for Python, `DESCRIPTION` for R packages.
- **Python environments: use `uv`.** `uv venv` + `uv pip install`, or `uv sync`
  against `pyproject.toml`. It resolves in seconds where pip takes minutes, and
  the lockfile is what makes a rerun reproducible. Reserve conda/mamba for
  packages with non-Python system dependencies that only bioconda ships
  (samtools, bcftools, htslib-linked tools) — that is a real constraint, not a
  preference.

### Testing and CI
- Run tests before declaring any task complete.
- For pipelines: dry-run (`snakemake -n`) counts as a minimum test. A small-data end-to-end test is preferred.
- For Python packages: `pytest --tb=short` with coverage report.

### Snakemake Troubleshooting
See §2A Tool gotchas → `snakemake` skill → `references/gotchas.md`.

---

## 5. Domain Playbook: AI Engineering

LLM applications (framework choice, prompt versioning, evaluation, call logging) and ML on genomic
data (split by chromosome or patient, never touch the test set until the end): `analysis-playbooks`
skill → `references/ai_engineering.md`.

---

## 6. Environment Reference

### Compute Awareness (SLURM)
- Route long-running jobs to a compute node via slurm-mcp (default partition: `componc_cpu`; prefer `cpushort` for work under 2 h — see the `mskcc-hpc` skill). Use Nextflow or Snakemake for pipelines rather than raw sbatch chains.

When writing SLURM job headers or snakemake resource directives, scale memory with data size and allow a 2× safety margin for unknown inputs. (No per-workflow estimate table exists yet; it is an open item in the llm_configs ledger. Query `slurm-mcp` for live partition limits rather than guessing.)

### SLURM GPU Jobs
- GPU jobs (`--gres=gpu:N`) can conflict with explicit `--mem` requests on some partitions. If GPU jobs fail silently, try removing the `mem_mb` resource or use `--mem=0` (all available memory on the node).
- Use `software-deployment-method: apptainer` in Snakemake SLURM profiles **only when all rules use `container:` or `singularity:` directives**. Omit it entirely for conda-based pipelines — it wraps every rule in `apptainer exec` and breaks any rule without an explicit container directive.
- Bind mounts must cover ALL input/output directories when using containers on compute nodes — compute nodes may not have the same mounts as login nodes.

### Large Data Directories
- ONT data directories can be massive (hundreds of pod5s, multi-GB BAMs). Text search tools (ripgrep, grep) will timeout on these.
- **Strategy**: Use `find` for filename searches. Restrict `grep` with `--include='*.py' --include='*.sh'` etc. to text file types only. For comprehensive searches, write a standalone script.
- **Never** attempt recursive grep on directories containing BAM, pod5, fast5, or CRAM files without file-type filtering.

### Containers
All container paths are in `$SITE_CONFIG/containers.yaml`. Always load paths from this file rather than hardcoding image locations.

#### Container Build Rules (Apptainer / Singularity `%post`)

The full rules and their reasons are in the `singularity-build` skill. The prohibitions:
- **Never `rm -rf /tmp/*` or `rm -rf /var/tmp/*` in `%post`** — under `--fakeroot` the container's
  `/tmp` is the host's `/tmp`; it deletes other users' files. Remove only files you created, by name.
- **Never `apt-get` in `--fakeroot` builds on MSKCC HPC** — use a `condaforge/miniforge3` base and
  `mamba`; that base needs `apptainer build --fakeroot --ignore-fakeroot-command` on RHEL 8.
- **Always `unset APPTAINER_BIND SINGULARITY_BIND` before building.**

### Reference Genomes
All genome paths (fasta, gtf, chrom.sizes, CpG islands) are in `$SITE_CONFIG/databases.yaml`. Supported builds: mm10, mm39, hg38, T2T-CHM13, GRCh37. Each has both local disk and S3 paths.

---

## 7. Figures and Visualization

### Standard Requirements (All Figures)
- **Output 3 formats**: Save every figure as PNG, PDF, and SVG under `results/{date}_{genome}_{description}/figures/{png,pdf,svg}/`. Create these directories in the script; there is no hook that makes them.
- **Font**: Arial (fall back to Helvetica if Arial unavailable). Headers bold.
  - **Draft / analysis figures** (viewed on screen at full size): minimum 20pt.
  - **Final manuscript figures** (reduced to journal column width): 5–8pt — see the Nature section below. 20pt at a 90 mm column is roughly 3.5× too large.
- **Axes**: Must be legible at final print size. Minimum tick label 16pt on draft figures; scale down with the body text for final figures.
- **Multi-panel figures**: Fix the y-axis range across panels to enable direct visual comparison.
- **Statistical tests**: Always prompt the user about including statistical annotations (e.g., t-test with p-values for group comparisons).
- **Figure size**: Default to the largest reasonable size for the context.

Record every figure with `/figure-manifest` as it is written — script, commit,
inputs. `/figure-manifest --check <run>` before assembling a manuscript.

### Two Figure Locations
- **`results/{run}/figures/{png,pdf,svg}/`** — individual analysis figures, written by scripts during analysis.
- **`docs/manuscript/figures/`** — final multi-panel figures only, assembled through `print-plate-assembly`
  (the authority for final figures). Workflow, Nature sizes, the lab's 8 pt ladder and ggplot2 `base_size`
  scaling: `analysis-playbooks` skill → `references/figures.md`.

### Matplotlib Defaults
Load from `$USER_CONFIG/matplotlib_defaults`.

### R / ggplot2
Load theme and font settings from `$USER_CONFIG/.Rprofile`.

- **Default colorblind-safe palette**: Okabe-Ito — `#0072B2` (blue), `#E69F00` (orange), `#D55E00` (vermillion), `#999999` (grey).

---

## 8. Statistics Defaults

| Parameter | Default |
|-----------|---------|
| Significance threshold (p-value) | 0.05 |
| Adjusted p-value threshold | 0.05 |
| Multiple testing correction | Benjamini–Hochberg (FDR) |
| Effect size reporting | Always report alongside p-values |

**Choosing a correction.** Default to Benjamini–Hochberg for discovery work — DMR/DEG calling, genome-wide scans, any analysis with thousands of tests. This matches what the RNA-seq playbook already does in practice (DESeq2's `padj` is BH). Bonferroni is correct only for a small, pre-specified confirmatory set; applied genome-wide it returns ~0 hits at realistic n and silently converts a discovery analysis into a null result.

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

Run **`/gates`** to work through these with evidence. Run **`/verify-run`**
before trusting any long parallel job — a completion marker is not success.

- [ ] All output files exist and are non-empty
- [ ] Random seeds are set where applicable
- [ ] Figures saved in all 3 formats under `results/{run}/figures/{png,pdf,svg}/`
- [ ] Variable names do not use forbidden names
- [ ] Script produces a timestamped log file in `logs/` with data dimensions, filter counts, and output confirmations
- [ ] Log captures both stdout and stderr (R: `sink` + `globalCallingHandlers`; Python: `logging` with dual handlers)
- [ ] The project's `PROGRESS.md` ledger has an entry for this session (`/wrapup`)
- [ ] For analysis: QC checkpoints passed and were reported to user

---

## Project ledger (PROGRESS.md)

Every project has a `PROGRESS.md` at its root; the ledger hook prints its head
at session start. Two obligations, no exceptions:

1. **Read it first.** Resume from "Exact next steps". Do not ask the user to
   restate what the ledger already says. If the session-start digest says it
   was truncated, read the rest of the file before acting on it.
2. **Write it last.** If you changed any file, add an entry before you finish
   (`/wrapup`, or `ledger-append` directly): dated, with the five fields — what
   was done, key file paths, commands that worked, known issues or blockers,
   exact next steps. Update `updated` and `next_action` in the header. A
   question only the user can answer goes in `## Open unknowns` with a
   decide-by date, not in chat alone.

If the project has no `PROGRESS.md` and you changed files, create one with
`ledger-append --create --project <name>`, which copies the template. If the
header says `shared_copy: /data1/greenbab/ledger/...`, push the file there
afterwards with `iris push PROGRESS.md <that path>`.
