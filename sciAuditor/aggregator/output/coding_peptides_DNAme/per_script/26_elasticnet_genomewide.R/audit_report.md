# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/26_elasticnet_genomewide.R`
- **Inferred at**: 2026-05-15T00:16:13-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 8 (62%) | **D** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 2 | 33% | F |
| reproducibility | 2 | 1 | 67% | D |
| variables | 1 | 0 | 100% | A |

## Findings

### BLOCKER (1)

- **header-preserved** (L116) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)

### WARNING (1)

- **relative-paths-only** (L26, L28, L30, L40, L42) — 5 CLI defaults are absolute paths

### NOTE (2)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)
- **pair-binding-coverage** — 10 analysis CLI option(s) not bound by launcher (will use defaults): --cpg_dir, --sample_sheet, --tpm, --definition, --min_cov_frac, --min_cpgs, --seed, --permute_y_seed, --outdir, --log_dir

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **seed-coverage** — compliance check passed: seed-coverage
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **3**
- Outputs: **3**
- Models: **0**
- Dataframes: **22**
- Stochastic ops: **1** (1 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_26_with_r.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/26_elasticnet_genomewide.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (1):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
| `SLURM_CPUS_PER_TASK` | `--ncores` | `${SLURM_CPUS_PER_TASK}` | launcher:NA → analysis:39 |
