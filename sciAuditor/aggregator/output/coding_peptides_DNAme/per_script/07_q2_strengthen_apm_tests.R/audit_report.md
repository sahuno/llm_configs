# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/07_q2_strengthen_apm_tests.R`
- **Inferred at**: 2026-05-14T23:37:46-0400
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

- **relative-paths-only** (L21, L25, L29, L33) — 4 CLI defaults are absolute paths

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
- Outputs: **6**
- Models: **14**
- Dataframes: **13**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `lm1` (L280) — `lm` design `total_peptide_genes ~ mean_apm_5mC`
- `lm2` (L282) — `lm` design `total_peptide_genes ~ n_expressed_genes`
- `lm3` (L284) — `lm` design `total_peptide_genes ~ mean_apm_5mC + n_expressed_genes`
- `lm0` (L286) — `lm` design `total_peptide_genes ~ 1`
- `lm1c` (L305) — `lm` design `total_peptide_count ~ mean_apm_5mC`
- `lm2c` (L306) — `lm` design `total_peptide_count ~ n_expressed_genes`
- `lm3c` (L307) — `lm` design `total_peptide_count ~ mean_apm_5mC + n_expressed_genes`
- `lm0c` (L308) — `lm` design `total_peptide_count ~ 1`
- `lm_nlrc5` (L394) — `lm` design `total_peptide_genes ~ nlrc5_5mC`
- `lm_apm` (L396) — `lm` design `total_peptide_genes ~ mean_apm_5mC`
- `lm_both` (L398) — `lm` design `total_peptide_genes ~ nlrc5_5mC + mean_apm_5mC`
- `lm_null` (L400) — `lm` design `total_peptide_genes ~ 1`
- `lm_nlrc5_c` (L429) — `lm` design `total_peptide_count ~ nlrc5_5mC`
- `lm_apm_c` (L430) — `lm` design `total_peptide_count ~ mean_apm_5mC`

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_07_q2_strengthen.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/07_q2_strengthen_apm_tests.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (2):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `RESULTS_DIR` | `--outdir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:17 → analysis:33 |
| `LOG_DIR` | `--log_dir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:18 → analysis:37 |
