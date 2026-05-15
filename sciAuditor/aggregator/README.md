# sciAuditor — aggregator

Project-level auditor. Walks a directory, dispatches every analysis
script to the right per-language parser, auto-detects bash launcher↔
analysis pairs, and emits a cohort-level audit report alongside
per-script reports.

## Run

```bash
/home/ahunos/miniforge3/envs/snakemake/bin/python3 sciauditor_aggregate.py \
    --project-dir /path/to/project/scripts \
    --output-dir  /tmp/cohort_audit \
    --jobs 8 \
    --fail-on BLOCKER
```

Defaults:

- `--rscript /home/ahunos/miniforge3/envs/r-env/bin/Rscript`
- `--python /home/ahunos/miniforge3/envs/snakemake/bin/python3`
- `--jobs min(cpu_count(), 8)` — set `--jobs 1` to disable parallelism
- `--fail-on none` — set to `BLOCKER` / `WARNING` / `NOTE` to make
  the auditor exit 1 when the cohort has findings at or above that
  severity (CI gate). Inclusive: `--fail-on WARNING` counts BLOCKERs
  too. A single line `GATE: PASS|FAIL (reason)` is emitted to stderr.

Benchmark (`coding_peptides_DNAme/scripts`, 35 audited scripts):

| Mode | Parse-phase | Wall total |
|---|---|---|
| `--jobs 1` (sequential) | 26.0 s | 30.0 s |
| `--jobs 8` (parallel)   | 8.2 s  | 12.2 s |

~2.5x wall speedup with byte-identical cohort findings (verified via
`diff <(sort seq.tsv) <(sort par.tsv)`).

## What it does

1. **Discovery**: recursively finds every `*.R`, `*.r`, `*.py`, `*.sh`
   under `--project-dir`.
2. **Pair detection**: parses every `*.sh` with `parser_bash` and
   checks `invocation.script`. If it points to an analysis script in
   the project, records the pair. Pair-consumed launchers are *not*
   audited again standalone (their compliance findings ride along on
   the analysis-side report).
3. **Dispatch**: per-script parser by extension:
   - `.R` / `.r` → `parser_r/sciauditor_r.R` (with `--pair_launcher`
     when paired)
   - `.py`      → `parser_py/sciauditor_py.py`
   - `.sh`      → `parser_bash/sciauditor_bash.py` (YAML only; bash
     parser doesn't emit a scored report yet)
4. **Aggregation**: collects every script's headline grade and
   per-severity finding counts; renders a cohort report.

## Output layout

```
<output-dir>/
├── cohort_audit_report.md    # project-wide summary
├── cohort_findings.tsv       # every finding + script_path column
└── per_script/
    ├── <script>/
    │   ├── analysis.inferred.yaml
    │   ├── audit_report.md
    │   └── audit_findings.tsv
    └── ...
```

`cohort_audit_report.md` contains:
- Project headline (BLOCKER/WARNING/NOTE/OK totals across the cohort)
- Grade distribution histogram
- Per-script table sorted best-to-worst, each row linking to its
  individual `audit_report.md`
- Findings rolled up by `(severity, rule)` showing which patterns
  recur across the cohort

`cohort_findings.tsv` has columns:
`script_path | language | severity | rule | sites | note` — feeds CI
or external dashboards directly.

## Validated against

`coding_peptides_DNAme/scripts/` — a real lab project with 52 source
files (31 R, 21 bash). The aggregator:

- Audited **35 scripts** (17 paired R+bash + 18 standalone) with
  **0 parser errors** across the cohort
- **Project totals**: 8 BLOCKERs, 29 WARNINGs, 27 NOTEs, 170 OKs
- **Grade distribution**: A=4, B=16, C=4, D=1, F=6, no-score=4
- **Top three recurring patterns**:
  - `relative-paths-only` WARNING in **24/35 scripts** (absolute
    paths in optparse defaults, a systemic style issue)
  - `pair-binding-coverage` NOTE in 16/35 (analysis CLI options not
    explicitly bound by the launcher — defaults are silently used)
  - `header-preserved` BLOCKER in **7 scripts** (`fread(...,
    header=FALSE)` without a downstream `colnames(...) <-` recovery)

Runtime: ~2-3 min on a workstation login node for the 35-script run.

## What's not yet implemented

- Workflow-DAG awareness (which script produces what input for which
  other script) — that's the "round 2 cross-script audit" deferred
  from `01_first_principles_brainstorm.md` §12.5
- `--ignore` / `--include` glob filters
- Bash audit_report.md (rolling into Python parser would let
  standalone bash scripts get scored too)
