# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/06_apm_trimodal_distributions.R`
- **Inferred at**: 2026-05-15T00:16:07-0400
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

- **relative-paths-only** (L17, L21, L25, L29) — 4 CLI defaults are absolute paths

### NOTE (1)

- **pair-binding-coverage** — 3 analysis CLI option(s) not bound by launcher (will use defaults): --methylation_wide, --peptide_counts, --tpm

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
- Dataframes: **31**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **1**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_06_apm_trimodal.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/06_apm_trimodal_distributions.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (2):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `RESULTS_DIR` | `--outdir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:17 → analysis:29 |
| `LOG_DIR` | `--log_dir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:18 → analysis:33 |
