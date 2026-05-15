# sciAuditor — bash front-end (Layer A static)

Round-2 parser. Reads a bash analysis or launcher script, emits a
v0.2 inferred YAML, and optionally a scored markdown audit report
(same shape as parser_r / parser_py).

The most important thing it produces is the **`invocation:`** block:
every `Rscript`/`python` call site with its script path and
`--flag $VAR` pairs unwound back to launcher-side variable names.
That block is what the R parser consumes when called with
`--pair_launcher` to compose a `pair_unit:` block.

## Run

```bash
# YAML only
python3 sciauditor_bash.py \
    --input  /path/to/launcher.sh \
    --output output/launcher.inferred.yaml

# YAML + scored audit report
python3 sciauditor_bash.py \
    --input      /path/to/script.sh \
    --output     output/script.inferred.yaml \
    --report_dir output/script.audit
# → output/script.audit/audit_report.md
# → output/script.audit/audit_findings.tsv
```

`--output -` writes YAML to stdout. Requires the Python `yaml` module
(present on the lab login node's system Python, plus snakemake/r-env).

## What's implemented (round 1)

- `schema_version`, `analysis_unit`, `script`, `runtime_context`
- `config_interface` — every `NAME=value` / `NAME="value"` /
  `NAME="${OTHER}/path"` assignment. `${OTHER}` references resolve
  against assigns seen earlier in the file. Booleans and numerics
  coerced; rest stay strings.
- `side_effects` — `mkdir`, `cd`, `export`, `set -e/u/o`, `source` /
  `.` includes, with line numbers
- `invocation` — first `Rscript`/`python3`/`python` call site
  detected. Records `invoker`, `language`, `script`, `site`, and
  `flags[]` (each with `flag`, plus either `value:` for literals or
  `value_var:` + `value_resolved:` for `${VAR}` references)
- `genome_build_declared` — scans every resolved variable value
  for a build token (mm10, hg38, etc.) and surfaces the first hit.
  Used by the genome-build-tag check.
- `compliance_checks` (7 rules; 2 BLOCKER / 3 WARNING / 2 NOTE):
  - **`raw-data-write`** *(BLOCKER)* — fails if mkdir / cp / mv /
    touch / `> redirect` writes anywhere under `data/raw/` or
    `/raw/`. Combines side_effect path inspection with regex scan
    of write-redirect patterns
  - **`hardcoded-contig`** *(BLOCKER)* — non-comment lines
    containing `"chr1"` / `"chrX"` / `"chrMT"` literals
  - `relative-paths-only` *(WARNING)* — any variable resolves to
    an absolute path
  - `forbidden-variable-names` *(WARNING)* — case-insensitive
    match of bash variable names against CLAUDE.md's banned list
    (`counts` / `results` / `mean` / `median` / `sum` / `conditions`)
  - `genome-build-tag` *(WARNING)* — fails if any variable value
    matches genomic file patterns (`.bed` / `.bam` / `.vcf` /
    `.fasta` / `.gtf` / `/reference/`) but no build token
  - `script-header-metadata` *(NOTE)* — Author/Name + Date/Purpose
    in first 10 comment lines
  - `logging-dual-capture` *(NOTE)* — detects `exec > >(tee -a
    $LOG) 2>&1` idiom or `tee -a … 2>&1` variants
  - `set-strict-mode` *(NOTE)* — `set -euo pipefail` (or any
    subset) in the first 30 lines

## What's deferred

- Multi-invocation scripts (round 1 stops at the first match)
- Heredocs (`<<EOF`) and process substitution `<(…)` / `>(…)`
- Function definitions inside the script
- `getopts` argument parsing surfaced as a separate `config_interface`
  (currently bash launchers expose flags as `NAME=value`, which is
  captured; `getopts -i $opt` loops aren't yet recognized)
- Glob expansion / `find` output capturing
- Compound expressions (`if`, `for`, `case` body parsing)

These don't bite for *launcher* scripts (which are 95% var
assignments + one invocation). They will need attention when the
bash parser starts auditing benchmark wrappers like `03_run_one.sh`.

## Pair-mode usage (from the R parser)

The R parser calls this script via `system2()` when invoked with
`--pair_launcher <path>`:

```bash
/home/ahunos/miniforge3/envs/r-env/bin/Rscript ../parser_r/sciauditor_r.R \
    --input          /path/to/analysis.R \
    --pair_launcher  /path/to/launcher.sh \
    --output         output/analysis.pair.yaml \
    --report_dir     output/analysis.pair.audit
```

The R parser uses the launcher YAML's `invocation.flags` to populate
the `pair_unit.binding[]` array — every `--flag` whose `value_var:`
matches an analysis-side optparse option name produces a binding row
with both site numbers (`launcher:18 → analysis:62`).

`pair_unit.effective_cwd_at_analysis` is derived from the first `cd`
side_effect in the launcher.

## Validated against

Five bash fixtures with `--report_dir` enabled:

| Script | Score | Grade | Notes |
|---|---|---|---|
| `14a_extract_methylation.sh` | 6/7 (86%) | B | clean launcher |
| `20a_build_extract_genomewide.sh` | 7/8 (88%) | B | extra check fires |
| `submit_26_elasticnet_genomewide.sh` | 4/7 (57%) | F | missing strict-mode + tee + header |
| `03_run_one.sh` (biotoolsBenchmarks) | 5/7 (71%) | C | getopts-style benchmark wrapper |
| `run_manually_run_DeSeq2.sh` | 5/7 (71%) | C | composes cleanly with R-side via pair_unit |

The bash audit report has the same shape as the R/Python reports
(Headline → By category → Findings by severity → Inventory), so the
aggregator can present all three languages in one cohort table
without special-casing.
