# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/22_lm_meth_to_rna_apm.R`
- **Inferred at**: 2026-05-15T00:16:11-0400
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
| reproducibility | 2 | 0 | 100% | A |
| variables | 0 | 1 | 0% | F |

## Findings

### WARNING (2)

- **relative-paths-only** (L22, L25, L30, L33) — 4 CLI defaults are absolute paths
- **forbidden-variable-names** (LNA, LNA) — collisions: results

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **2**
- Outputs: **2**
- Models: **2**
- Dataframes: **6**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `fit` (L97) — `lm` design `log2_tpm ~ meth`
- `fi` (L104) — `lm` design `log2_tpm ~ meth`
