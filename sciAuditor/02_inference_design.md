# sciAuditor — Inference Layer (round 2, section 1)

> Goal: given an analysis script (R / Python / bash) and optionally the
> data it operates on, automatically extract a structured description
> of what the script *actually does* — inputs, outputs, column-level
> operations, statistical models, filters, stochastic ops, side
> effects.
>
> This document explores the **inference** side of the manifest-vs-
> inference question. The **manifest** side is deferred — it will be
> designed against `casetrack` (https://github.com/sahuno/casetrack)
> in a later iteration. For now, inference output is a generic
> structured form; once casetrack's manifest schema is stable, we
> shape the output to match.
>
> **Schema state**: §4 carries **v0.2**, which absorbs the ten deltas
> from `03_phase0_target_yaml.md` and fourteen more from
> `04_realcase_DESeq2_addendum.md` (S11–S25). v0.1 is retired.

---

## 0. Why inference matters even if we have a manifest

A scientist-authored manifest is **what they say the script does**.
Inference produces **what the code actually does**. The audit lives in
the diff between the two.

- Manifest only → no enforcement; the manifest drifts from reality.
- Inference only → no contract; nothing to compare against, no clear
  pass/fail.
- Manifest + inference → the auditor can flag every divergence as a
  finding. This is the design target.

A useful side-effect: the first run of inference on a legacy script
produces a draft manifest the scientist can edit and commit. That's
the on-ramp for adopting manifests on existing projects.

---

## 1. What inference must extract

Per script, the auditor should produce a structured artifact with:

### 1a. I/O
- **Inputs**: every file the script reads
  - path (literal, templated, or "dynamic-unresolved")
  - format (csv/tsv/parquet/bed/bedMethyl/rds/h5/…)
  - read parameters (delimiter, header, comment char, na strings,
    skip rows)
  - inferred schema at read time (columns + dtypes, if a sample is
    available)
- **Outputs**: every file the script writes
  - same fields as inputs, plus the schema *as written*
  - whether the write overwrites an existing path
- **Implicit I/O**: library-internal reads (e.g. `tximport` reading a
  directory of `quant.sf` files, `DESeq2::DESeqDataSetFromMatrix`
  consuming a metadata frame). Driven by a small library-knowledge
  catalogue.

### 1b. Columns
- For every dataframe in the script, track:
  - origin (which read call introduced it)
  - columns added, renamed, dropped, type-cast
  - columns *referenced* in any expression (predicate, formula,
    aesthetic mapping, group_by, summarise, …)
  - columns that flow to outputs

This produces a per-dataframe column lineage graph.

### 1c. Transformations
- Filtering (predicate, estimated row reduction)
- Normalisation (method + parameters, applied to which columns)
- Log/scale/centre (base, pseudo-count, target columns)
- Aggregation (group keys, agg function, target columns)
- Imputation (method, target columns, what counted as "missing")
- Joins (left/right keys, join type)
- Pivoting/reshaping

### 1d. Statistical models
- Function called (e.g. `DESeq`, `lmFit`, `glm`, `lmer`)
- Formula / design (as resolved string + parsed terms)
- Reference levels and contrasts
- Multiple-testing correction (method, family scope)

### 1e. Stochastic ops & seeds
- Every call to a known stochastic function
- Was `set.seed()` / `np.random.seed()` / `random.seed()` in scope
  before the call?
- Was the seed value a literal or read from config?

### 1f. Side effects
- Global option mutations (`options()`, `pd.set_option`,
  `sys.setrecursionlimit`)
- Env var reads/writes
- Working-directory changes
- Caches written outside declared output paths

### 1g. Provenance metadata
- Git rev of the script
- Language version (R / Python)
- Loaded packages and their versions (best-effort: parse `library()`
  / `import` and reconcile with `renv.lock` / `uv.lock` if present)
- Container digest (if executed in one)

---

## 2. Three layers of inference

### Layer A — Static analysis (always on)
Parse the source AST and walk it.

- **R**: `base::parse()`, `base::getParseData()`, `rlang` for NSE
  resolution in tidyverse pipelines, `codetools::findGlobals()` for
  dataflow.
- **Python**: `ast` module for skeleton; `libcst` for round-trippable
  parses; optionally `jedi` or `pylsp` for symbol resolution.
- **Bash**: `bashlex` for AST; regex for the common idioms (`while
  read`, here-docs).

**Strengths:** deterministic, fast (~seconds), zero execution risk,
runs anywhere.

**Limits:** can't resolve dynamic paths (`paste0(prefix, sample,
".tsv")`), can't see inside `source()`-d helpers without import-graph
walking, library-internal I/O invisible.

### Layer B — Runtime trace (opt-in, dry-run mode)
Re-execute the script on a tiny sampled or synthetic dataset, with
key functions monkey-patched to log everything.

- Wrap every `read.*` and `write.*` in a logger that records: path,
  args, returned dimensions, returned column schema, call site
  (file:line).
- Wrap stochastic functions to record whether a seed was set.
- Capture dataframes at "checkpoint" lines (after read, before
  write, before model fit) and serialise schemas.
- R: `trace()`, `setHook("on.exit", …)`, or load-time injection via
  `.Rprofile`.
- Python: monkey-patch `pandas.read_*` / `to_*`, `polars.read_*`,
  `numpy.load`; use `sys.settrace` for line-level events if needed.

**Strengths:** sees ground truth including dynamic paths and
library-internal I/O.

**Limits:** needs the script to run end-to-end (or to a checkpoint)
on something; setup cost for synthetic / sampled data; some scripts
are slow even on small data.

### Layer C — LLM-assisted reading (opt-in)
Feed the script (and Layer A output) to an LLM with a structured-
output schema, ask it to fill in the bits static analysis couldn't:

- Resolve human-meaningful column roles ("this is the response
  variable", "this is a technical covariate") that aren't explicit
  in the code.
- Decode `paste0`-constructed paths into templates with named slots.
- Interpret NSE-heavy tidyverse pipes.
- Summarise the script's scientific intent in one sentence.

**Strengths:** handles narrative semantics; degrades gracefully.

**Limits:** non-deterministic; token cost; needs careful
guardrails to avoid hallucinated columns.

### Hybrid is the design
- Layer A always runs and produces the skeleton.
- Layer B runs in CI or on `--deep`; ground-truths the dynamic bits.
- Layer C fills semantic gaps and is checked against A & B; any LLM
  claim contradicted by A or B is dropped.
- **Disagreement between layers is itself a finding**: e.g., static
  says column `treatment` is read but runtime never accessed it → the
  branch containing that read may be dead code.

---

## 3. Per-element inference recipes

### 3.1 Path inference (R example)

For each call to a read/write function:

```text
literal string  → done
variable        → walk back to assignment; recurse
paste/paste0/   → extract template + variable slots; record as
glue/sprintf       parameterised path; resolve variables recursively
file.path(...)  → same, with "/" join
fs::path(...)   → same
config[[k]]     → look up k in any parsed yaml/json config in scope
loop iterator   → record pattern, mark cardinality = loop length
```

Output: `{path_template, slot_bindings, resolution_confidence}`.

A worked example:

```r
samples <- yaml::read_yaml("config.yaml")$samples
for (s in samples) {
  d <- readr::read_tsv(file.path("data/raw", paste0(s, ".counts.tsv")))
  ...
}
```

Inferred:
```yaml
inputs:
  - path_template: "data/raw/{sample}.counts.tsv"
    slot_bindings:
      sample: "$.samples[*] from config.yaml"
    resolution_confidence: high
    cardinality: length(config.yaml::samples)
```

### 3.2 Column inference

For every dataframe binding, maintain a tracked schema:

- After `read_*` with `header=TRUE`: columns = file header.
- After `header=FALSE`: columns = `V1..VN` — **flag as audit warning
  unless the user explicitly assigns names next**.
- After `mutate(new_col = ...)` / `df["new_col"] = ...`: add.
- After `rename(new = old)`: rename, record the mapping.
- After `select(...)` / `df[[col]]`: project.
- After `pivot_longer/wider`: reshape; flag because column lineage
  becomes coarse.
- After joins: union of left + right, deduplicating on the `by`
  columns; **flag** if `by` is implicit.

The lineage graph supports questions like: "which raw-file columns
flow into the output `padj` column?"

### 3.3 Formula / model inference

For each modelling call:

- Extract the `formula = …` or `design = …` argument verbatim.
- If it's a literal `~ batch + condition`: parse terms via the
  language's formula grammar.
- If it's a variable: walk back; if the variable is built via
  `as.formula(paste(…))`, extract the components and record as a
  *templated formula* with confidence ≤ medium.
- For each term, resolve to a column in the design dataframe (which
  must itself be tracked via §3.2).
- Record the reference level by looking for prior `factor(x, levels=…)`
  or `relevel()` calls; first level = reference.
- Record the **design subset**: for scripts that build per-model
  dataframes (e.g. DESeq2 with one DDS per contrast), capture
  `design_subset.rows` (the dataframe id of the per-model metadata
  slice) and `design_subset.cols` (the per-model column subset of the
  count matrix). This makes "what data is this model fit to?"
  auditable.
- Record the **per-model `pre_filter`**: filters applied immediately
  before `DESeq()` / `lmFit()` / etc. are model-local, distinct from
  global filters in `transformations:`.
- Record each `results()` / `topTags()` / contrast-extraction call as
  a sub-entry in `models[].contrasts[]`, with its own `site` and
  `coef_or_contrast` identifier. Downstream figures and outputs
  reference these contrast ids.
- **Cross-model symmetry**: when a script fits multiple models, the
  auditor should compute `models.filter_symmetry` — flag if the same
  filter expression appears literally identical across all models
  (likely intentional symmetry), differs only in threshold values
  (likely drift), or is structurally different (likely deliberate).

### 3.4 Filter inference

Detect filtering predicates (`filter()`, `subset()`, `df[mask, ]`,
`df.query()`, `df[df.x > k]`) and extract:
- the predicate expression
- the columns it depends on
- if runtime trace available: rows before / rows after

### 3.5 Stochastic-op / seed inference

Per call site:

- Build a set of known stochastic call sites in the script
  (`sample`, `kmeans`, `umap`, `Rtsne`, `clusterProfiler::GSEA`,
  `np.random.*`, `random.*`, `sklearn.*` with `random_state=None`,
  etc.).
- Walk the control-flow graph backwards from each: is there a
  reaching definition of `set.seed` / `np.random.seed` /
  `random.seed`?
- Record `seed_set: bool` and `seed_value: <literal | expr>` per
  call.

After walking all sites, populate the top-level `seed_policy:`
summary:

- `declared_value` — the most common seed in the script (e.g. `1`).
- `coverage` — counts of `{seeded, unseeded, total}`.
- `divergence_from_claude_default` — `true` when `declared_value`
  differs from CLAUDE.md's mandated default of `42`.
- `severity` — `WARNING` if any stochastic op is unseeded;
  `NOTE` if all are seeded but the value differs from default;
  `OK` if seeded with the default value.

The per-call array is the audit evidence; the policy block is the
headline finding.

### 3.6 Compliance-check inference (positive findings)

Most audit rules in CLAUDE.md describe what *not* to do; a few
describe what *should* be present (logging discipline, alignment
guards before DESeq2, seed coverage, etc.). The inference layer
should pattern-match for *positive evidence* and emit
`compliance_checks[]` entries with `status: pass | fail | n/a`. The
patterns that move the needle today:

- **`logging-dual-capture`**: detect `sink(..., split = TRUE)` plus
  either `globalCallingHandlers(message = …)` or a tee'd `stderr`.
  Pass = both present and ordered correctly; fail = neither; n/a =
  script is a bash launcher or one-shot script.
- **`alignment-guard-before-DDS`**: detect a `setdiff` / `match` /
  `stop()` block in the ≤ 30 lines preceding any
  `DESeqDataSetFromMatrix` / `lmFit` call. Pass = present;
  fail = absent and a DDS-style constructor is called.
- **`seed-coverage`**: pass = every stochastic op has a reaching
  `set.seed`; fail otherwise.
- **`genome-build-tag`**: pass = at least one path segment matches
  one of {mm10, mm39, GRCm39, hg38, GRCh38, hg19, GRCh37, t2t,
  chm13}; fail = data is clearly genomic but no tag.
- **`relative-paths-only`**: pass = every CLI default and module
  constant is relative; fail otherwise.
- **`forbidden-variable-names`**: pass = no exact-match binding to
  `{counts, results, mean, median, sum, conditions}`; fail
  otherwise.

`compliance_checks[]` entries carry `evidence_sites:` lists so the
final report can hyperlink to the supporting code. Positives feed
the per-category scores in the final `audit_report.md`.

---

## 4. Inferred-output shape — schema v0.2

Replaces the v0.1 draft. Absorbs the ten deltas from
`03_phase0_target_yaml.md` and fourteen more from
`04_realcase_DESeq2_addendum.md` (S11–S25). Stored under
`.audit/<run>/inferred/<analysis_unit_id>.yaml` per the Q1 default.
A future iteration aligns this to the casetrack manifest schema.

### 4.1 Top-level field map

| Field | Status | Purpose |
|---|---|---|
| `schema_version` | required | "0.2" |
| `analysis_unit` | required | id + whether `single` or `pair` |
| `pair_unit` | optional | launcher↔analysis binding when `kind: pair` |
| `script` | required | path, language, git rev, inference layers used |
| `runtime_context` | required | effective cwd, host, user at inference time |
| `config_interface` | required | optparse / argparse / getopts / module-constant surface |
| `inputs` | may-be-empty | filesystem reads + their schemas |
| `outputs` | may-be-empty | filesystem writes + written schemas + groupings |
| `package_resources` | optional | annotation / curated-set data shipped in packages |
| `env_vars_read` / `env_vars_written` | may-be-empty | process env interaction |
| `dataframes` | may-be-empty | per-frame lineage (empty for bash) |
| `transformations` | may-be-empty | filter / normalise / merge / aggregate ops |
| `models` | may-be-empty | each with `design_subset`, `reference_level`, `contrasts[]` |
| `figures` | may-be-empty | first-class; `derived_from` a contrast or dataframe id |
| `stochastic_ops` | may-be-empty | per-call sites, with seed scope evidence |
| `seed_policy` | required | top-level summary across all stochastic ops |
| `functions_defined` | optional | in-script helpers + their propagated I/O |
| `hardcoded_data` | optional | embedded sample / gene / contig / threshold blocks |
| `external_binaries` | optional | spawned binaries performing the actual I/O |
| `driver_pattern` | optional | script-emits-script across languages |
| `validation` | optional | inline pre-flight checks (`stop()`, `[[ -f $X ]]`) |
| `side_effects` | may-be-empty | mkdir, options(), env writes, locks |
| `environment` | required | language version, packages, container |
| `organism_inferred` | optional | mouse / human / etc. — from packages / symbol case |
| `genome_build_declared` | optional | "mm10" / "hg38" / etc. when extractable |
| `compliance_checks` | required | positive AND negative findings vs CLAUDE.md rules |
| `audit_findings_preview` | required | static findings; finalised in `audit_report.md` |
| `unresolved` | may-be-empty | anything inference couldn't decide |

`may-be-empty` = field is present as `[]` even when the script has
no instances. `optional` = field is omitted if absent.

### 4.2 Worked example

Modeled after the DESeq2 + GSEA pair from
`04_realcase_DESeq2_addendum.md`. Truncated with `...` where structure
repeats — full coverage would be 800+ lines and add nothing.

```yaml
schema_version: 0.2

analysis_unit:
  id: RNA-seq_DiffExpr/DESeq2_GSEA_run
  kind: pair                              # single | pair

pair_unit:
  launcher:
    path: scripts/run_manually_run_DeSeq2.sh
    language: bash
  analysis:
    path: scripts/manually_run_DeSeq2.R
    language: R
  binding:                                 # launcher var → analysis CLI flag
    - { launcher_var: SOURCE_DIR,       analysis_flag: --source_dir,       site: "launcher:18 → analysis:62" }
    - { launcher_var: METADATA,         analysis_flag: --metadata_File,    site: "launcher:19 → analysis:84" }
    - { launcher_var: QC_METRICS,       analysis_flag: --qc_metrics,       site: "launcher:20 → analysis:81" }
    - { launcher_var: REF_VARIABLE,     analysis_flag: --ref_variable,     site: "launcher:27 → analysis:75" }
    - { launcher_var: DROP_SAMPLES,     analysis_flag: --drop_samples,     site: "launcher:28 → analysis:73" }
    - { launcher_var: MIN_READ_COUNTS,  analysis_flag: --min_read_counts,  site: "launcher:29 → analysis:77" }
    # ... 7 more
  effective_cwd_at_analysis: "${OUTPUT_DIR}"     # launcher cd's at launcher:48

script:
  path: scripts/manually_run_DeSeq2.R
  language: R
  git_rev: <runtime>
  inferred_at: <runtime>
  layers_used: [static]

runtime_context:
  cwd_at_invocation: "${OUTPUT_DIR}"
  resolved_cwd: ${WORKFLOW_DIR}/results
  host: <runtime>
  user: <runtime>

config_interface:
  framework: optparse
  options:
    - { name: --source_dir,           default: "/data1/.../rerun_RNASeq_11032025/", default_kind: absolute, role: input_dir }
    - { name: --workflow_dir,         default: "/data1/.../RNA-seq_DiffExpr/",      default_kind: absolute, role: workflow_root }
    - { name: --metadata_File,        default: "/data1/.../metadata_triplicates_recoded.csv", default_kind: absolute, role: input_path }
    - { name: --qc_metrics,           default: ".../qc.tsv",                        default_kind: absolute, role: input_path }
    - { name: --drop_samples,         default: "R.S.2,R.C.3",                       role: filter_spec }
    - { name: --ref_variable,         default: "DMSO",                              role: model_param }
    - { name: --min_read_counts,      default: 50,    role: filter_threshold }
    - { name: --smallest_group_size,  default: 3,     role: filter_threshold }
    - { name: --blind_transform,      default: true,  role: model_param }
    - { name: --log_dir,              default: "logs", default_kind: relative,      role: log_dir }
    - { name: --png_dpi,              default: 150,   role: figure_param }
    - { name: --rasterise_dpi,        default: 100,   role: figure_param }

inputs:
  - id: counts_main
    path_template: "{opt.source_dir}/CT/counts.tsv"
    kind: tabular
    format: tsv
    read_call: { fn: data.table::fread, site: 175 }
    referenced_columns: [gene.id, "<one column per sample>"]
  - id: annotation
    path_template: "{opt.source_dir}/annot.tsv"
    kind: tabular
    format: tsv
    read_call: { fn: data.table::fread, site: 173 }
    referenced_columns: [gene.id, gene.symbol, description, entrez.gene.id, gene.type, chr, length]
  - id: metadata
    path_template: "{opt.metadata_File}"
    kind: tabular
    format: csv
    read_call: { fn: base::read.csv, site: 370 }
    referenced_columns: [samples, condition, new_samples_name, condition_long]
  # ... qc_metrics, counts_annot

outputs:
  - id: de_results_qstat_cki_vs_dmso
    group: per_contrast_de_results
    kind: tabular
    path_template: "data/manual_DeSeq2/QSTAT_CKi_vs_DMSO_DESeq2_results.tsv"
    format: tsv
    write_call: { fn: data.table::fwrite, site: 3099 }
    write_mode: overwrite
    schema_written:
      columns: [gene.id, baseMean, log2FoldChange, lfcSE, stat, pvalue, padj, lfc_group]
      origin: contrast_results_table
  - id: de_results_cki_vs_dmso        # parallel structure
    group: per_contrast_de_results
    # ...
  - id: gsea_hallmark_qstat_cki
    group: per_contrast_gsea_hallmark
    kind: tabular
    path_template: "data/manual_DeSeq2/QSTAT_CKi_vs_DMSO_GSEA_Hallmark_results.tsv"
    write_call: { fn: data.table::fwrite, site: 3123 }
  - id: target_gene_lists_wide
    group: target_gene_lists
    kind: tabular
    path_template: "data/manual_DeSeq2/target_gene_lists.tsv"
    write_call: { fn: data.table::fwrite, site: 355 }
    schema_written:
      columns: ["<one column per gene category>"]
      origin: hardcoded_data.gene_lists
  # ... 17 more across groups: per_contrast_gsea_c5_GO,
  #     per_contrast_gsea_m5_GO, per_contrast_normalized_counts,
  #     cross_contrast_summary, target_gene_vst

package_resources:
  - { package: org.Mm.eg.db,    role: gene_annotation,     species: mouse,  version: <runtime> }
  - { package: msigdbr,         role: gene_set_collection, collections_used: [H, C5/GO, M5/GO], version: <runtime> }
  - { package: DESeq2,          role: stats_engine,        version: <runtime> }
  - { package: clusterProfiler, role: gsea_engine,         version: <runtime> }

env_vars_read: []
env_vars_written: []

dataframes:
  - { id: cts,           origin: 175, derived_from: ["{opt.source_dir}/CT/counts.tsv"] }
  - { id: annot,         origin: 173, derived_from: ["{opt.source_dir}/annot.tsv"] }
  - { id: cts_coding,    origin: 192, derived_from: [cts, annot],
      transform: { op: filter, predicate: "gene.type == 'protein_coding'" } }
  - { id: metadata_df,   origin: 370, derived_from: ["{opt.metadata_File}"] }
  - { id: metadata_df_dropped, origin: 395, derived_from: [metadata_df],
      transform: { op: filter, predicate: "!samples %in% drop_samples" } }
  - { id: qstat_cki_vs_dmso_metadata, origin: 502, derived_from: [metadata_df_dropped],
      transform: { op: row_subset, predicate: "condition %in% c('DMSO','QSTAT-CKi')" } }
  - { id: qstat_cki_vs_dmso_df, origin: 511, derived_from: [cts_coding],
      transform: { op: col_subset, columns: [dmso_samples, qstatCKI_samples] } }
  # ... parallel for the other two contrasts

transformations:
  - { site: 192,  op: filter,  target: cts_coding, predicate: "gene.type == 'protein_coding'" }
  - { site: 395,  op: filter,  target: metadata_df, predicate: "!samples %in% drop_samples" }
  - { site: 506,  op: relevel, target: qstat_vs_dmso_metadata.condition, levels: [DMSO, QSTAT] }
  - { site: 536,  op: filter,  target: qstat_cki_vs_dmso_dds,
      predicate: "rowSums(counts(dds) >= MIN_ReadsCounts) >= smallestGroupSize" }
  # ... two more pre-DESeq filters at 1331, 1380 (per-model)

models:
  - id: qstat_cki_vs_dmso_dds
    site: 516
    fn: DESeq2::DESeq
    formula: "~ condition"
    formula_resolution: literal
    reference_level: DMSO
    design_subset:
      rows: qstat_cki_vs_dmso_metadata          # dataframe id
      cols: [dmso_samples, qstatCKI_samples]
    pre_filter: { site: 536, predicate: "rowSums(counts) >= 50, in >= 3 samples" }
    contrasts:
      - { id: qstat_cki_vs_dmso_res, site: 540, coef_or_contrast: "default (last vs first level)" }
  - id: cki_vs_dmso_dds
    site: 520
    fn: DESeq2::DESeq
    formula: "~ condition"
    reference_level: DMSO
    design_subset: { rows: cki_vs_dmso_metadata, cols: [dmso_samples, CKI_samples] }
    pre_filter: { site: 1331 }
    contrasts: [{ id: cki_vs_dmso_res, site: 1334 }]
  - id: qstat_vs_dmso_dds                         # parallel
    site: 524
    # ...
  filter_symmetry: pairwise_identical_thresholds  # auditor-derived

figures:
  - id: volcano_qstat_cki_vs_dmso
    site: 1234
    depicts: volcano_plot
    derived_from: qstat_cki_vs_dmso_res
    written_by: save_figure_3fmt
    paths: ["figures/manual_DeSeq2/{pdf,png,svg}/volcano/..."]
  - id: gsea_dotplot_hallmark_qstat_cki
    site: 1320
    depicts: gsea_dotplot
    derived_from: gsea_h
  # ...

stochastic_ops:
  - { site: 1298, fn: clusterProfiler::GSEA, seed_set: true, seed_value: 1 }
  - { site: 1357, fn: clusterProfiler::GSEA, seed_set: true, seed_value: 1 }
  - { site: 1406, fn: clusterProfiler::GSEA, seed_set: true, seed_value: 1 }
  # ... 9 more across L2178–L2669

seed_policy:
  declared_value: 1
  coverage: { stochastic_ops: 12, seeded: 12, unseeded: 0 }
  divergence_from_claude_default: true             # CLAUDE.md default = 42
  severity: NOTE
  note: "consistent seed=1 across 12 GSEA/permutation calls; defensible but non-default; document in script header"

functions_defined:
  - { id: save_figure_3fmt,           site: "563-602", signature: "(plot_obj, filename_base, output_dir, width, height, units, dpi, rasterise, device_type)", io_emitted: [pdf, png, svg] }
  - { id: compute_tpm,                site: "617-622", io_emitted: [] }
  - { id: inject_gene_lengths_to_dds, site: "630-642", io_emitted: [] }
  - { id: plot_gene_norm_counts,      site: "660-740+", io_emitted: [] }

hardcoded_data:
  - id: hdac_targets
    site: "218-223"
    kind: curated_geneset
    count: 11
    citations: []
    note: "HDAC class I + II target list"
  - id: CKi27_genes
    site: "278-302"
    kind: curated_geneset_structured
    count: 40
    citations: ["PMID:25422890", "PMID:40439998", "PMID:34288272", "PMID:40020669", "PMID:41109929", "PMID:29731968"]
  - id: drop_samples_default
    site: 73                                       # optparse default
    kind: sample_id_list
    values: [R.S.2, R.C.3]
    count: 2
  # ... downstream_effectors, cell_cycle_apoptosis, ferroptosis, stemness

external_binaries: []        # analysis is pure R
driver_pattern: null         # bash → R via Rscript is plain invocation, not script-emits-script

validation:
  - { site: "382-391", kind: pre_drop_check,   description: "validate drop_samples present in metadata and counts before dropping" }
  - { site: "411-416", kind: dup_check,        description: "stop() on duplicate new_samples_name" }
  - { site: "439-441", kind: dup_check,        description: "stop() on duplicate samples" }
  - { site: "451-462", kind: alignment_guard,  description: "metadata rownames must match count colnames (setdiff in both directions)" }
  - { site: "468-470", kind: alignment_guard,  description: "final assertion: all(colnames(cts_coding) == rownames(metadata_rown_df))" }

side_effects:
  - { site: 25,        kind: r_option,  detail: "options(width=200)" }
  - { site: "35-47",   kind: r_option,  detail: "theme_set(ggplot2 global theme)" }
  - { site: "107-108", kind: mkdir,     paths: [figures/manual_DeSeq2, data/manual_DeSeq2] }
  - { site: 114,       kind: mkdir,     paths: [logs] }
  - { site: "119-142", kind: sink_open, detail: "stdout to log_file with split=TRUE; message routed via globalCallingHandlers" }

environment:
  r_version: <runtime>
  r_packages: [DESeq2, tidyverse, EnhancedVolcano, pheatmap, data.table, clusterProfiler, org.Mm.eg.db, msigdbr, enrichplot, ggrastr, optparse, ...]
  container: null

organism_inferred: mouse                           # inferred from org.Mm.eg.db + symbol case (Cdkn1a vs CDKN1A)
genome_build_declared: null                        # no mm10/mm39/GRCm39 token anywhere

compliance_checks:
  - { rule: logging-dual-capture,       status: pass, evidence_sites: [119, 126, 135, 144] }
  - { rule: alignment-guard-before-DDS, status: pass, evidence_sites: ["451-470"] }
  - { rule: seed-coverage,              status: pass, evidence_sites: [1298, 1357, 1406, 2178, 2190, 2202, 2419, 2441, 2454, 2643, 2656, 2669] }
  - { rule: genome-build-tag,           status: fail, note: "no genome tag in paths; organism is mouse" }
  - { rule: relative-paths-only,        status: fail, evidence_sites: [63, 66, 82, 85] }
  - { rule: forbidden-variable-names,   status: pass, note: "no exact-match collisions with [counts, results, mean, median, sum, conditions]" }

audit_findings_preview:
  - { severity: WARNING, rule: relative-paths-only,
      sites: [63, 66, 82, 85, "launcher:14,17-20,24"],
      note: "optparse + launcher defaults are absolute; override-able via CLI but defaults won't run on another machine" }
  - { severity: WARNING, rule: genome-build-tag,
      note: "organism inferred=mouse from org.Mm.eg.db; no genome build (mm10/mm39/GRCm39) declared anywhere in pair" }
  - { severity: NOTE, rule: seed-policy-non-default,
      note: "seed=1 used across 12 stochastic ops; CLAUDE.md default is 42; document in script header" }
  - { severity: NOTE, rule: hardcoded-data-block,
      sites: [218, 226, 236, 248, 254, 278],
      note: "6 curated gene lists embedded; consider promoting to YAML config under workflow_dir/configs/ for downstream reuse" }
  - { severity: OK, rule: alignment-guard,
      note: "DESeq2 alignment failure-mode (silent wrong assignment when colnames != rownames) is explicitly defended at L451-470" }
  - { severity: OK, rule: logging-discipline,
      note: "dual stdout+stderr capture via sink() + globalCallingHandlers" }

unresolved:
  - { kind: figure_paths_via_helper, site: 1204,
      note: "save_figure_3fmt writes 3 file extensions per call; full output enumeration requires walking every call site (dozens)" }
```

### 4.3 Notes on field semantics

- **`analysis_unit.kind: pair`** triggers the `pair_unit:` block.
  When `single`, the launcher binding is omitted.
- **`outputs[].group:`** lets the report fold ~20 per-contrast outputs
  into one bullet ("3 contrasts × 5 result types = 15 files"),
  keeping the audit log short.
- **`models[].filter_symmetry:`** is auditor-derived, not present in
  the source — it flags drift across multi-model scripts that should
  be symmetric.
- **`compliance_checks:`** is the only place positive-status findings
  show up alongside negatives; the *severity* axis in
  `audit_findings_preview:` (with `OK` as a valid level) drives the
  scored final report.
- **`seed_policy:`** is the headline; `stochastic_ops:` is the
  evidence array.
- **`organism_inferred:` mismatch with file paths**, or
  `genome_build_declared: null` while data is clearly mouse/human →
  finding.
- **Cardinality of outputs**: the `outputs[]` array enumerates
  *distinct identities*. When a single `save_figure_3fmt()` call
  emits three files (pdf/png/svg), that's one output entry with
  `format: multi` and a `paths:` list — not three entries.

---

## 5. Hard cases worth naming up front

1. **Sourced helpers** — `source("utils.R")`. Solution: walk
   `source()` / `import` graph and inline-analyse helpers; cap depth.
2. **Library-internal I/O** — `tximport()`, `DESeqDataSetFromHTSeq…`,
   `methylKit::methRead()`. Solution: small curated catalogue
   `library_io_semantics.yaml` describing where each function reads
   from based on its arguments.
3. **Dynamic formula construction** — `as.formula(paste("~", paste(c,
   collapse="+")))`. Solution: record terms with confidence=medium and
   require manifest confirmation.
4. **Tidyverse NSE** — `filter(x > y)` doesn't evaluate at parse time.
   Solution: use `rlang::call_args()` / `lobstr::ast()` to extract
   expression trees without evaluation.
5. **Snakemake / Nextflow** — paths come from `{wildcards}` and a
   config. Solution: parse the rule via Snakemake's Python API to
   resolve before per-script inference runs.
6. **R's `<<-`, `assign()`, and `attach()`** — break lexical scoping.
   Solution: flag any of these; refuse to infer cross-scope dataflow
   through them.
7. **Launcher↔analysis binding** (v0.2). Bash that invokes an
   `Rscript`/`python` with literal `--flag $VAR` pairs is a *pair
   unit*. Solution: detect the pair, match launcher var assignments
   against the analysis script's optparse/argparse signature, emit
   `pair_unit.binding[]` with site refs on both sides. Caveat: if the
   launcher constructs flags dynamically (`for x in …; do --flag $x;
   done`), record as `binding_resolution: dynamic` with confidence
   medium.
8. **In-script helper I/O must propagate upward** (v0.2). A function
   defined in the script (`save_figure_3fmt`, `write_results`) that
   performs file I/O contributes to `outputs:` — but the entries
   should be attributed to the *call sites*, not the definition site,
   so the audit traces back to the contrast/dataframe that drove
   each write. Solution: two-pass walk — pass 1 catalogues
   `functions_defined[]` with their declared I/O; pass 2 expands
   each call into output entries with call-site attribution.
9. **Package-shipped data is not a filesystem read** (v0.2).
   `library(org.Mm.eg.db)` loads species annotations from inside the
   installed R package. Inference must recognise a small allowlist of
   data-shipping packages (`org.*.eg.db`, `msigdbr`, `BSgenome.*`,
   `TxDb.*`, GENCODE/Ensembl helpers) and emit
   `package_resources[]` instead of `inputs[]`. Mismatches between
   package species and inferred organism → finding.
10. **Effective cwd is a function of the process chain** (v0.2). A
    bash launcher `cd "$OUT"` before invoking R means the R script's
    relative paths resolve under `$OUT`, not under the script's
    directory. Solution: track `runtime_context.cwd_at_invocation`
    through every `cd` / `os.chdir` / `setwd()` along the chain;
    record the *resolved* cwd as a separate field so audit findings
    cite the absolute path the reader will actually look for.
11. **Multiple models per script with model-local subsets** (v0.2).
    DESeq2 scripts commonly fit one DDS per contrast against a
    metadata/count subset. Solution: track `models[].design_subset`
    pointing at the per-model dataframe id; cross-check `models.
    filter_symmetry` to flag drift across what should be parallel
    models.
12. **Curated geneset blocks vs accidental hardcoded data** (v0.2).
    A 40-element list of gene symbols cited with PMIDs is curated
    science; a stray 5-element sample-id list is usually accidental
    embedding. Solution: `hardcoded_data[].kind:` taxonomy
    distinguishes; presence of `citations:` argues for "curated";
    short lists without context default to `accidental_embed`.

---

## 6. Compliance checks the inference layer can do *for free*

Once inference is producing the v0.2 structured output, every
CLAUDE.md rule with a syntactic signature becomes a pass/fail
predicate against the YAML. Grouped by severity:

### BLOCKERs (audit gate)
- `header=FALSE` followed by no `colnames<-` assignment → "never
  strip headers" rule.
- Output path resolves under `data/raw/` → "raw data is immutable".
  Cross-references the existing `block-raw-data-writes.sh` hook.
- Output path not under `data/processed/{genome}/` or
  `results/{date}_{genome}_{description}/` → file-layout rule.
- Hardcoded contig name in code (`"chr1"`, `"chrX"`) → already caught
  by `block-hardcoded-contigs.sh`; inference adds the "flowed into
  model X" trace.

### WARNINGs (review-required)
- Stochastic op with no seed in scope → seed-discipline rule.
- Forbidden variable name (`counts`, `results`, `mean`, `median`,
  `sum`, `conditions`) bound in script → naming rule.
- Filename / config missing genome tag when organism is clearly
  genomic → genome-build-tag rule. Driven by
  `organism_inferred` vs `genome_build_declared`.
- Any optparse / argparse / launcher default with `default_kind:
  absolute` → "relative paths in scripts and configs" rule.
- `seed_value` not equal to CLAUDE.md default (42), even when set →
  NOTE-promoted to WARNING if undocumented.

### POSITIVE compliance checks (v0.2 — feed the scored report)
These emit `compliance_checks[]` with `status: pass`:

- `logging-dual-capture` — `sink(..., split=TRUE)` plus
  `globalCallingHandlers(message=…)` in R; `logging` with FileHandler
  + StreamHandler in Python; `exec > >(tee -a $LOG) 2>&1` in bash.
- `alignment-guard-before-DDS` — `setdiff`/`stop()` block in the ≤30
  lines preceding any `DESeqDataSetFromMatrix` call (or analogous
  `lmFit` / `methylKit::unite` etc.).
- `seed-coverage` — every stochastic op site has a reaching
  `set.seed` / `np.random.seed` / `random.seed`.
- `script-header-metadata` — author + date + one-line purpose comment
  at top of script (CLAUDE.md §2 "Documentation").

These are the cheapest wins. They all run from Layer A alone, no
manifest required. The scored final report uses the pass:fail ratio
across these checks as one of its per-category grades.

---

## 7. Implementation phasing

Revised in round 3 after the language-agnostic decision (Q3 below).
The core data model and the three front-end parsers are now built in
parallel, not stacked.

1. **Phase 0** — pick one example script per language (R, Python,
   bash) from a real project; hand-construct the target inferred-
   output YAML for each. These are the regression fixtures.
2. **Phase 1** — Layer A in parallel for R, Python, bash. All three
   front-ends emit the same language-neutral YAML schema. Bash has a
   thinner surface (path-extraction, no rich column lineage).
3. **Phase 2** — wire the compliance checks from §6; the auditor
   becomes useful for the first time.
4. **Phase 3** — implement the two-tier output (Q4 below): live
   audit log + scored final report.
5. **Phase 4** — Layer B runtime trace (R first, then Python; bash
   trace via `set -x` post-processing or `strace -e openat`).
6. **Phase 5** — Layer C LLM-assist for unresolved cases.
7. **Phase 6** — wire to casetrack manifest schema; the manifest
   becomes the contract, inference becomes the enforcer.

---

## 8. Open questions — decisions and remaining

### Decided in round 3

- **Q3 — Language priority**: **language-agnostic from day 1**. The
  auditor accepts R, Python, *and* bash. The core data model
  (inferred YAML) is language-neutral; each language gets its own
  front-end parser emitting the same shape. Bash gets a thinner
  front-end (path-extraction only — `samtools view in.bam > out.sam`
  is easy; rich column lineage isn't a meaningful concept in bash).
  Phasing in §7 revised accordingly.

- **Q4 — Output format**: **two-tier**.
  - **Live audit log** during the run: verbose, timestamped, every
    finding as it's discovered. Streams to stderr and to
    `.audit/<run>/audit.log`.
  - **Scored final report** at end of run:
    `.audit/<run>/audit_report.md` with category scores (I/O,
    columns, transforms, models, reproducibility — each scored A–F
    or 0–100), findings grouped by severity (BLOCKER / WARNING /
    NOTE), and a single headline score. Machine-readable companion
    `.audit/<run>/audit_findings.tsv` for CI gating.

### Recommended in round 3 (pending user override)

- **Q1 — Where inferred output lives**: `.audit/` (gitignored) for
  *drafts*; promote to a committed manifest (in or near the script)
  only after human review. Two-stage prevents draft churn from
  polluting git while keeping promoted contracts versioned.

- **Q2 — Runtime-trace dataset**: **head-of-real by default** (first
  N rows of the real input). Per-script `audit_fixture:` override in
  the manifest for scripts that need balanced or stratified test
  data (DE analysis, paired tests, multi-group comparisons).
  Synthetic is a last-resort fallback when no real data is
  available.

- **Q5 — Cross-script inference**: **defer to the workflow-DAG
  audit** (round-2 candidate in `01_first_principles_brainstorm.md`
  §12.5). Per-script inference is already a large surface; cross-
  script handoff validation is a natural fit for the
  Snakemake/Nextflow-aware DAG layer, which already knows the rule
  dependencies.

---

## 9. What we are NOT designing here

- The manifest format itself — that waits for the casetrack pass.
- The audit-finding catalogue — separate doc once inference output is
  stable.
- The slash-command / hook / workflow-rule wiring (round-1 §12.2) —
  same.

Round 3 input wanted on the questions in §8.
