# sciAuditor — R front-end (Layer A static)

Round-1.5 parser. Reads an R analysis script, emits a v0.2 inferred
YAML matching `sciAuditor/02_inference_design.md` §4, and (optionally)
a scored audit report in markdown + a machine-readable findings TSV.

## Run

```bash
# YAML only
/home/ahunos/miniforge3/envs/r-env/bin/Rscript sciauditor_r.R \
    --input  /path/to/script.R \
    --output output/script.inferred.yaml

# YAML + scored audit report
/home/ahunos/miniforge3/envs/r-env/bin/Rscript sciauditor_r.R \
    --input      /path/to/script.R \
    --output     output/script.inferred.yaml \
    --report_dir output/script.audit
# → output/script.audit/audit_report.md
# → output/script.audit/audit_findings.tsv
```

Or `--output -` for stdout YAML. Requires R packages `yaml` and
`optparse` (both present in the lab `r-env`).

## What's implemented (round 1)

- `schema_version`, `analysis_unit`, `script`, `runtime_context`
- `config_interface` — optparse `make_option()` calls, including
  `default`, `default_kind` (absolute vs relative), `help`, site
- `inputs` — every call to `fread`, `read.csv`, `read.table`,
  `read.delim`, `readr::read_*`, `readRDS`, `yaml::read_yaml`,
  resolved through `opt$x`, `file.path()`, `paste0()`, simple
  literal-assigns
- `outputs` — every call to `fwrite`, `write.csv`, `write.table`,
  `readr::write_*`, `saveRDS`, `ggsave`, plus `write_mode:`
  (overwrite vs append) and any captured `sep` / `col.names` /
  `header` arg
- `side_effects` — `dir.create`, `options()`, `setwd()`,
  `Sys.setenv()`
- `stochastic_ops` + `seed_policy` summary — every call to a known
  stochastic fn, with a linear-order "is there a `set.seed` earlier
  in the file?" check
- `env_vars_read` / `env_vars_written` — `Sys.getenv` / `Sys.setenv`
- `environment.r_packages` — every `library()` / `require()`
- `organism_inferred` — from `org.*.eg.db` package allowlist
- `genome_build_declared` — pattern-matched in any path template
- `compliance_checks` (eight rules wired, three with BLOCKER severity):
  - **`raw-data-write`** *(BLOCKER)* — fails if any output path resolves
    under `data/raw/`; the raw-data-immutability rule
  - **`header-preserved`** *(BLOCKER)* — fails on any read call with an
    explicit `header = FALSE` / `col.names = FALSE`. Round 1 doesn't
    yet verify if a `colnames(x) <- ...` recovery follows
  - **`hardcoded-contig`** *(BLOCKER)* — fails on any non-comment line
    containing a literal `"chrN"` / `"chrXY"` / `"chrMT"`
  - `relative-paths-only` *(WARNING)* — fails if any optparse default
    is absolute
  - `forbidden-variable-names` *(WARNING)* — any top-level binding to
    one of `[counts, results, mean, median, sum, conditions]`
  - `seed-coverage` *(WARNING)* — every stochastic op must have a
    reaching `set.seed`
  - `script-header-metadata` *(NOTE)* — Author/Name + Date/Purpose in
    the first 10 comment lines
  - `logging-dual-capture` *(NOTE)* — `sink(split=TRUE)` AND
    `globalCallingHandlers(message=…)` both present
  - Plus the auto-emitted `genome-build-tag` *(WARNING)* when
    `organism_inferred` is set but `genome_build_declared` is null
- `audit_findings_preview` — derived from `compliance_checks`,
  including `OK` rows for passes (so the scored report has a
  positive baseline)

## What's deferred (declared in `unresolved`)

- `transformations[]` predicate extraction with rows-before/after
  counts (needs runtime trace; current parser puts the predicate text
  inside `dataframes[].transform.expr` instead)
- `figures[]` first-class enumeration (ggsave calls land in
  `outputs[]` only; grouping by `derived_from` contrast isn't wired)
- `functions_defined[]` with helper-I/O propagation upward to the
  call site (currently each `ggsave` inside `save_figure_3fmt` shows
  as a single output entry per call, not per logical figure)
- `package_resources[]` (only `organism_inferred` derives from this)
- `external_binaries[]` for `system()`/`system2()` calls
- `driver_pattern` detection for R-emits-bash scripts
- `pair_unit` (round 1 is single-script only; pair detection is a
  follow-up where bash launcher metadata is parsed first)
- Runtime trace (Layer B) and LLM assist (Layer C)

## What's wired since round 1

Round 1.5 (this version) added three collectors and the report:

- **`models[]`** — every `DESeqDataSetFromMatrix` / `lm` / `glm` /
  `lmer` / `lmFit` / `glmFit` / `glmQLFit` call, with `formula`,
  `count_data`, `col_data`, `reference_levels` (extracted from any
  `factor(x, levels=…)` call earlier in the file), and a
  `contrasts[]` sub-array from subsequent `results()` / `topTable()` /
  `topTags()` extractions.
- **`dataframes[]`** — every `<-` whose RHS is a positive-list
  dataframe-producing call: any of `READ_FNS`, `merge` / `*_join`,
  `filter` / `subset`, `rbind` / `bind_rows`, `data.frame` /
  `data.table` / `as.data.frame` / `as_tibble`, tidyverse verbs by
  name, `%>%` / `|>` pipes, or `[` subset on a known frame. The
  positive list keeps the count tractable (DESeq2 script: 72 frames
  instead of 343).
- **`hardcoded_data[]`** — every `<-` whose RHS is `c(...)` with ≥5
  literal strings or `list(name=c(...), …)` with ≥5 literals across
  ≥2 sub-vectors. Classified by content into `contig_list` /
  `sample_id_list` / `curated_geneset` / `curated_geneset_structured`
  / `string_list`. PMID/DOI citations harvested from comments in the
  ≤10 lines preceding the binding.
- **`emit_report()`** — when `--report_dir` is set, emits
  `audit_report.md` (headline score, per-category grades A–F,
  findings grouped by severity, inventory) and `audit_findings.tsv`
  for CI.

## Regression fixture

`output/00_build_cohort_wide.inferred.yaml` is the parser's emit for
`cohort_overview/scripts/00_build_cohort_wide.R`. The hand-built
target for the same script is in
`sciAuditor/03_phase0_target_yaml.md` §"YAML 1". Diff'ing the two is
the validation harness for subsequent parser iterations.

## Known minor issues

- `make_option(c("-x", "--name"), …)` calls report site as the line
  containing `c(` rather than the line containing `make_option(`,
  off by 1. The line you'd jump to in an editor still lands you in
  the right option block.
- Integer fields occasionally serialize as floats (`0.0` / `1.0`) in
  YAML due to `yaml::as.yaml` coercion. Cosmetic only.
- `dir.create(dirname(opt$out))` resolves its path as the literal
  text `dirname(opt$out)` rather than a templated path
  `{dirname({opt.out})}`. To fix, the path-template walker would
  need to recognize `dirname()` / `basename()` as identity-with-tag
  ops.

These are all in the bucket "fix when they start mattering".

## Next step

Phase 1 of §7 says "Layer A in parallel for R, Python, bash". The
sibling Python parser (`parser_py/sciauditor_py.py`) and bash parser
(`parser_bash/sciauditor_bash.sh`) should target the Phase 0
fixtures in `sciAuditor/03_phase0_target_yaml.md` §"YAML 2" and
§"YAML 3". Once all three emit comparable v0.2 YAML, Phase 2 wires
the compliance checks and emits the scored audit report.
