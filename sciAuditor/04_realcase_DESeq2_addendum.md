# sciAuditor — Real-case addendum: DESeq2 + GSEA pair

> Goal: extract schema deltas from a real analysis that's
> substantially richer than the three Phase 0 picks. This addendum
> does **not** re-do the full hand-built YAML (the script is 4,970
> lines — repetitive structure, low marginal information). It
> focuses on the *new* things this pair teaches us about the
> schema, on top of the ten deltas already captured in
> `03_phase0_target_yaml.md`.

## The pair

- Launcher: `RNA-seq_DiffExpr/scripts/run_manually_run_DeSeq2.sh`
  (88 lines)
- Analysis: `RNA-seq_DiffExpr/scripts/manually_run_DeSeq2.R`
  (4,970 lines)

The launcher `cd`s into `OUTPUT_DIR` then invokes the R script with
13 CLI args. Together they form **one analysis run**. The auditor
must treat them as a single unit, not two scripts.

## Why this example is more informative than Phase 0

| Property | Phase 0 picks | DESeq2 pair |
|---|---|---|
| Languages involved | 1 per script | bash launcher → R analysis |
| Models fitted | 0 | 3 (one per contrast) |
| Stochastic ops | 0–1 | 12+ `set.seed(1)` calls before GSEA |
| TSV outputs | 1–2 | 20+ |
| Figure outputs | 0 | dozens, in pdf/png/svg |
| Hardcoded gene/sample lists | 1 small | 6 large, structured by drug |
| In-script helper definitions | 0 | 4+ (save_figure_3fmt, compute_tpm, …) |
| Pre-flight validation code | minimal | extensive (sample alignment, dup check) |
| Logging instrumentation | minimal | full (sink + globalCallingHandlers) |
| Package-shipped data deps | 0 | 2 (org.Mm.eg.db, msigdbr) |

Phase 0 was an alphabet check; this pair is the first real sentence.

## Top 15 new schema-impact insights

Numbered for cross-reference; tied to specific line ranges.

### S11. The audit unit is a *script pair*, not a single file
`run_manually_run_DeSeq2.sh` is a parameter container; the R script
is the analysis. CLI args declared at L62–95 of the R script are
populated from L26–80 of the launcher. The auditor's manifest must
allow `script:` to be either a single file OR a pair (launcher +
analysis). Inferring a pair: look for any bash that invokes an
R/Python script with literal flags matching that script's optparse
/ argparse signature.

### S12. CLI defaults vs launcher-supplied values can diverge
R-script defaults (e.g. `--drop_samples "R.S.2,R.C.3"`) happen to
match the launcher (L28). They might not. The auditor should record
**both** "default if not supplied" and "actual value at this run" —
and flag when they diverge silently (no log line documenting the
override).

### S13. Multiple models per script
The §4 schema treats `models:` as a list, which is right — but the
DESeq2 pair exposes that each model carries its own:
- design dataframe (a *subset* of the master metadata at L502–504)
- design matrix subset (a *subset* of the master count matrix at L510–512)
- factor releveling (L506–508: `factor(..., levels = c("DMSO","QSTAT"))`)
- independent filter (L536: `rowSums(counts(dds)) >= MIN`)
- explicit reference level (first level of the factor)

The schema needs `models[].design_subset.{rows,cols}` pointers and
`models[].reference_level` as a first-class field.

### S14. Filters are model-local
L536, L1331, L1380 each filter their *own* DDS before `DESeq()`.
Different DDS objects, same threshold (`MIN_ReadsCounts=50`,
`smallestGroupSize=3`) — but a future bug could easily change one
without the others. The auditor should detect "near-duplicate filter
predicates across models" and either confirm intentional symmetry or
flag drift.

### S15. Seed compliance — non-default literal
12+ calls to `set.seed(1)` (L1298, L1357, L1406, L2178, L2190, L2202,
L2419, L2441, L2454, L2643, L2656, L2669). CLAUDE.md default is 42.
Seed-of-1 is a defensible scientific choice (reproducibility within
the script) but warrants:
- finding: `seed-policy: non-default value (1 vs 42)` → **NOTE**
- finding: `seed-discipline: every stochastic op is seeded` →
  **OK / positive**

Schema needs `stochastic_ops[]` with `seed_set: bool`,
`seed_value: literal|expr`, and a top-level `seed_policy:` summary.

### S16. Output schema is taxonomical, not flat
20+ TSV outputs cluster naturally:
- per-contrast results: `{CONTRAST}_DESeq2_results.tsv`
- per-contrast normalized counts
- per-contrast GSEA results (Hallmark, C5/GO, M5)
- summary / cross-contrast tables (chisq, NES heatmaps, pairwise)
- target-gene VST matrices (per contrast + combined)

The schema needs `outputs[].group:` so the report can summarize
"the 3 per-contrast DE results files" as one logical artifact, not
three separate audit rows.

### S17. Hardcoded data has structure — needs `kind:` taxonomy
L218–305 define ~120 lines of curated gene lists organized by drug
and biology (`hdac_targets`, `downstream_effectors`,
`cell_cycle_apoptosis`, `ferroptosis`, `stemness`, `CKi27_genes`).
These are NOT bugs — they're scientific design — but they're audit-
relevant because:
- they should ideally live in a config / package, not the script
- they need provenance (PMIDs are listed at L276 — auditor should
  extract these as citations)

Schema: `hardcoded_data[].kind:` ∈ `{sample_id_list,
gene_symbol_list, region_list, threshold_constants,
contig_list, curated_geneset}`. And `hardcoded_data[].citations:`
optional array of PMID / DOI.

### S18. In-script function definitions are first-class
L563 `save_figure_3fmt`, L617 `compute_tpm`, L630
`inject_gene_lengths_to_dds`, L660+ `plot_gene_norm_counts`. These
are defined *and called* in the same file. The auditor needs:
- a `functions_defined:` block: name, signature, line range, calls-out
- when a defined-here function performs I/O (`save_figure_3fmt`
  writes pdf/png/svg), that I/O must propagate into the `outputs:`
  list with attribution to the call site, not the definition site

### S19. Self-instrumented logging is a compliance positive
L116–148 set up a timestamped log file, dual stdout+stderr capture
via `sink()` + `globalCallingHandlers(message=…)`, with an
`on.exit()` guard. This implements §"Logging and Audit Trail" from
CLAUDE.md. The auditor should emit:
- finding: `logging-discipline: dual stdout+stderr capture detected`
  → **OK / positive**
- conversely, scripts without this should get a **WARNING**

Schema: `compliance_checks[]` with `{rule, status: pass|fail|n/a,
evidence_sites:[…]}`.

### S20. Defensive sample-alignment code is a compliance positive
L447–470 perform extensive metadata↔counts alignment with explicit
`stop()` on mismatch. The exact failure mode that bites DESeq2
(silent wrong assignment when colnames don't match rownames) is
defended against. Auditor should detect "DDS construction preceded
by alignment guard" and credit it.

### S21. Package-shipped data is a fourth I/O category
`library(org.Mm.eg.db)` (L13) and `library(msigdbr)` (L19) load
species annotations and curated gene sets from package data, not
filesystem files. The §4 schema currently only knows about
`inputs[].path_template:`. We need:

```yaml
package_resources:
  - package: org.Mm.eg.db
    version: <runtime>
    role: gene_annotation
    species: mouse
  - package: msigdbr
    version: <runtime>
    role: gene_set_collection
    collections_used: [H, C5/GO, M5/GO]
```

### S22. Implicit cwd-as-output-root
The launcher does `cd "${OUTPUT_DIR}"` at L48 *before* invoking R.
The R script then writes relative paths like
`data/manual_DeSeq2/target_gene_lists.tsv` (L355). The *absolute*
output paths depend on launcher cwd at invocation time. The auditor
must track effective cwd through the script chain and resolve
relative writes against it.

Schema: `runtime_context.cwd:` field; resolved by walking from
launcher process state into invoked process.

### S23. Missing genome build tag → WARNING
The data is mouse RNA-seq (uses `org.Mm.eg.db`, mouse symbols like
`Cdkn1a`, `Hdac1`). No filename, directory, or config field carries
the genome tag (mm10 vs mm39 vs GRCm39). CLAUDE.md mandates this.
The auditor should detect:
- mouse identity (from package or gene-symbol case)
- missing genome tag in paths
- emit **WARNING: organism inferred=mouse, genome build undeclared**

Schema: `organism_inferred:` and `genome_build_declared:` top-level.
Mismatch → finding.

### S24. Contrasts are sub-entities of models
DESeq2 model objects support multiple `results()` extractions —
each one is a *contrast*. The pair pulls one contrast per model
(`qstat_cki_vs_dmso_res = results(qstat_cki_vs_dmso_dds)` at L540
etc.) — but more elaborate scripts pull several. Schema:

```yaml
models:
  - id: qstat_cki_vs_dmso_dds
    fn: DESeq2::DESeq
    formula: "~ condition"
    reference_level: DMSO
    design_df: qstat_cki_vs_dmso_metadata
    count_df: qstat_cki_vs_dmso_df
    contrasts:
      - id: qstat_cki_vs_dmso_res
        site: 540
        coef_or_contrast: "default (last vs first level)"
```

### S25. Volcano / GSEA plots are downstream of contrasts — lineage
The volcano plot at L1234 and the GSEA dotplots at L1320, L1371,
L1421 all consume a specific contrast's results table. The figure-
level lineage answers "this volcano shows which contrast on which
DDS on which subset of which raw counts?" — that's the audit chain.

Schema: `figures[].derived_from:` (a contrast id) and
`figures[].depicts:` (e.g. `volcano_plot`, `gsea_dotplot`,
`heatmap_vst`).

## Updated consolidated schema deltas (round 4 input, revised)

Numbering continues from `03_phase0_target_yaml.md` §"Consolidated
schema deltas". The first ten remain. New ones (load-bearing first):

11. **`pair_unit:`** — top-level toggle when the audit subject is a
    launcher + analysis pair. Captures the cross-script binding of
    launcher constants to analysis CLI args.
12. **`runtime_context.cwd:`** — track effective working directory
    across the pair; resolves relative writes.
13. **`models[].design_subset.{rows,cols}:`** — sample / feature
    subsets per model.
14. **`models[].reference_level:`** — explicit; extracted from
    `factor(..., levels=)` calls.
15. **`models[].contrasts:[]`** — first-class sub-array; figures /
    downstream consumers reference contrast IDs.
16. **`outputs[].group:`** — logical grouping for taxonomic
    summarisation in the report.
17. **`hardcoded_data[].kind:`** — taxonomy of embedded data.
18. **`hardcoded_data[].citations:`** — PMID/DOI when present.
19. **`package_resources:`** — fourth I/O category (annotation
    packages, MSigDB-style curated sets, organism dbs).
20. **`functions_defined:`** — in-script helper definitions; their
    I/O propagates to top-level `outputs:` with attribution.
21. **`compliance_checks:`** — surfaces *positive* compliance
    findings (logging discipline, alignment guards, seed coverage)
    alongside negative ones.
22. **`organism_inferred:`** + **`genome_build_declared:`** —
    mismatch is a WARNING.
23. **`figures[]`** as a first-class top-level array with
    `derived_from:` pointing to a contrast or dataframe id.
24. **`seed_policy:`** — top-level summary: declared value, coverage
    over stochastic ops, divergence from CLAUDE.md default (42).

## Implication for step A (revising §4 schema in doc 02)

The doc 02 §4 schema (v0.1) is no longer sufficient. The v0.2
revision needs to absorb:

- the 10 deltas from `03_phase0_target_yaml.md` (config_interface,
  external_binaries, driver_pattern, hardcoded_data,
  audit_findings_preview, validation, append_pattern,
  env_vars_read/written, output kind:, empty-list permissions)
- the 14 deltas above (S11–S24, S25)

Total: **~24 schema fields** to add/revise. That's a substantive
v0.2.

I'd still do step A next — but it's now a bigger lift. Two ways to
break it down:

- **A-minimal**: lock the *additions* only (new top-level blocks
  and new fields). Leave existing v0.1 fields alone.
- **A-full**: full v0.2 rewrite of §4, with examples drawn from the
  DESeq2 pair where the abstraction is hardest to see (S11, S20,
  S21).

My recommendation: **A-full**. The DESeq2 pair is realistic enough
that the v0.2 schema will hold up against ~80% of the lab's tabular
analyses. Settling now beats refactoring later.

## What I did NOT do in this addendum

- Hand-build the full DESeq2 inferred YAML (~500–800 lines of
  repetitive structure — low marginal information vs the deltas
  above).
- Audit the script for findings under v0.2. That happens once the
  parser exists.
- Address the GSEA-result interpretation layer (NES heatmap clustering
  at L1071, antigen-presentation NES table at L2627). Those are
  scientifically interesting but the schema is already adequate
  for them; they're just more contrasts × analysis-stage rows.
