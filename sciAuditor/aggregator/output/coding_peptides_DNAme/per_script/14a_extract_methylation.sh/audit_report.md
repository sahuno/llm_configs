# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/14a_extract_methylation.sh`
- **Inferred at**: 2026-05-15T00:16:13-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 6 / 7 (86%) | **B** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 1 | 50% | F |
| reproducibility | 3 | 0 | 100% | A |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L20, L21, L22, L23, L24, L25, L26, L32) — 8 variables resolve to absolute paths

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture
- **set-strict-mode** — compliance check passed: set-strict-mode

## Inventory

- Shell variables: **19**
- Side effects: **4**
- Invocation: _no Rscript/python call detected (standalone shell)_
- Genome build declared: **_not declared_**
