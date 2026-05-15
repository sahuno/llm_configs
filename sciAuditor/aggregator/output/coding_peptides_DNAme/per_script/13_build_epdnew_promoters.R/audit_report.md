# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/13_build_epdnew_promoters.R`
- **Inferred at**: 2026-05-15T00:16:09-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 7 (71%) | **C** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 2 | 33% | F |
| reproducibility | 2 | 0 | 100% | A |
| variables | 1 | 0 | 100% | A |

## Findings

### BLOCKER (1)

- **header-preserved** (L93) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)

### WARNING (1)

- **relative-paths-only** (L17, L19, L22, L31, L33) — 5 CLI defaults are absolute paths

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **3**
- Outputs: **5**
- Models: **0**
- Dataframes: **10**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
