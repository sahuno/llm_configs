# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/users/ahunos/projects/cohort_overview/scripts/00_build_cohort_wide.R`
- **Inferred at**: 2026-05-14T21:46:02-0400
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 2 / 4 (50%) | **F** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| io | 0 | 1 | 0% | F |
| reproducibility | 1 | 1 | 50% | F |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L15, L17, L19) — 3 CLI defaults are absolute paths

### NOTE (1)

- **logging-dual-capture** — no log-capture setup detected

### OK (2)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names

## Inventory

- Inputs: **2**
- Outputs: **1**
- Models: **0**
- Dataframes: **13**
- Stochastic ops: **0** (0 seeded, 0 unseeded)
- Hardcoded blocks: **2**
- Organism inferred: **not detected**
- Genome build declared: **_not declared_**
