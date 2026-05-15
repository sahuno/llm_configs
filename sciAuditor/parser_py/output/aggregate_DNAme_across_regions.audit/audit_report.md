# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/workflows/ont_modkit_pileup/scripts/aggregate_DNAme_across_regions.py`
- **Inferred at**: 2026-05-14T23:19:21-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 7 (71%) | **C** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 3 | 0 | 100% | A |
| reproducibility | 1 | 1 | 50% | F |
| variables | 0 | 1 | 0% | F |

## Findings

### WARNING (1)

- **forbidden-variable-names** (L146) — collisions: results

### NOTE (1)

- **logging-dual-capture** — no FileHandler+StreamHandler logging detected

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **relative-paths-only** — compliance check passed: relative-paths-only
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **2**
- Outputs: **0**
- Models: **0**
- Dataframes: **0**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
