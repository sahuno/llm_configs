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
  or `relevel()` calls.

### 3.4 Filter inference

Detect filtering predicates (`filter()`, `subset()`, `df[mask, ]`,
`df.query()`, `df[df.x > k]`) and extract:
- the predicate expression
- the columns it depends on
- if runtime trace available: rows before / rows after

### 3.5 Stochastic-op / seed inference

- Build a set of known stochastic call sites in the script.
- Walk the control-flow graph backwards from each: is there a
  reaching definition of `set.seed` / `np.random.seed` /
  `random.seed`?
- If yes → record the seed value.
- If no → **WARNING** (your CLAUDE.md mandates seeds for all
  stochastic ops; this is a compliance check).

---

## 4. Inferred-output shape (draft)

Generic for now; a future iteration aligns this to casetrack's
manifest schema. Stored at `results/.../audit/inferred/<script>.yaml`.

```yaml
schema_version: 0.1
script:
  path: src/03_de_analysis.R
  language: R
  git_rev: 8f3a2c1
  inferred_at: 2026-05-14T12:34:56Z
  layers_used: [static, runtime_trace]

inputs:
  - path_template: data/processed/{genome}/counts.tsv
    slot_bindings: { genome: hg38 }
    format: tsv
    read_call:
      function: readr::read_tsv
      site: src/03_de_analysis.R:12
      args: { col_types: cols(.default = "d", gene_id = "c") }
    schema_observed:   # populated by runtime trace
      n_rows: 24531
      columns: [gene_id, S01, S02, S03, S04, S05, S06]
      dtypes: [c, d, d, d, d, d, d]
  - path_template: sample_sheet.tsv
    ...

outputs:
  - path_template: results/{date}/{genome}/de_{contrast}.tsv
    slot_bindings: { date: $today, genome: hg38, contrast: tx_vs_ctrl }
    format: tsv
    write_call:
      function: readr::write_tsv
      site: src/03_de_analysis.R:88
    schema_written:
      columns: [gene_id, baseMean, log2FoldChange, lfcSE, pvalue, padj]

dataframes:
  - id: counts
    origin: src/03_de_analysis.R:12
    schema: [gene_id, S01..S06]
    flows_to: [dds]
  - id: meta
    origin: src/03_de_analysis.R:18
    schema: [sample, condition, batch]
    flows_to: [dds]
  - id: dds
    origin: src/03_de_analysis.R:30
    derived_from: [counts, meta]
    transform: DESeqDataSetFromMatrix
  ...

transformations:
  - site: src/03_de_analysis.R:35
    op: filter
    target: dds
    predicate: rowSums(counts(dds)) >= 10
    rows_before: 24531
    rows_after: 18742   # from runtime trace
  - site: src/03_de_analysis.R:41
    op: normalisation
    method: DESeq2_size_factors
    target: dds

models:
  - site: src/03_de_analysis.R:52
    fn: DESeq2::DESeq
    formula: "~ batch + condition"
    formula_resolution: literal
    design_columns: [batch, condition]
    reference_levels: { condition: control, batch: 1 }
    contrasts:
      - name: condition_treated_vs_control
        site: src/03_de_analysis.R:60

stochastic_ops:
  - site: src/03_de_analysis.R:67
    fn: stats::kmeans
    seed_in_scope: false
    severity: WARNING

side_effects:
  - site: src/03_de_analysis.R:5
    kind: global_option
    detail: "options(stringsAsFactors = FALSE)"

environment:
  r_version: 4.3.2
  packages:
    - { name: DESeq2, version: 1.42.0, source: bioc }
    - { name: readr, version: 2.1.5, source: cran }
  container: docker://bioconductor/bioconductor_docker:RELEASE_3_18

unresolved:
  - kind: dynamic_path
    site: src/03_de_analysis.R:75
    expression: paste0("results/extra_", Sys.getenv("RUN_ID"), ".tsv")
    note: depends on RUN_ID env var; resolved value unknown at static time
```

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

---

## 6. Compliance checks the inference layer can do *for free*

Once inference is producing the structured output above, several of
your CLAUDE.md rules become trivial pass/fail predicates:

- `header=FALSE` followed by no `colnames<-` assignment → BLOCKER
  (your "never strip headers" rule).
- Output path not under `data/processed/{genome}/` or
  `results/{date}_{genome}_{description}/` → BLOCKER.
- Any write whose path resolves under `data/raw/` → BLOCKER (also
  caught by your existing hook; cheap double-check).
- Hardcoded contig name (`"chr1"`, `"chrX"`) → BLOCKER (your
  `block-hardcoded-contigs.sh` already does this; inference adds the
  "this contig flowed into model X" context).
- Stochastic op with no seed in scope → WARNING.
- Forbidden variable name (`counts`, `results`, `mean`, `median`,
  `sum`, `conditions`) bound in script → WARNING.
- Filename missing genome tag where pattern requires it → WARNING.

These are the cheapest wins. They run from Layer A alone, no manifest
needed.

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
