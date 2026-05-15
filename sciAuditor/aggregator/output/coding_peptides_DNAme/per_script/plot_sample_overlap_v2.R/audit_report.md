# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/plot_sample_overlap_v2.R`
- **Inferred at**: 2026-05-14T23:57:33-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 6 / 7 (86%) | **B** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 3 | 0 | 100% | A |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### NOTE (1)

- **logging-dual-capture** — no log-capture setup detected

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **relative-paths-only** — compliance check passed: relative-paths-only
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **3**
- Outputs: **1**
- Models: **0**
- Dataframes: **8**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **1**
- Organism inferred: **not detected**
- Genome build declared: **hg38**
