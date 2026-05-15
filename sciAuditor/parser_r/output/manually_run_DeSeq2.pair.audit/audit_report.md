# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr/scripts/manually_run_DeSeq2.R`
- **Inferred at**: 2026-05-14T22:32:24-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 3 / 6 (50%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 0 | 1 | 0% | F |
| io | 0 | 1 | 0% | F |
| reproducibility | 2 | 1 | 67% | D |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (2)

- **relative-paths-only** (L62, L65, L81, L84) — 4 CLI defaults are absolute paths
- **genome-build-tag** — organism inferred=mouse; no genome build token in inputs/outputs

### NOTE (2)

- **script-header-metadata** (L1) — missing Date or Purpose
- **seed-policy** — seed=1 used across 12 stochastic ops; CLAUDE.md default is 42

### OK (3)

- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **seed-coverage** — compliance check passed: seed-coverage
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **5**
- Outputs: **29**
- Models: **5**
- Dataframes: **72**
- Stochastic ops: **12** (12 seeded, 0 unseeded)
- Hardcoded blocks: **8**
- Organism inferred: **mouse**
- Genome build declared: **_not declared_**

## Models

- `qstat_cki_vs_dmso_dds` (L517) — `DESeqDataSetFromMatrix` design `~condition`
  - contrasts: `qstat_cki_vs_dmso_res`
- `cki_vs_dmso_dds` (L521) — `DESeqDataSetFromMatrix` design `~condition`
  - contrasts: `cki_vs_dmso_res`
- `qstat_vs_dmso_dds` (L525) — `DESeqDataSetFromMatrix` design `~condition`
  - contrasts: `qstat_vs_dmso_res`
- `dds_all_conditions` (L4550) — `DESeqDataSetFromMatrix` design `~condition`
- `all_samples_dds` (L4801) — `DESeqDataSetFromMatrix` design `~condition`

## Pair binding

- **Launcher**: `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr/scripts/run_manually_run_DeSeq2.sh`
- **Analysis**: `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr/scripts/manually_run_DeSeq2.R`
- **Effective cwd at analysis**: `${OUTPUT_DIR}`

**Bindings (12):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `SOURCE_DIR` | `--source_dir` | `/data1/greenbab/projects/triplicates_epigenetics_diyva/RN...` | launcher:18 → analysis:62 |
| `WORKFLOW_DIR` | `--workflow_dir` | `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr` | launcher:17 → analysis:65 |
| `METADATA` | `--metadata_File` | `/data1/greenbab/projects/triplicates_epigenetics_diyva/co...` | launcher:19 → analysis:84 |
| `QC_METRICS` | `--qc_metrics` | `/data1/greenbab/projects/triplicates_epigenetics_diyva/RN...` | launcher:20 → analysis:81 |
| `REF_VARIABLE` | `--ref_variable` | `DMSO` | launcher:27 → analysis:75 |
| `DROP_SAMPLES` | `--drop_samples` | `R.S.2,R.C.3` | launcher:28 → analysis:73 |
| `MIN_READ_COUNTS` | `--min_read_counts` | `50` | launcher:29 → analysis:77 |
| `SMALLEST_GROUP_SIZE` | `--smallest_group_size` | `3` | launcher:30 → analysis:79 |
| `BLIND_TRANSFORM` | `--blind_transform` | `True` | launcher:31 → analysis:71 |
| `PNG_DPI` | `--png_dpi` | `150` | launcher:34 → analysis:91 |
| `RASTERISE_DPI` | `--rasterise_dpi` | `100` | launcher:35 → analysis:93 |
| `LOG_DIR` | `--log_dir` | `logs` | launcher:40 → analysis:88 |
