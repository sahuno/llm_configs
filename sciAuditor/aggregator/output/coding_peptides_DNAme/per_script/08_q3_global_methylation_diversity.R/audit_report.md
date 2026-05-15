# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/08_q3_global_methylation_diversity.R`
- **Inferred at**: 2026-05-15T00:16:08-0400
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

- **pair-binding-coverage** — 6 analysis CLI option(s) not bound by launcher (will use defaults): --methylation_wide, --peptide_counts, --tpm, --top_n, --hyper_threshold, --hypo_threshold

### OK (6)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **logging-dual-capture** — compliance check passed: logging-dual-capture

## Inventory

- Inputs: **3**
- Outputs: **8**
- Models: **4**
- Dataframes: **13**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Models

- `lm0` (L319) — `lm` design `f0`
- `lm1` (L320) — `lm` design `f1`
- `lm2` (L321) — `lm` design `f2`
- `lm3` (L322) — `lm` design `f3`

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_08_q3_global.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/08_q3_global_methylation_diversity.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (2):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `RESULTS_DIR` | `--outdir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:17 → analysis:33 |
| `LOG_DIR` | `--log_dir` | `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme...` | launcher:18 → analysis:49 |
