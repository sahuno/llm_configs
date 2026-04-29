---
name: runtime-resource-study
description: |
  Run a stage-gated runtime/resource optimization study for any bioinformatics tool
  or command-line program on a SLURM HPC cluster. Walks through preflight, OFAT factor
  scan, 2^k confirmation factorial, build-mode + alternative-implementation comparison,
  input-size scan, out-of-sample validation, and produces a fitted predictive resource
  model (wall_s and peak_rss as functions of input size), a machine-readable model.yaml
  with caveats, a full REPORT.md, and a one-page exec summary PDF. Trigger PROACTIVELY
  whenever the user asks to "benchmark", "optimize", "tune", "characterize runtime/memory",
  "find best config", "build a resource model", "how does X scale", or "what should I
  put in my Snakemake resources directive for tool Y" — for any compute-bound bioinformatics
  step (sort, dedup, alignment, variant calling, methylation calling, basecalling, indexing,
  pileup, liftover). Also triggers on /runtime-resource-study or /benchmark-tool. Skip
  only for one-off quick timing where a single number suffices and no model is needed.
---

# runtime-resource-study

Stage-gated benchmark methodology for compute-bound HPC tools. Produces a predictive
`wall(N, file_size)` + `rss(N)` model that drives Snakemake / Nextflow `resources`
directives, plus a publication-quality report.

## Outcome

| Artefact | Purpose |
|---|---|
| `model.yaml` | Machine-readable model — coefficients, R², validation residuals, caveats, helper formulas |
| `REPORT.md` | Full narrative — math callout, TL;DR, per-stage results, recommendations |
| `exec_summary.{pdf,png,svg}` | One-page US Letter summary for sharing |
| `benchmark.csv` per stage | One row per replicate (raw measurements) |
| `summary_table.csv` per stage | Per-condition median + min/max + CV |

All under `<project_root>/<tool>/<command>/` with reproducible drivers.

## When you're invoked

1. **Confirm scope with the user**: tool name, command, input class (BAM/VCF/FASTQ/POD5/etc.),
   expected scale, and which alternative implementation to baseline against (every study
   includes ≥1).
2. **Read the exemplar**: the samtools sort study at
   `/data1/greenbab/users/ahunos/projects/biotoolsBenchmarks/samtools/sort/` is a complete
   working instance. Skim its `REPORT.md` for deliverable shape and `src/` for script patterns.
3. **Read `references/stage_design.md`** to pick factor levels for the user's tool. Different
   tool classes (sort, align, variant-call) have different relevant factors.
4. **Walk through the 7 stages below**, getting user approval at each handoff (especially
   Stage 0 setup and the Stage 5 → 6 transition).

## The 7 stages

### Stage 0 — Setup

Decide and write down (output: `Stage0_setup.md` in project root):

- Tool, command, input class, expected scale
- **Is this a GPU tool?** (basecaller, GPU-accelerated aligner / variant caller, anything needing `--gres=gpu`). If yes, **read `references/gpu_tools.md`** before continuing — the factor menu, runner, and partition all change. Use `scripts/03_run_one_gpu.sh.template` instead of the CPU runner.
- Factors to vary (CPU tools: threads, memory, compression, tmp-dir, build mode. GPU tools: model size, GPU type, batch size, runners, mod-base flags — see `gpu_tools.md`.)
- Baseline level for each factor (the "default" all sweeps hold others at)
- ≥1 alternative implementation (e.g., samtools sort ↔ sambamba sort ↔ Picard SortSam; dorado ↔ guppy ↔ bonito)
- Calibration input (small enough for fast iteration, large enough to be CPU/GPU-bound)
- Cost rate — default `$0.05/core-hour` if local rate unknown. For GPU tools, also `$/gpu-hour` (default A100=$1.50, L40S=$0.80, H100=$3.00) and `$/kWh` for energy (default $0.12)

### Stage 1 — Preflight

Inspect the input: record count, file size, schema/version, technology, sort state, key
metadata. Without this, factor levels are guessed.

Use `scripts/01_inspect_input.sh.template` — adapt the metadata-extraction commands to
your input format (the template covers BAM, VCF, FASTQ stubs).

Output: `results/preflight/<input>.preflight.yaml`.

### Stage 2 — OFAT factor scan

Vary one factor at a time around the baseline. Identify which factors move the needle
and at what magnitude.

- 5–10 levels per factor
- 3 replicates per condition
- One SLURM job per (condition × replicate)

Driver: copy `scripts/submit_grid.py.template`, fill in `FACTORS` and `BASELINE` for
your tool. See `references/stage_design.md` for choosing levels.

Output: `results/<date>_stage2_ofat/`.

### Stage 3 — Confirmation factorial

2^k full factorial near the candidate optimum from Stage 2. Detect interactions and
tighten variance bounds at the recommended config.

- Pick the 4 factors with biggest Stage 2 effect → 16 conditions
- 3 replicates each → 48 jobs

Output: `results/<date>_stage3_factorial/`.

### Stage 4 — Build-mode + alternative-implementation comparison

Closes the "is this the right tool?" gap. Test:

- **Build modes**: container (apptainer SIF) vs conda vs native (if available)
- **Alternative implementations** (≥1): e.g., for sorting: sambamba, Picard SortSam.
  For variant calling: deepvariant vs gatk HaplotypeCaller. For alignment: minimap2 vs
  winnowmap.

5+ replicates per build mode (build comparisons need higher n — differences are often
small and noisy). Capture `/proc/cpuinfo` model name per replicate.

Per `rules/apptainer_vs_conda.md`: on this cluster, prefer SIF for short HTSlib-class
jobs (NFS cold-start tax on conda binaries).

Output: `results/<date>_stage4_buildmode/`.

### Stage 5 — Input-size scan

Subsample reproducibly (seed=42) at 10/25/50/75/100% of the calibration input. Fit
`wall_s = a + b·N_records` and `rss = c + d·N_records`. Target R² ≥ 0.95.

| Input format | Subsample command |
|---|---|
| BAM | `samtools view -s 42.<frac> -b -o out.bam in.bam` |
| VCF | `bcftools view in.vcf.gz \| awk 'BEGIN{srand(42)} /^#/{print; next} rand()<<frac>>{print}' \| bgzip > out.vcf.gz` |
| FASTQ | `seqkit sample -p <frac> -s 42 in.fq.gz -o out.fq.gz` |
| POD5 | `pod5 subset --threads 8 in.pod5 -o out.pod5 --include-fraction <frac>` |

Output: initial `model.yaml`.

### Stage 6 — Out-of-sample validation

Hold out 1–2 inputs ~10× larger than calibration max. Predict, run, compare. Report
error in % terms.

If the 1-term linear model has > ±20% error, **refit with file_size as a second
predictor**: `wall_s = a + b·N + c·file_size_bytes`. Discovered in the samtools sort
study — the page-cache-vs-IO-bound regime boundary makes 1-term linear fits fail at
extrapolation (~30× scale beyond calibration).

Update `model.yaml` with validation residuals and the 2-term fit if needed.

### Stage 7 — Variance partitioning + cost + report

Three things in this final stage:

1. **Variance partitioning** — for each stage's data, fit `lme4::lmer(wall ~ factor +
   (1|host))` and report % variance explained by host vs condition vs replicate.
   If host explains >25% of variance, you have hardware heterogeneity that needs
   `--exclude=<bad_nodes>` or tighter partition selection. Use
   `scripts/fit_model.py --variance-partition`.
2. **Cost accounting** — multiply `wall × threads × cost_per_core_hour` for each
   condition. Identify the cost-Pareto frontier — sometimes `-@ 16` is cheaper than
   `-@ 32` even though it's slower. Use `scripts/cost_accounting.py`.
3. **Report** — render `assets/REPORT_template.md` with your data; render
   `scripts/exec_summary.R.template` for the one-page summary.

## Methodology non-negotiables

These prevent silent confounders that invalidate every conclusion.

- **Compute-node only for streams.** Any operation that streams a multi-GB input
  (`samtools view -c`, `bcftools view`, `wc -l`, etc.) goes on a SLURM job. Even one-off
  inventory tasks. See project memory `login_node_discipline.md`.
- **One condition per SLURM job.** `--exclusive`, single-node. Fresh node → cold page
  cache → honest fs_in measurements. Never loop conditions inside an allocation. See
  `rules/mskcc_partitions.md`.
- **GNU time, dynamically resolved.** Don't hardcode `/usr/bin/time` — it doesn't exist
  on this cluster. Install via conda alongside the tool and resolve as a sibling of the
  tool's binary. See `rules/gnu_time.md`.
- **`--exclude=isca071`** on cpushort. After Stage 1, inventory CPU model per replicate;
  if any node clusters separately, add to the exclude list and rerun affected conditions.
- **GPU tools: pin GPU type via `--gres=gpu:<type>:N`**, never just `--gres=gpu:N`. GPU
  vintage perf differences are 3–10× (much larger than CPU heterogeneity). Capture
  `gpu_model`, `gpu_driver`, peak GPU memory, and mean GPU utilisation per replicate via
  the nvidia-smi sidecar in `03_run_one_gpu.sh.template`. See `references/gpu_tools.md`.
- **Manifest separate from benchmark CSV.** `manifest.tsv` is the record of intent (what
  conditions WERE planned). `benchmark.csv` is the record of actuals. They should match
  row-for-row at the end.
- **flock-guarded CSV appends.** Concurrent jobs each append a row; flock prevents
  corruption.
- **≥3 replicates per condition.** 5+ for build-mode and alternative-implementation
  comparisons. Report median + min/max + CV. Flag CV > 20% as needing investigation.
- **Out-of-sample validation before declaring "production-ready."** A model that fits
  its training data but isn't validated is just a curve through points.
- **slurm-mcp gotchas**: `submit_batch` injects `--mem 64G` on cmdline which conflicts
  with `#SBATCH --mem-per-cpu`; doesn't support `--array`. See `rules/slurm_mcp.md`.
  For batches > 20 jobs, prefer direct `sbatch` via Python.

## Templates

In `scripts/` — fill placeholders marked `{{NAME}}`:

| Template | Purpose | Edit |
|---|---|---|
| `01_inspect_input.sh.template` | Preflight | Metadata-extraction commands per input format |
| `03_run_one.sh.template` | Single-condition runner (CPU) with GNU time | The `${TOOL_BIN} ${ARGS}` line + CSV header |
| `03_run_one_gpu.sh.template` | Single-condition runner (GPU) — adds nvidia-smi sidecar, `--nv` for containers, GPU identity capture | The `# === Build command ===` block + tool-specific factors |
| `submit_grid.py.template` | Stage driver: manifest + sbatch + submit | `FACTORS` dict, `BASELINE` |
| `summarise_stage.R.template` | Per-stage figures + table | Factor labels, plot titles |
| `exec_summary.R.template` | One-page composite | Plug in your CSV paths |

Bundled (run as-is):

| Script | Purpose |
|---|---|
| `fit_model.py` | Linear regression, variance partitioning, cross-validation |
| `cost_accounting.py` | wall × threads × $/core-hour → CPU-hours, $/sample |

## Final deliverables checklist

For each stage (1–6):
- [ ] `manifest.tsv` (intent)
- [ ] `benchmark.csv` (actuals)
- [ ] `summary_table.csv` (medians + CV)
- [ ] `figures/{png,pdf,svg}/` (≥1 headline figure)

For the project as a whole:
- [ ] `model.yaml` (validated, with caveats)
- [ ] `REPORT.md`
- [ ] `exec_summary.pdf`
- [ ] Variance partitioning report (Stage 7)
- [ ] Cost-Pareto frontier (Stage 7)

## Reference files

- `references/stage_design.md` — picking factors, levels, replicate counts per tool class
- `references/analysis_recipes.md` — variance partitioning, model fit + validation, cost accounting
- `references/templates_guide.md` — how to fill each template
- `references/exemplar_walkthrough.md` — tour of the samtools sort study end-to-end
- `references/gpu_tools.md` — **read this first for any GPU tool** (basecaller, GPU aligner, GPU variant caller). Different factor menu, partitions, container `--nv`, nvidia-smi sidecar, energy accounting.

## When NOT to use this skill

- One-off quick test where a single number suffices ("does this finish in <1h?" — just run it)
- The tool's authors already published a thorough benchmark on similar hardware
- The user only needs `--time` for SLURM and doesn't care about the math

For these, a short `/usr/bin/time` wrap and a dry estimate is enough.
