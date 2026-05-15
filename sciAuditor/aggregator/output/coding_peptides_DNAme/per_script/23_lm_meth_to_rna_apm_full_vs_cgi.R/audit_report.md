# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/23_lm_meth_to_rna_apm_full_vs_cgi.R`
- **Inferred at**: 2026-05-14T23:57:31-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 4 / 7 (57%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 2 | 1 | 67% | D |
| reproducibility | 1 | 1 | 50% | F |
| variables | 0 | 1 | 0% | F |

## Findings

### WARNING (2)

- **relative-paths-only** (L24, L26, L28, L31, L33) — 5 CLI defaults are absolute paths
- **forbidden-variable-names** (LNA) — collisions: results

### NOTE (1)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)

### OK (4)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **3**
- Outputs: **1**
- Models: **2**
- Dataframes: **7**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `fit` (L79) — `lm` design `formula`
- `fi` (L83) — `lm` design `formula`
