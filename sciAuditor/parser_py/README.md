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

## Round-2 additions

- **`dataframes[]`** — every assignment whose RHS is a positive-listed
  pandas op: `pd.read_*`, `pd.DataFrame`, `pd.Series`, `pd.merge`,
  `pd.concat`, `pd.crosstab`, method calls in `DF_MUTATING_METHODS`
  (`merge` / `join` / `drop` / `dropna` / `fillna` / `groupby` /
  `agg` / `apply` / `assign` / `rename` / `reset_index` /
  `set_index` / `sort_values` / `pivot*` / `melt` / `astype` /
  `to_frame` / `select_dtypes` / `head` / `tail` / `sample` / …) on
  a known frame, plus `df[mask]` / `df.loc[...]` / `df.iloc[...]`
  subscripts. Walks method chains so
  `pd.DataFrame({...}).sort_values(...)` and
  `df.dropna().reset_index()` resolve to the right ancestor.
  Scalar reductions (`sum` / `mean` / `len` / `shape` / `describe`)
  short-circuit so plain summary statistics don't pollute the
  lineage.

- **`models[]`** — sklearn / statsmodels / scipy classes:
  - 30+ sklearn classes (linear models / ensembles / trees / SVM /
    NN / KNN / clustering / mixture / dim-reduction)
  - statsmodels (`OLS` / `WLS` / `GLS` / `GLM` / `Logit` / `MNLogit` /
    `Poisson` / `NegativeBinomial` / `MixedLM` / `PHReg` / `RLM`)
  - `scipy.stats.linregress`

  Captures the construction site and any subsequent `model.fit(X, y)`
  call, plus an inline `random_state=` kwarg if present.
  Hyperparameters extracted from constructor kwargs.

## What's deferred

- Predicate extraction for `transformations[]` with rows-before/after
  counts (Layer B runtime trace work)
- `figures[]` first-class enumeration (currently `savefig` lands in
  `outputs[]`)
- `functions_defined[]`
- `external_binaries[]` via `subprocess.run`
- `pair_unit` from the launcher side
- Heavily-nested chains like
  `clinical.drop_duplicates(...).set_index(...)["dx_age"]` —
  the outer Subscript whose base is a Call isn't yet walked through.
  Round-1 misses about 2-3 such bindings per ~500-line script.

## Validated against

`data/src/30_anchor_check_methylation.py` (231 lines): A grade (7/7,
100%). 5 argparse options at L135-141, 1 input, 2 outputs.

`workflows/ont_modkit_pileup/scripts/aggregate_DNAme_across_regions.py`
(268 lines): C grade (5/7, 71%). Fires a real
`forbidden-variable-names` finding at L146 for a `results = []`
binding (function-local — still flagged per CLAUDE.md's any-scope
rule).

`scripts/AgingLINE1/src/04_clock_and_eaa.py` (539 lines): B grade
(6/7, 86%). Catches:
- **2 sklearn models** — `cv_model = ElasticNetCV(...)` at L142
  with fit at L150 (hyperparameters: `l1_ratio`, `alphas`, `cv`,
  `max_iter`, `random_state`, `n_jobs`); `final_model = ElasticNet(...)`
  at L159 with fit at L173 (`alpha`, `l1_ratio`, `max_iter`,
  `random_state`)
- **6 dataframes** at L175/357/360/443/494/500 including chained
  `pd.DataFrame({...}).sort_values(...)` constructions
- 1 `relative-paths-only` WARNING for an absolute argparse default
  at L82
