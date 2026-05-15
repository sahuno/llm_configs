# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/11_q9_apm_methylation_io_response.R`
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

- **relative-paths-only** (L19, L22, L25, L28, L31, L34, L37) — 7 CLI defaults are absolute paths

### NOTE (1)

- **pair-binding-coverage** — 7 analysis CLI option(s) not bound by launcher (will use defaults): --apm_burden, --apm_pergene, --peptide_diversity, --global_meth, --cta_merged, --metadata, --cta_demeth_threshold

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **6**
- Outputs: **8**
- Models: **0**
- Dataframes: **19**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_11_q9_io_response.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/11_q9_apm_methylation_io_response.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (2):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `RESULTS_DIR` | `--outdir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:19 → analysis:37 |
| `LOG_DIR` | `--log_dir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:20 → analysis:43 |
