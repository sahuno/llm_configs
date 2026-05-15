# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/14b_build_matrices.R`
- **Inferred at**: 2026-05-15T00:16:10-0400
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

- **relative-paths-only** (L20, L22, L24, L26, L28) — 5 CLI defaults are absolute paths

### NOTE (1)

- **pair-binding-coverage** — 5 analysis CLI option(s) not bound by launcher (will use defaults): --sample_sheet, --cpg_dir, --promoter_dir, --outdir, --log_dir

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **3**
- Outputs: **4**
- Models: **0**
- Dataframes: **9**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_epdnew_analysis.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/14b_build_matrices.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (0):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
