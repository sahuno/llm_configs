# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/25_nlrc5_lasso_cpgs.R`
- **Inferred at**: 2026-05-15T00:16:12-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 4 / 7 (57%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 2 | 33% | F |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### BLOCKER (1)

- **header-preserved** (L63) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)

### WARNING (1)

- **relative-paths-only** (L24, L26, L28, L34, L36) — 5 CLI defaults are absolute paths

### NOTE (1)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)

### OK (4)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **3**
- Outputs: **1**
- Models: **0**
- Dataframes: **13**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
