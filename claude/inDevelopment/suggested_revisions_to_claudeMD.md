# Suggested Revisions to CLAUDE.md

Date: 2026-03-02
Context: Align CLAUDE.md with revised `claude/scripts/init_project.py` (v0.2.0)

---

## 1. §1.5 — Project scaffold is outdated

**Current** (lines 18-29):
```
<project_root>/
├── data/inbox/
├── data/raw/
├── data/processed/
├── src/
├── results/
├── figures/{png,pdf,svg}/        <-- figures at root level
├── workflows/{wf_snakemake,wf_nextflow}/
└── docs/
```

**Problem**: Figures are now inside results dirs, not at root. Missing `logs/`, `softwares/containers/`, genome-tagged processed dir.

**Suggested replacement**:
```
<project_root>/
├── config.yaml
├── sample_sheet.tsv
├── data/
│   ├── inbox/                    # staging — review before promoting to raw/
│   ├── raw/                      # IMMUTABLE after initial deposit
│   └── processed/{genome}/       # tagged by genome build
├── src/                          # numbered scripts: 01_, 02_, ...
├── results/
│   └── {date}_{description}/     # one dir per run
│       └── figures/{png,pdf,svg}/
├── workflows/wf_snakemake/       # configs, profiles/slurm, rules, scripts
├── softwares/containers/
├── logs/
└── docs/
```

---

## 2. §1.5 — Remove mandatory README per directory

**Current** (line 31):
> Each directory must have a `README.md` describing its purpose, contents, and any scripts within it.

**Problem**: 15+ boilerplate READMEs that go stale immediately. The init script generates one good top-level README with a tree diagram instead.

**Suggested replacement**:
> A top-level `README.md` is generated with project metadata, directory tree, and aims. Additional READMEs should only be created when the user requests documentation.

This is consistent with the existing Documentation rule (line 103): "Do not create READMEs proactively."

---

## 3. §1.5 — Mention init_project.py and project types

**Current**: No mention of the init script or `--type` parameter.

**Suggested addition** (after the scaffold diagram):
> Use `claude/scripts/init_project.py` to scaffold projects:
> ```bash
> # Scaffold in current directory:
> python init_project.py --type analysis --genome hg38
>
> # Create new subdirectory:
> python init_project.py --name my_project --type pipeline --engine snakemake --genome mm10
> ```
> Project types: `analysis` (default workflow dirs), `pipeline` (engine-specific layout, requires `--engine`), `ml` (adds notebooks, model dirs).

---

## 4. §4 — Run naming convention conflicts with init_project.py

**Current** (line 280):
> Run naming convention: `{version}_{genome}_{data_subset}` (e.g. `v1_hg38_10pct`, `v2_mm10_full`).

**init_project.py uses**: `{date}_{description}` (e.g. `20260302_v1`)

**Decision needed**: Pick one convention. Options:
- **A**: `{date}_{description}` — chronologically sortable, self-documenting when it was run
- **B**: `{version}_{genome}_{subset}` — more descriptive of content
- **C**: `{date}_{version}_{description}` — hybrid (e.g. `20260302_v1_hg38_full`)

**Recommendation**: Option A (`{date}_{description}`) is simpler and the genome is already in `config.yaml`. The date makes runs naturally sort in `ls`. Update CLAUDE.md to match.

---

## 5. §7 — Figure paths reference old root-level structure

**Current** (line 386):
> Save every figure as PNG, PDF, and SVG in their respective subdirectories (`figures/png/`, `figures/pdf/`, `figures/svg/`).

**Problem**: Figures now live inside results dirs, not at a root-level `figures/` directory.

**Suggested replacement**:
> Save every figure as PNG, PDF, and SVG in their respective subdirectories within the current results directory (`results/{date}_{description}/figures/png/`, `.../pdf/`, `.../svg/`).

Also update line 152:
```
# Current:
"Saved: figures/pdf/volcano_CKi_vs_DMSO.pdf (+ png, svg)"

# Should be:
"Saved: results/20260302_v1/figures/pdf/volcano_CKi_vs_DMSO.pdf (+ png, svg)"
```

---

## 6. §10 — Quality gate figure path

**Current** (line 469):
> Figures are saved in all 3 formats (png, pdf, svg)

**Suggested revision**:
> Figures are saved in all 3 formats under `results/{run}/figures/{png,pdf,svg}/`

---

## 7. §4 — Sample sheet format (already done)

**Status**: Updated to `patient, sample, condition, assay, path, genome` ✓

**Note**: Also update `profiles/setup_preferences.yaml` if it exists — CLAUDE.md references it as the canonical definition.

---

## 8. New addition — Document the `docs/manuscript/figures/` distinction

The scratch.md notes make an important distinction that isn't in CLAUDE.md:

> `docs/manuscript/figures/` — multi-panel figures collated with python scripts on letter size paper. This is NOT a substitute for `results/{run}/figures/`

**Suggested addition** to §7:
> **Two figure locations**:
> - `results/{run}/figures/{png,pdf,svg}/` — individual analysis figures per run
> - `docs/manuscript/figures/` — final multi-panel publication figures assembled from individual figures (created when preparing a manuscript, not during analysis)

**Decision needed**: Should `docs/manuscript/` be part of the init scaffold or created manually when manuscript prep begins?

---

## Summary of changes

| Section | Change | Impact |
|---------|--------|--------|
| §1.5 scaffold | Update tree diagram | High — this is what Claude reads every session |
| §1.5 READMEs | Relax to top-level only | Low — aligns with existing §2 Documentation rule |
| §1.5 init script | Document the tool | Medium — makes the script discoverable |
| §4 run naming | Reconcile convention | Medium — prevents confusion |
| §7 figure paths | Update to results-relative | High — affects every figure-saving instruction |
| §10 quality gate | Update figure path | Low — cosmetic |

---

## Open questions

- [ ] Which run naming convention? `{date}_{description}` vs `{version}_{genome}_{subset}`
- [ ] Should `docs/manuscript/` be in the init scaffold?
- [ ] Should the philosophy of research publication section (lines 450-457) be formalized or left as stream-of-thought?
