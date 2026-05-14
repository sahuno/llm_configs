# sciAuditor — First Principles Brainstorm (round 1)

> Goal: a Claude Code skill that audits computational-biology analyses so we
> ship faster *and* with confidence. Scope of round 1: **tabular data**
> analyses in genomics / transcriptomics / ONT DNA methylation.
>
> This is a brainstorm, not a spec. Each section ends with **open questions**
> meant to drive the next iteration.

---

## 0. Framing — what is an audit, actually?

An audit answers three questions about an analysis:

1. **Is it what you think it is?** — does the code actually do what the
   narrative / figure caption / paper text claims it does?
2. **Will it survive being re-run?** — by you in 6 months, by a reviewer,
   by a CI runner with a different package version.
3. **Is the conclusion *robust* to defensible alternative choices?** — would
   a different normalisation, filter, or contrast flip the headline finding?

Most "bugs" in computational biology aren't crashes — they're silent
semantic mismatches between *the model the scientist thinks they fit* and
*the model the code actually fit*. The auditor's job is to surface those.

A natural decomposition:

- **Static audit** — read the code + configs without running anything.
  Cheap, deterministic, runs in CI, catches ~70% of common defects.
- **Dynamic audit** — re-execute (or partially execute) the workflow on
  the actual data, compare to a manifest, recompute spot checks.
- **Semantic audit** — does the analysis match the stated scientific
  question? This is the hardest layer and the one where Claude adds the
  most value over a linter.

Each principle below should be tagged with which layer(s) it lives in.

---

## 1. Inputs & outputs (your starting point, expanded)

You asked: *what are all the data inputs and outputs of the script?*

That single question fans out into a checklist:

### Inputs
- **Identity** — path, basename, file format, delimiter, encoding, quote
  char, comment char, compression. Many silent bugs come from
  `read.table` guessing the wrong separator.
- **Versioning** — checksum (md5/sha256), file size, mtime, upstream
  workflow run ID (Snakemake/Nextflow). An input is only reproducible if
  you can *prove* you read the same bytes next time.
- **Provenance** — where did this file come from? Was it produced by a
  rule in this workflow, downloaded from a public bucket, or
  hand-edited? Hand-edited inputs are an audit red flag.
- **Schema contract** — expected columns (names + dtypes + units),
  declared up front, validated at read time. Your CLAUDE.md already
  forbids ad-hoc headers; the auditor should *enforce* that contract.
- **Sample-sheet linkage** — every count/methylation matrix should be
  joinable to `sample_sheet.tsv` via a documented key. The auditor must
  check that the join is 1:1 and total (no orphan samples on either
  side).
- **Genome build / coordinate system** — 0-based vs 1-based, BED vs GFF
  vs VCF; build tag matches the file's directory (you already enforce
  `data/processed/{genome}/`).

### Outputs
- **Path predictability** — outputs live under
  `results/{date}_{genome}_{description}/`; the auditor should verify
  the script writes nowhere else (no `/tmp`, no `~/`, no overwrites of
  inputs).
- **Header presence** — your rule: BED-like outputs start with `#`. The
  auditor must check this for every tabular write, not just BED.
- **Format-units match** — methylation fraction in `[0,1]` vs `[0,100]`,
  counts as integers, log-fold-change as float — the column name and
  the dtype must agree.
- **Side-effects** — does the script also modify state outside its
  declared outputs (env vars, global R options like
  `options(stringsAsFactors=...)`, written caches)? List them.
- **Plot ↔ data parity** — every figure has an accompanying CSV/TSV with
  the underlying numbers. If a panel can't be regenerated from a saved
  table, the audit fails.

### Open questions
- Should the auditor *require* a per-script `manifest.yaml` listing
  declared inputs and outputs, or should it *infer* them by parsing the
  code? Probably both — declared is the contract, inferred is the
  reality, and divergence is the bug.
- How aggressive should checksum tracking be? For raw FASTQ/POD5,
  checksums are gold; for derived counts matrices, mtime + git rev of
  the producing rule may be enough.

---

## 2. Explanatory variables & column semantics (your starting point, expanded)

You asked: *which explanatory variables, which columns, were they
transformed, were headers removed?*

This is really three questions glued together.

### 2a. Column identity is sacred
- Refer to columns by **name**, never by index. Positional access
  (`df[, 3]`, `awk '{print $4}'`) is a top source of silent breakage
  when an upstream rule adds a column.
- Headers must round-trip: input header → in-memory schema → output
  header. The auditor should flag any code path that:
  - reads with `header=FALSE` when the file has a header,
  - writes with `col.names=FALSE` / `header=False`,
  - renames columns without a documented rationale,
  - relies on factor-level ordering instead of explicit `levels=`.
- Joins/merges must specify `by=` explicitly. Implicit joins on
  "whatever columns share a name" are an audit fail.

### 2b. Variable role declaration
For each modelling step, the auditor should be able to extract:
- response variable(s) — what's on the LHS of the formula
- explanatory variable(s) — what's on the RHS, split into:
  - biological variable of interest (`condition`, `treatment`, `timepoint`)
  - biological covariates (`sex`, `age`, `tissue`)
  - technical covariates (`batch`, `flowcell`, `library_prep_date`)
  - nuisance/random effects (`patient_id`, `replicate`)
- reference level for each categorical (which group is the intercept?)
- interaction terms, and *why* they're there

The dangerous failure mode here is **confounded design**: batch
correlated with condition, or treatment correlated with sex. The
auditor should cross-tab every technical covariate against the
biological variable of interest and flag low-rank designs.

### 2c. Transformations — a separate section because it's huge
See §3.

### Open questions
- Should the auditor require a `design.yaml` per modelling script that
  declares role of every column? That would make this layer trivial to
  audit and forces the scientist to think about it once, up front.
- For ONT methylation specifically: is the "condition" the read-level
  modification probability, the site-level fraction, or the
  region-level summary? The auditor needs to know which it is to apply
  the right distributional check.

---

## 3. Transformations — the silent-bug factory

Every transformation is a place where the code's behaviour can diverge
from the scientist's mental model. Audit each one for: **was it applied,
to what, with what parameters, in what order, and is the choice
defensible?**

### 3a. Common tabular transformations to audit
- **Log transforms**: `log2`, `log10`, `log1p`. Pseudo-count value?
  Applied to counts or to normalised values? Reversible?
- **Normalisation** (RNA-seq): TMM, RLE, CPM, TPM, VST, rlog, DESeq2
  size factors. Each makes different assumptions; mixing them across
  steps is a classic bug.
- **Methylation-specific**: M-values vs beta-values, smoothing
  (BSmooth), coverage filtering (min reads per CpG), strand collapse.
- **Scaling/centering**: per-feature z-score vs per-sample. If fed into
  ML, was scaling fit on train only?
- **Imputation**: kNN, mean, zero-fill. Imputing zeros in count data is
  almost always wrong; flag it.
- **Outlier handling**: winsorization, MAD-based removal, Cook's
  distance. Must be logged with which samples/features were dropped.
- **Aggregation**: gene-level from transcript-level (sum vs
  length-weighted), region-level from CpG-level (mean vs
  coverage-weighted mean — *very different*).

### 3b. Order of operations matters
Filtering before vs after normalisation gives different answers.
Batch correction before vs after VST gives different answers. The
auditor should reconstruct the DAG of transformations and flag
common bad orderings:
- normalise → filter low-count (filter should usually come first)
- batch-correct → fit model that already includes batch in design
  (double-correction)
- impute → compute correlations (inflates correlation)
- scale → PCA across all samples then split train/test (leakage)

### 3c. Reversibility & traceability
For every transformation, the auditor should be able to answer: *given
this output row, what raw input row(s) produced it, and what
operations were applied?* If the answer requires re-running the whole
pipeline, traceability is broken — usually fixed by writing
intermediates with consistent keys.

### Open questions
- Should we maintain a curated catalogue of "known dangerous
  transformation pairs" (like the bullet list above) that the auditor
  pattern-matches against?
- For nonparametric / rank-based methods, traceability is murkier —
  what's the right granularity of audit?

---

## 4. Sample / feature filtering

A filter is just a transformation whose output schema is the same as
its input but with fewer rows. Audit-worthy because **filters are
where samples quietly disappear**.

- **Before/after dimensions logged** at every filter step (n samples, n
  features). The auditor should be able to render a Sankey of how the
  cohort shrank.
- **Reason recorded** per dropped sample/feature: low coverage, failed
  QC, ambiguous metadata, etc.
- **Filter criteria parameterised** in config, not hardcoded in
  the script body.
- **Filtered output ≠ raw mutation** — your CLAUDE.md already enforces
  this via the raw-data-write hook. The auditor should also check that
  filtered intermediates are written to `data/processed/`, never back
  to `raw/`.

---

## 5. Statistical model specification

This is where "is it what you think it is?" most often breaks.

- **Distribution match** — counts → NB (DESeq2, edgeR); proportions →
  beta-binomial (methylKit, DSS); continuous → Gaussian. Flag e.g.
  `lm()` on raw counts.
- **Formula audit** — extract the formula, list every term, confirm
  reference levels, list contrasts. Compare what the code tests to
  what the prose claims.
- **Multiple testing** — was correction applied? Across what family of
  tests? BH within contrast vs across all contrasts gives different
  FDRs.
- **Effect-size reported alongside p-value** — auditor should flag any
  results table that has p but no effect.
- **Power / n** — was the design powered for the effect being claimed?
  Even a back-of-envelope flag (n_per_group < 3) is useful.

---

## 6. Reproducibility hygiene

You already have most of this baked in (set.seed, immutable raw,
genome tagging). The auditor's job is to *check compliance*:

- `set.seed(42)` (or user-specified) called **before every stochastic
  op** — sampling, CV split, bootstrap, UMAP/t-SNE init, kmeans.
- Software versions captured: `sessionInfo()` for R, `pip freeze` /
  `uv pip freeze` for Python, container digest for singularity.
- No hardcoded absolute paths (you have a hook for this — auditor
  should still re-verify in case the hook was bypassed).
- Workflow runnable end-to-end from `data/raw/` → final figures with a
  single command. If the only way to reproduce a result is to run
  scripts in the right order by hand, that's an audit fail.

---

## 7. Cross-script / cross-stage consistency

Workflows are modular (your principle 1). The seams between modules
are where consistency drifts:

- **Sample IDs** identical across every file in the workflow (no
  `Sample_01` here, `sample-01` there, `S1` somewhere else).
- **Gene/feature IDs** from one annotation release used throughout
  (Ensembl 110 vs GENCODE 44 is a common mismatch).
- **Genome build** consistent — or, if intentionally multi-build (your
  multi-build section), liftOver applied and both coordinates retained.
- **Units** consistent — TPM in one script, CPM in the next, both
  labelled "expression" — flag it.
- **Sample sheet is the single source of truth** — every script reads
  from it, no script silently overrides it.

---

## 8. ONT-DNA-methylation / transcriptomics specifics

The general principles above apply, but tabular outputs from
ONT/RNA-seq pipelines have domain-specific tripwires:

### ONT methylation (modkit / bedMethyl)
- Coverage threshold for site inclusion (commonly ≥5×; varies)
- Strand handling: per-strand vs combined; CpG dyad collapsing
- Modification type: 5mC vs 5hmC vs 6mA — confused at your peril
- Coordinate system: bedMethyl is 0-based; many downstream R tools
  expect 1-based
- "% modified" column scale: 0–100 vs 0–1
- Filter on `valid_coverage` not raw read depth

### RNA-seq (counts / TPM tables)
- Counts vs estimated counts (Salmon/Kallisto) vs length-scaled TPM —
  feed the right one to the right tool
- Gene-level aggregation method documented (tximport: `lengthScaledTPM`
  vs `dtuScaledTPM` vs `no`)
- Ribosomal / mitochondrial filtering decisions
- Strandedness of the library (fr-firststrand vs unstranded) consistent
  with featureCounts/htseq options used upstream

### Open question
- Should the auditor ship with per-assay "expected schema" YAMLs (e.g.
  bedMethyl columns, DESeq2 results columns) and validate against
  them?

---

## 9. Sanity / smell-test layer

Cheap checks that catch a surprising fraction of bugs:

- PCA before and after normalisation — samples cluster by biology, not
  by batch?
- Library-size distribution — any sample 10× smaller than the rest?
- Housekeeping gene expression — flat across conditions?
- Methylation global distribution — bimodal at 0 and 1 preserved?
- p-value histogram — uniform under the null with a spike near 0? Or
  weird U-shape (suggests miscalibration)?
- "Too good to be true" check — if >50% of features are significant at
  FDR<0.05, the model is probably misspecified.

These are diagnostics the auditor can *generate* even if the original
script didn't, and stash under `results/.../audit/`.

---

## 10. Audit output: what does the skill actually produce?

A first cut:

1. **`audit_report.md`** — human-readable, per-script section, severity
   levels (BLOCKER / WARNING / NOTE).
2. **`audit_findings.tsv`** — machine-readable for CI gating.
3. **`audit_dag.svg`** — DAG of inputs → transforms → outputs, with
   findings overlaid.
4. **`audit_diagnostics/`** — auto-generated PCA, library-size, p-value
   histograms, sample-sheet × covariate cross-tabs.

Severity rubric (draft):
- **BLOCKER** — header dropped, hardcoded contig, leakage, raw data
  overwritten, sample-sheet/data mismatch.
- **WARNING** — positional column access, unseeded stochastic op,
  un-documented filter, confounded design.
- **NOTE** — style/convention drift, missing units, missing
  `sessionInfo()`.

---

## 11. What this skill is *not*

To stay focused (round 1):
- Not a generic code linter — there are tools for that.
- Not a workflow runner — Snakemake/Nextflow already do that.
- Not a statistics tutor — it flags, it doesn't lecture.
- Not assay-agnostic forever — start with tabular RNA-seq + ONT
  methylation; expand later.

---

## 12. Next iteration — questions for you

1. **Manifest vs inference**: do you want to *require* a per-script
   `manifest.yaml` declaring I/O + roles, or have the auditor parse
   the code? My instinct: require it, because the act of writing the
   manifest is itself a forcing function for clear thinking.
2. **Where does the auditor run?** Three options that compose:
   (a) pre-commit hook on changed scripts,
   (b) Snakemake/Nextflow rule that runs after each module,
   (c) on-demand `claude /audit <script.R>` slash command.
3. **Gold-standard fixtures**: should we curate a tiny "known-good"
   and "known-bad" tabular dataset pair (e.g. a 50-sample RNA-seq toy
   + a deliberately-broken twin) as the auditor's test bed?
4. **Severity gating**: should BLOCKER findings actually block a
   workflow run, or just annotate? My instinct: block, with an
   explicit `--audit-override` escape hatch that gets logged.
5. **Scope of round 2**: after tabular, do we go to (a) image/figure
   audit, (b) workflow-DAG audit, or (c) cross-sample integrative
   audit (RNA + methylation)?

---

## 13. Working principles I'm proposing for the skill itself

- **Audit the data, not the developer.** Findings cite line numbers
  and column names, never blame.
- **Every finding is fixable in one PR.** If a finding requires "rewrite
  the analysis", split it.
- **Cheap by default, deep on demand.** Static layer runs in seconds;
  dynamic and semantic layers are opt-in flags.
- **The audit is itself reproducible.** Same script + same data + same
  auditor version → byte-identical report.
- **Findings link to evidence.** Every BLOCKER cites a file:line and,
  where applicable, the exact bytes/rows that triggered it.
