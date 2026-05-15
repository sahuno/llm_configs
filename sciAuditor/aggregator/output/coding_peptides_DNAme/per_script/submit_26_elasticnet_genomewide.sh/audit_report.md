# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_26_elasticnet_genomewide.sh`
- **Inferred at**: 2026-05-15T00:16:14-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 4 / 7 (57%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 1 | 50% | F |
| reproducibility | 1 | 2 | 33% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L19, L20, L21, L22) — 4 variables resolve to absolute paths

### NOTE (2)

- **script-header-metadata** (L1) — missing Author/Date/Purpose in first 10 comment lines
- **logging-dual-capture** — no `exec > >(tee -a $LOG) 2>&1` dual-capture idiom detected

### OK (4)

- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **set-strict-mode** — compliance check passed: set-strict-mode

## Inventory

- Shell variables: **4**
- Side effects: **1**
- Invokes `R` on `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/26_elasticnet_genomewide.R` (L27) with 1 `--flag $VAR` pair(s)
- Genome build declared: **_not declared_**
