# sciAuditor — Python front-end (Layer A static)

Round-1 parser. Reads a Python analysis script, emits a v0.2 inferred
YAML matching `sciAuditor/02_inference_design.md` §4, and (optionally)
a scored markdown audit report identical in structure to the R parser.

## Run

```bash
# YAML only
/home/ahunos/miniforge3/envs/snakemake/bin/python3 sciauditor_py.py \
    --input  /path/to/script.py \
    --output output/script.inferred.yaml

# YAML + scored audit report
/home/ahunos/miniforge3/envs/snakemake/bin/python3 sciauditor_py.py \
    --input       /path/to/script.py \
    --output      output/script.inferred.yaml \
    --report_dir  output/script.audit
# → output/script.audit/audit_report.md
# → output/script.audit/audit_findings.tsv
```

System Python (3.6) is too old — `from __future__ import annotations`
and `list[str]` type hints require ≥3.7 / 3.9 respectively. The lab
`snakemake` and `r-env` conda environments both ship Python ≥3.12 with
PyYAML.

## What's implemented

Same surface as the R parser, language-adapted:

- `schema_version`, `analysis_unit`, `script`, `runtime_context`
- `config_interface` — every `parser.add_argument(...)` call
  (works for any ArgumentParser instance name); captures `name`,
  `type`, `default`, `default_kind` (absolute vs relative),
  `required`, `help`, `site`
- `inputs` — every call to `pd.read_csv`, `pd.read_table`,
  `pd.read_parquet`, `pd.read_excel`, `polars.read_csv`, `open`,
  `gzip.open`, `np.load`, `yaml.safe_load`, `json.load` with the
  first positional arg or named `filepath_or_buffer=` /
  `path=` argument resolved through f-strings, `Path(...) / "subpath"`
  builds, and simple variable substitution
- `outputs` — every `*.to_csv` / `.to_tsv` / `.to_parquet` /
  `.to_excel` / `.savefig` method call, plus `write_mode`,
  `write_params.sep`, `write_params.index`
- `side_effects` — `os.makedirs`, `os.mkdir`, `Path.mkdir`,
  `os.chdir`, `os.environ.update`, `logger.setLevel`, basicConfig
- `stochastic_ops` + `seed_policy` summary — `random.*`,
  `np.random.*`, `sklearn` clusterers / splitters; reaching-seed
  check via linear-order `random.seed` / `np.random.seed`
  detection AND inline `random_state=` kwarg
- `env_vars_read` / `env_vars_written`
- `environment.python_packages` — every top-level `import` and
  `from … import …` (base module name only)
- `hardcoded_data[]` — top-level `NAME = [list/tuple/set of ≥5
  string literals]`. Classified into `contig_list` /
  `sample_id_list` / `curated_geneset` / `string_list`. PMID/DOI
  citations harvested from ≤10 preceding comment/docstring lines
- `genome_build_declared` — heuristic search for `mm10` / `hg38` /
  etc. tokens in input/output paths
- `compliance_checks` — exactly the eight rules the R parser ships,
  including the three BLOCKERs:
  - **`raw-data-write`** *(BLOCKER)*
  - **`header-preserved`** *(BLOCKER)* — fires on
    `pd.read_csv(..., header=None)`
  - **`hardcoded-contig`** *(BLOCKER)* — regex on non-comment lines
  - `relative-paths-only`, `forbidden-variable-names`,
    `seed-coverage`, `genome-build-tag` *(WARNING)*
  - `logging-dual-capture`, `script-header-metadata` *(NOTE)* —
    docstring-aware (CLAUDE.md §2 says Python convention puts the
    `Author:` / `Date:` block in the module docstring; we accept that)

## What's deferred

- `dataframes[]` and per-frame column lineage (§3.2) — pandas chains
  are tractable statically but require deeper dataflow analysis
- `transformations[]` predicate extraction
- `models[]` (`sklearn.*().fit(X, y)`, `statsmodels.OLS(...)`,
  `scipy.stats.linregress` etc.)
- `figures[]` first-class enumeration (currently `savefig` lands in
  `outputs[]`)
- `functions_defined[]`
- `external_binaries[]` via `subprocess.run` — already a known idiom
  in the lab; needs wiring
- `pair_unit` from the launcher side — relies on
  `parser_bash/sciauditor_bash.py` (Python-side analysis already
  exposes its argparse signature, so a bash launcher can be paired
  by re-using the same logic as the R pair composer; not yet wired)

## Validated against

`data/src/30_anchor_check_methylation.py` (231 lines): 5 argparse
options (--bedmethyl-dir, --pattern, --anchors, --outdir, --log_dir)
at lines 135-141, 1 pd.read_csv input at L72, 2 to_csv outputs at
L201/214, 3 side_effects (mkdir + logging setLevel + mkdir). All 7
compliance rules pass (the script implements the documented
author/date/purpose block and uses CLAUDE.md-compliant
FileHandler+StreamHandler logging).

`workflows/ont_modkit_pileup/scripts/aggregate_DNAme_across_regions.py`
(268 lines): 2 inputs, 4 argparse options, **fires a real
`forbidden-variable-names` WARNING at L146** for a top-level binding
to `results` (one of CLAUDE.md's six banned names). Demonstrates that
the parser catches an actual rule violation in a production script.
