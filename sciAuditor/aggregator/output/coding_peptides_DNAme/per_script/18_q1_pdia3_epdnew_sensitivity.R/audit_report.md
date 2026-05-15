# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/18_q1_pdia3_epdnew_sensitivity.R`
- **Inferred at**: 2026-05-14T23:37:57-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 7 / 7 (100%) | **A** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 3 | 0 | 100% | A |
| reproducibility | 2 | 0 | 100% | A |
| variables | 1 | 0 | 100% | A |

## Findings

### OK (7)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **relative-paths-only** — compliance check passed: relative-paths-only
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **4**
- Outputs: **5**
- Models: **4**
- Dataframes: **16**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **hg38**

## Models

- `m_model` (L101) — `lm` design `log2_tpm ~ pct_5mC`
- `y_model` (L102) — `lm` design `peptide_count ~ pct_5mC + log2_tpm`
- `total_m` (L103) — `lm` design `peptide_count ~ pct_5mC`
- `m` (L135) — `lm` design `log2_tpm ~ pct_5mC`
