# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/27_elasticnet_seed_stability.R`
- **Inferred at**: 2026-05-15T00:16:13-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 3 / 7 (43%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 2 | 33% | F |
| reproducibility | 1 | 1 | 50% | F |
| variables | 0 | 1 | 0% | F |

## Findings

### BLOCKER (1)

- **header-preserved** (L83) — 1 read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)

### WARNING (2)

- **relative-paths-only** (L26, L28, L30, L32, L41, L43) — 6 CLI defaults are absolute paths
- **forbidden-variable-names** (LNA) — collisions: results

### NOTE (2)

- **logging-dual-capture** — partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)
- **pair-binding-coverage** — 11 analysis CLI option(s) not bound by launcher (will use defaults): --cpg_dir, --summary, --sample_sheet, --tpm, --top_n, --seeds, --min_cov_frac, --definition, --include_genes, --outdir, --log_dir

### OK (3)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **4**
- Outputs: **2**
- Models: **0**
- Dataframes: **16**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_27_seed_stability.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/27_elasticnet_seed_stability.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (0):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
