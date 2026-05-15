# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr/scripts/manually_run_DeSeq2.R`
- **Inferred at**: 2026-05-14T21:46:03-0400
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
