# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/24_elasticnet_meth_to_rna_apm.R`
- **Inferred at**: 2026-05-14T23:38:01-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 3 / 7 (43%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 2 | 33% | F |
| reproducibility | 1 | 1 | 50% | F |
| variables | 0 | 1 | 0% | F |

## Findings

### BLOCKER (1)

- **header-preserved** (L81) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)

### WARNING (2)

- **relative-paths-only** (L32, L34, L36, L38, L45, L47) — 6 CLI defaults are absolute paths
- **forbidden-variable-names** (LNA) — collisions: results

### NOTE (1)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)

### OK (3)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **4**
- Outputs: **2**
- Models: **0**
- Dataframes: **14**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
