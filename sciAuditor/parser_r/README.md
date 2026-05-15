# sciAuditor — R front-end (Layer A static)

Round-1 parser. Reads an R analysis script, emits a v0.2 inferred YAML
matching `sciAuditor/02_inference_design.md` §4.

## Run

```bash
/home/ahunos/miniforge3/envs/r-env/bin/Rscript sciauditor_r.R \
    --input  /path/to/script.R \
    --output output/script.inferred.yaml
```

Or `--output -` for stdout. Requires R packages `yaml` and `optparse`
(both present in the lab `r-env`).

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
- `compliance_checks` (five rules wired):
  - `script-header-metadata` — Author + Date / Purpose in header
  - `relative-paths-only` — fails if any optparse default is absolute
  - `forbidden-variable-names` — any top-level binding to one of
    `[counts, results, mean, median, sum, conditions]`
  - `seed-coverage` — every stochastic op has a reaching `set.seed`
  - `logging-dual-capture` — `sink(split=TRUE)` AND
    `globalCallingHandlers(message=…)` both present
- `audit_findings_preview` — derived from `compliance_checks`,
  including `OK` rows for passes (so the scored report has a
  positive baseline)

## What's deferred (declared in `unresolved`)

- `dataframes[]` and the per-frame column-lineage graph (§3.2)
- `transformations[]` predicate extraction (filter / merge / mutate /
  aggregate with rows-before/after counts — needs runtime trace for
  the counts)
- `models[]` extraction (formula / design subset / contrasts) — §3.3
- `figures[]` first-class enumeration
- `functions_defined[]` and helper-I/O propagation
- `hardcoded_data[]` with `kind:` taxonomy and PMID extraction
- `package_resources[]` allowlist (org.*.eg.db, msigdbr, BSgenome.*,
  TxDb.*) — only `organism_inferred` is wired so far
- `external_binaries[]` for `system()`/`system2()` calls
- `driver_pattern` detection for R-emits-bash scripts
- `pair_unit` (round 1 is single-script only; pair detection is a
  follow-up where bash launcher metadata is parsed first)
- Runtime trace (Layer B) and LLM assist (Layer C)

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
