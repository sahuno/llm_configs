---
name: cohort-overview
description: |
  Build a per-patient × per-assay sample-availability heatmap (SPECTRUM-style
  cohort overview) from a wide TSV. Patient-level annotations (signature,
  BRCA1/2, CCNE1) on top, site strip on left, three-state cells (Yes/No/NA)
  with customizable colours and optional NA→No collapse.

  Use proactively when the user asks for a cohort overview, sample
  availability heatmap, assay coverage plot, data availability figure, or
  SPECTRUM-style heatmap; has a TSV with one row per sample and wants to
  visualize which assays (DLP, ONT, WGS, mpIF, scRNA/scATAC-seq, etc.) were
  run per patient; or types `/cohort-overview`. Keywords: "cohort overview",
  "sample availability", "assay matrix", "per-patient heatmap", "SPECTRUM
  heatmap", "coverage overview", "what samples do we have".

  Uses ComplexHeatmap: row-split by assay, per-patient sample slots, patient
  annotations on top, site strip on left.
---

# Cohort Overview Heatmap

Recreates a SPECTRUM-style cohort data-availability heatmap showing, for each
patient, which assays were run on which samples, alongside patient-level
genomic annotations and per-sample site labels.

**What you'll produce:** a `results/{png,pdf,svg}/` directory with a single
heatmap. Rows are grouped by assay; within each assay block, samples are
stacked by a consistent per-patient slot index (so sample S02 of patient 017
always sits in the same row across every assay block). Columns are patients,
ordered by the user's first patient-level annotation (typically a mutational
signature).

## When to use this skill

Trigger whenever a user with a per-sample table wants a "what have we
profiled" overview. Common phrasings: "make a cohort overview", "plot sample
availability across assays", "which patients have DLP + WGS + scRNA-seq",
"recreate the SPECTRUM data heatmap".

Skip this skill for single-assay plots, per-gene heatmaps, or anything that
isn't a patient × assay availability matrix.

## The two scripts

This skill ships two scripts. Do not rewrite them from scratch — copy them
into the user's project (usually `scripts/`) and adapt only if the user asks:

1. **`scripts/01_generate_mock_cohort.R`** — generates `data/cohort_wide.tsv`
   with 85 patients / ~290 samples / 7 assays. Useful when the user wants a
   demo run, or to sanity-check their own TSV against the expected schema.

2. **`scripts/02_plot_cohort_heatmap.R`** — the main plotter. Uses optparse,
   ComplexHeatmap, and writes PNG/PDF/SVG. Fully configurable via CLI flags.

Both live at `<skill-dir>/scripts/` (the skill directory Claude Code loaded
this SKILL.md from). Copy them with `cp`; don't regenerate them.

## Input TSV schema (wide format, one row per sample)

| Column group       | Columns                                                              | Notes                                                        |
|--------------------|----------------------------------------------------------------------|--------------------------------------------------------------|
| sample keys        | `patient_id`, `sample_id`                                            | `sample_id` unique per row; `patient_id` repeats             |
| sample attribute   | `site`                                                               | Adnexa, Omentum, Blood, Ascites, …                           |
| patient-level      | `signature`, `BRCA1`, `BRCA2`, `CCNE1`                               | **must be constant within a `patient_id`** — script validates |
| assay availability | `DLP`, `ONT`, `WGS`, `mpIF`, `scATAC-seq`, `scRNA-seq`, `scRNAseqVDJ` | cell values: `Yes` \| `No` \| `NA`                           |

`NA` means "not attempted / unknown" — semantically distinct from `No`
("attempted, failed or negative"). The plot encodes them as different
colours by default.

A 3-line example lives at `examples/cohort_wide.tsv`. Read it only if the
user is debugging their own file format.

## Plot semantics

- **Top annotation:** one block per patient, ordered by the first
  `--patient-cols` column (default: `signature`).
- **Row split:** one block per assay, in `--assays` order.
- **Within each assay block:** samples are stacked by a per-patient slot
  index (ordered by `site`, then `sample_id`). Block height = the largest
  number of samples any patient has.
- **Cell colours:** `Yes` → black, `No` → grey, `NA` → white
  (all three overridable via CLI). The default palette is chosen so that
  **ink = attempt**: dark cells = success, grey cells = attempted-but-failed,
  blank cells = never attempted. This lets you see coverage gaps at a glance.
- **Left strip:** modal Site across patients for that row — tells you "most
  samples in slot 1 are from the primary tumour site".

## Workflow

### 1. Inspect the user's data

- If the user has their own TSV: read the first ~5 lines and confirm all
  required columns are present. If assay columns have values other than
  `Yes`/`No`/`NA`, ask what they mean before proceeding.
- If the user wants a demo: run `scripts/01_generate_mock_cohort.R` from
  their project directory to produce `data/cohort_wide.tsv`.
- If patient-level columns vary within a `patient_id`, the plotter will
  error. Warn the user and ask whether to take the first value, the mode,
  or fix upstream.

### 2. Copy scripts into the user's project

```bash
mkdir -p <project>/scripts <project>/data <project>/results
cp <skill-dir>/scripts/01_generate_mock_cohort.R <project>/scripts/
cp <skill-dir>/scripts/02_plot_cohort_heatmap.R <project>/scripts/
```

### 3. Run the plotter

```bash
Rscript scripts/02_plot_cohort_heatmap.R --input data/cohort_wide.tsv
Rscript scripts/02_plot_cohort_heatmap.R --help     # full option list
```

### 4. Check the output

Figures land under `results/{png,pdf,svg}/`. Default stem is
`cohort_overview_heatmap`. Open the PNG and verify: patients ordered by
signature, all listed assays present as row blocks, cell colours match
`--yes-color` / `--no-color` / `--na-color`.

A reference PNG from the mock data is at `examples/cohort_overview_heatmap_reference.png`
if you want to show the user what "correct" looks like.

## CLI options (script `02_plot_cohort_heatmap.R`)

| Flag                                 | Default                                      | Purpose                                                   |
|--------------------------------------|----------------------------------------------|-----------------------------------------------------------|
| `-i`, `--input`                      | **required**                                 | path to wide TSV                                          |
| `-o`, `--outdir`                     | `results`                                    | output root (creates `pdf/`, `png/`, `svg/`)              |
| `-n`, `--name`                       | `cohort_overview_heatmap`                    | file stem                                                 |
| `-W`, `--width`                      | `14`                                         | figure width (inches)                                     |
| `-H`, `--height`                     | `8`                                          | figure height (inches)                                    |
| `--assays`                           | 7-assay default                              | comma-separated assay columns, in plot order              |
| `--patient-cols`                     | `signature,BRCA1,BRCA2,CCNE1`                | patient-level annotation columns; 1st orders columns      |
| `--sig-order`                        | `FBI,HRD,HRD-Del,HRD-Dup,TD,Undetermined,NA` | factor order for the 1st patient-level col                |
| `--patient-id-col`                   | `patient_id`                                 | patient-id column name                                    |
| `--sample-id-col`                    | `sample_id`                                  | sample-id column name                                     |
| `--site-col`                         | `site`                                       | site column name                                          |
| `--yes-color`                        | `#000000`                                    | cell colour for Yes (attempted, succeeded)                |
| `--no-color`                         | `#BDBDBD`                                    | cell colour for No (attempted, failed/negative)           |
| `--na-color`                         | `#FFFFFF`                                    | cell colour for NA (not attempted / unknown)              |
| `--na-as-no`                         | off                                          | render NA as No (collapses legend to Yes/No)              |
| `--no-png` / `--no-pdf` / `--no-svg` | off                                          | skip a format                                             |

## Common tailoring

- **Subset of assays:** `--assays "DLP,WGS,ONT"` (order matters — top to bottom).
- **Custom patient annotations:** `--patient-cols "signature,TP53,RB1"` —
  the first column still determines patient ordering. Unknown columns get an
  auto palette (uses `RColorBrewer` if available).
- **Two-state cells:** `--na-as-no` collapses NA into No and shortens the
  legend to Yes/No.
- **Wider canvas for big cohorts:** `--width 20 --height 10` for 150+ patients.

## Required R packages

- **Required:** `optparse`, `dplyr`, `tidyr`, `readr`, `ComplexHeatmap`, `circlize`
- **Optional:** `svglite` (true SVG), `showtext` + `sysfonts` (Arial),
  `RColorBrewer` (nicer palettes for custom `--patient-cols`)

If packages are missing, install with:
```r
install.packages(c("optparse","dplyr","tidyr","readr","circlize","svglite","showtext","sysfonts","RColorBrewer"))
# ComplexHeatmap via Bioconductor:
if (!require("BiocManager")) install.packages("BiocManager")
BiocManager::install("ComplexHeatmap")
```

## Expected final layout

```
<project>/
├── data/cohort_wide.tsv
├── scripts/
│   ├── 01_generate_mock_cohort.R
│   └── 02_plot_cohort_heatmap.R
└── results/
    ├── png/cohort_overview_heatmap.png
    ├── pdf/cohort_overview_heatmap.pdf
    └── svg/cohort_overview_heatmap.svg
```

## Troubleshooting

- **"Arial font not found in PostScript font database"** — harmless; the
  script falls back to `sans`. Install `showtext` + `sysfonts` for true Arial.
- **SVG export fails** — install `svglite`. The base `svg()` device needs X11
  which is often unavailable on macOS; `svglite` is self-contained.
- **Patient-level column not constant within `patient_id`** — the plotter
  errors with the offending patient_id. Fix upstream or collapse to the mode.
- **No rows render for an assay** — all values for that column are `NA` and
  `--na-as-no` is off. Either drop the assay from `--assays` or pass `--na-as-no`.
