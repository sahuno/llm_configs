# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/30_plotly_html.R`
- **Inferred at**: 2026-05-14T23:38:06-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 4 / 7 (57%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 0 | 1 | 0% | F |
| io | 2 | 1 | 67% | D |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### BLOCKER (2)

- **header-preserved** (L396) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)
- **hardcoded-contig** (L398) — 1 line(s) contain hardcoded contig literals (chrN / chrXY / chrMT)

### NOTE (1)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)

### OK (4)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **relative-paths-only** — compliance check passed: relative-paths-only
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write

## Inventory

- Inputs: **11**
- Outputs: **0**
- Models: **0**
- Dataframes: **36**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
