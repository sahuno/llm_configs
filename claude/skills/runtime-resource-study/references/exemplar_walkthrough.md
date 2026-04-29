# Exemplar walkthrough — the samtools sort study

The skill was distilled from a complete 6-stage study on `samtools sort`.
Path: `/data1/greenbab/users/ahunos/projects/biotoolsBenchmarks/samtools/sort/`

Read these files in order to see what a finished study looks like:

## In order of importance

1. **`REPORT.md`** — the deliverable shape. Open it first. The "math"
   callout near the top is what your study should also produce.
2. **`results/20260428_hg38_stage4_inputscan/model.yaml`** — the
   machine-readable model. Your model.yaml should follow this schema.
3. **`PLAN.md`** — running log of decisions and findings. Optional but
   useful as a running notebook.

## Per-stage exemplars

For each stage in your study, look at the corresponding artefact in the
samtools sort tree:

| Your stage | Look at |
|---|---|
| Stage 1 (preflight) | `src/01_inspect_input.sh` and `results/preflight/p17424_1_tumor_chr17.preflight.yaml` |
| Stage 2 (OFAT) | `src/04_submit_grid.py`, `src/05_summarise.R`, `results/20260428_hg38_stage1_ofat/figures/png/` |
| Stage 3 (factorial) | `src/06_submit_stage2.py`, `src/07_summarise_stage2.R` |
| Stage 4 (build mode) | `src/08_submit_stage3a.py`, `src/samtools_container.sh` (the SIF wrapper), `src/09_summarise_stage3a.R` |
| Stage 5 (input scan) | `src/02_subsample.sh` (subsampling), `src/10_submit_input_scan.py`, `src/11_summarise_stage4_model.R` |
| Stage 6 (validation) | `src/12_validate_predictions.py`, `src/13_subsample_merged.py` (intermediate sizes), `src/14_submit_intermediate_scan.py`, `src/15_combined_model_plot.R` |
| Stage 7 (exec summary) | `src/16_executive_summary.R`, `results/combined_model/figures/png/exec_summary.png` |

## What was learned (and why it shaped the skill)

These are the lessons baked into this skill. Each one is a default that
"just works" so future studies don't have to rediscover it.

1. **Page-cache contamination is real and severe.** A 2-condition pilot
   showed `fs_in = 0` for the second condition because the input BAM was
   already cached from condition 1. This is why the skill mandates
   one-condition-per-job + `--exclusive`.

2. **Hardware heterogeneity hides in plain sight.** Stage 1 found one
   replicate at t=32 ran 35 % slower on `isca071` (CPU% 1134 vs 1771).
   `scontrol show node` showed identical attributes — the CPU vintage
   difference was only visible in `/proc/cpuinfo`. This is why the skill
   captures CPU model per replicate and recommends `--exclude=isca071`.

3. **Conda binaries on NFS pay a cold-start tax.** Container vs conda
   showed conda's wall was linear in `minor_pf` count (~2.5 µs/fault) —
   not because containers are faster, but because the apptainer SIF
   consolidates I/O onto fast Weka instead of slow NFS. Stage 4 in the
   skill captures this.

4. **Linear-in-N models fail at ~30× extrapolation.** The 1-term
   `wall = a + b·N` validated within ±5 % on chr17 inputs but errored
   ±16 % on whole-genome BAMs. Adding a `c·file_size` term restored
   ±5 % accuracy. This is why Stage 6 has explicit "refit with 2-term
   if needed" guidance.

5. **`-l 9` is a trap on long-read mod-base BAMs.** 8.4× slower than
   `-l 1` for 3 % smaller output. The compression-level sweep is in
   the OFAT recipe so future tools test the extremes.

6. **RSS saturates near node limit.** Both 16 M and 21 M record BAMs
   landed at ~440 GB peak RSS — same node, same allocator. The model
   in Stage 5 caps RSS at the saturation ceiling.

7. **WekaFS-vs-node-local matters only in spill regime.** When working
   set fits in heap (`-m × threads ≥ rss`), tmp-dir choice is
   irrelevant. Above the spill threshold WekaFS is ~18 % faster than
   `/tmp`. The skill's Stage 2 includes both extremes.

## Total scope of the exemplar

- **6 stages, ~140 jobs**, ~46 minutes of cumulative compute on cpushort
- **6 hours of wall time end-to-end** including iteration, debugging,
  and report writing
- **28 data points across 10 unique input sizes** in the final fit
  (430× range)
- **R² 0.994** on combined fit; ±5 % out-of-sample validation
- **17 scripts** in `src/`, **7 results dirs**, **20+ figures**

Your study doesn't need to match this scope. A simpler tool (fewer
factors, smaller scale range) can finish in 3 stages and 30 minutes.
The skill scales down naturally — skip Stage 4 if there's no SIF, skip
Stage 6 if your calibration range already covers production.
