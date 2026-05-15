# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/10_q1_pooled_mediation_summary.R`
- **Inferred at**: 2026-05-14T23:37:49-0400
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

- **relative-paths-only** (L19, L21, L23, L25) — 4 CLI defaults are absolute paths

### NOTE (1)

- **pair-binding-coverage** — 4 analysis CLI option(s) not bound by launcher (will use defaults): --methylation_wide, --peptide_counts, --tpm, --n_boot

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **3**
- Outputs: **5**
- Models: **2**
- Dataframes: **13**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `m_model` (L142) — `lm` design `as.formula("mean_log2_tpm ~ mean_pct_5mC")`
- `y_model` (L144) — `lm` design `y_formula`

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_10_pooled_mediation.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/10_q1_pooled_mediation_summary.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (2):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `RESULTS_DIR` | `--outdir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:13 → analysis:25 |
| `LOG_DIR` | `--log_dir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:14 → analysis:28 |
