# sciAuditor — Audit Report

- **Analysis**: `/data1/greenbab/users/ahunos/projects/biotoolsBenchmarks/samtools/sort/src/03_run_one.sh`
- **Inferred at**: 2026-05-15T00:15:39-04:00
- **Schema**: v0.2 · Layer A (static)

## Headline

| Score | Grade |
|---|---|
| 5 / 7 (71%) | **C** |

## By category

| Category | Pass | Fail | %  | Grade |
|---|---:|---:|---:|---:|
| genomics | 1 | 0 | 100% | A |
| io | 1 | 1 | 50% | F |
| reproducibility | 2 | 1 | 67% | D |
| variables | 1 | 0 | 100% | A |

## Findings

### WARNING (1)

- **relative-paths-only** (L91, L108, L109, L110, L111) — 5 variables resolve to absolute paths

### NOTE (1)

- **logging-dual-capture** — no `exec > >(tee -a $LOG) 2>&1` dual-capture idiom detected

### OK (5)

- **script-header-metadata** — compliance check passed: script-header-metadata
- **forbidden-variable-names** — compliance check passed: forbidden-variable-names
- **raw-data-write** — compliance check passed: raw-data-write
- **hardcoded-contig** — compliance check passed: hardcoded-contig
- **set-strict-mode** — compliance check passed: set-strict-mode

## Inventory

- Shell variables: **47**
- Side effects: **3**
- Invocation: _no Rscript/python call detected (standalone shell)_
- Genome build declared: **_not declared_**
