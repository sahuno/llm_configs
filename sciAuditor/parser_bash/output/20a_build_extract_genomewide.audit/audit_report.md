# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/20a_build_extract_genomewide.sh`
- **Inferred at**: 2026-05-15T00:15:38-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 7 / 8 (88%) | **B** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 2 | 0 | 100% | A |
| io | 1 | 1 | 50% | F |
| reproducibility | 3 | 0 | 100% | A |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L13, L14, L15, L16, L17, L18, L19, L20, L21, L28) — 10 variables resolve to absolute paths

### OK (7)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture
- **set-strict-mode** — compliance check passed: set-strict-mode
- **genome-build-tag** — compliance check passed: genome-build-tag

## Inventory

- Shell variables: **17**
- Side effects: **4**
- Invokes `python` on `-` (L44) with 0 `--flag $VAR` pair(s)
- Genome build declared: **hg38**
