# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/16_compare_definitions.R`
- **Inferred at**: 2026-05-15T00:16:10-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 7 (71%) | **C** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 2 | 1 | 67% | D |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L14, L16, L19, L21) — 4 CLI defaults are absolute paths

### NOTE (1)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **0**
- Outputs: **2**
- Models: **0**
- Dataframes: **2**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **1**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
