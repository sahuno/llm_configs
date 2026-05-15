# sciAuditor — bash front-end (Layer A static)

Round-1 parser. Reads a bash analysis or launcher script and emits a
v0.2 inferred YAML. The most important thing it produces is the
**`invocation:`** block: every `Rscript`/`python` call site with its
script path and `--flag $VAR` pairs unwound back to launcher-side
variable names. That block is what the R parser consumes when called
with `--pair_launcher` to compose a `pair_unit:` block.

## Run

```bash
python3 sciauditor_bash.py \
    --input  /path/to/launcher.sh \
    --output output/launcher.inferred.yaml
```

`--output -` writes YAML to stdout. Requires the Python `yaml` module
(present on the lab login node's system Python).

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
- `compliance_checks`:
  - `script-header-metadata` — Author/Name + Date/Purpose in first
    10 comment lines
  - `relative-paths-only` — flags any variable resolved to an
    absolute path

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

`run_manually_run_DeSeq2.sh` (88 lines): 14 variables detected at the
correct lines, 3 side_effects (mkdir, cd, plus the implicit
`echo` block which we don't model), 1 invocation at L69 with 12
`--flag $VAR` pairs all unwound. Composes cleanly with the R parser's
DESeq2-side YAML into a 12-row pair binding table.
