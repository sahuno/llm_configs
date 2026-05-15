# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/assoc_peptides_DNAme.R`
- **Inferred at**: 2026-05-14T23:57:33-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 7 (71%) | **C** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 2 | 1 | 67% | D |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L14, L18, L22, L26) — 4 CLI defaults are absolute paths

### NOTE (2)

- **logging-dual-capture** — no log-capture setup detected
- **pair-binding-coverage** — 7 analysis CLI option(s) not bound by launcher (will use defaults): --peptide_counts, --gtf, --bedmethyl_dir, --outdir, --min_coverage, --upstream, --downstream

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **header-preserved** — compliance check passed: header-preserved
- **hardcoded-contig** — compliance check passed: hardcoded-contig

## Inventory

- Inputs: **2**
- Outputs: **5**
- Models: **0**
- Dataframes: **9**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **0**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**

## Pair binding

- **Launcher**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/submit_assoc_peptides_DNAme.sh`
- **Analysis**: `/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/scripts/assoc_peptides_DNAme.R`
- **Effective cwd at analysis**: `_not detected_`

**Bindings (0):**

| Launcher var | Analysis flag | Resolved value | Sites |
|---|---|---|---|
