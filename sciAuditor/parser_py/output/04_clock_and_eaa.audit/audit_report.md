# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/AgingLINE1/src/04_clock_and_eaa.py`
- **Inferred at**: 2026-05-14T23:29:32-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 6 / 7 (86%) | **B** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 2 | 1 | 67% | D |
| reproducibility | 2 | 0 | 100% | A |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L82) — 1 CLI defaults are absolute paths

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **logging-dual-capture** — compliance check passed: logging-dual-capture
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **3**
- Outputs: **5**
- Models: **2**
- Dataframes: **6**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `final_model` (L159) — `ElasticNet` design `?`
- `cv_model` (L142) — `ElasticNetCV` design `?`
