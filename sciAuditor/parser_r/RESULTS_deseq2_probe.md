# Probe results: round-1 R parser on the DESeq2 + GSEA pair

Ran `sciauditor_r.R` against
`RNA-seq_DiffExpr/scripts/manually_run_DeSeq2.R` (4,970 lines) — the
script `04_realcase_DESeq2_addendum.md` used as its richness probe.

**Verdict**: the parser survives without crashing and produces 647
lines of v0.2 YAML in a few seconds. Coverage of static-detectable
schema fields is solid; the v0.2 schema blocks that round 1
explicitly defers are the biggest remaining gaps.

## What the parser caught (vs the doc-04 manually-traced ground truth)

| Block | Inferred | Ground truth (doc 04) | Match |
|---|---|---|---|
| `inputs[]` | 5 (annot, counts_annot, cts, qc_metrics, metadata) at lines 173, 174, 175, 176, 370 | 5 | exact |
| `outputs[]` | 29 (fwrite + ggsave + saveRDS) | "20+ TSV" + dozens of figures | exact for tabular; figures captured but not yet grouped |
| `stochastic_ops[]` | 12 GSEA calls at lines 1299, 1358, 1407, 2179, 2191, 2203, 2420, 2442, 2455, 2644, 2657, 2670 | 12 (`set.seed(1)` precedes each `GSEA(...)`) | exact |
| `seed_policy` | `declared_value: 1`, divergent from CLAUDE.md=42, severity NOTE | "seed=1 across 12 GSEA / permutation calls; defensible but non-default" | exact |
| `environment.r_packages` | 26 detected (DESeq2, tidyverse, …, ComplexHeatmap, grid, …) | 21+ | superset (caught a few loaded inside helper functions) |
| `organism_inferred` | mouse (from `org.Mm.eg.db`) | mouse | exact |
| `genome_build_declared` | null | null | exact |
| `side_effects` | 7 (1 options(), 6 mkdir, including sites 575/1568/3507 inside helper functions) | full set | superset |
| `compliance_checks` | 6 rules, 4 pass / 2 fail | n/a (target listed only findings) | extended (positives surface in scored report) |
| `audit_findings_preview` | 7 entries (2 WARNING, 2 NOTE, 3 OK) including auto-emitted genome-build-tag and seed-policy | doc-04 listed 4 WARNING + 2 NOTE + 2 OK | functionally aligned |

## Notable correct calls

- **`logging-dual-capture: pass`** — picked up `sink(split=TRUE)` at L122 + `globalCallingHandlers(message=…)` at L135. Confirmed positive compliance, exactly per doc 04 §S19.
- **`seed-policy NOTE`** — auto-derived from coverage (12/12 seeded) plus literal value (1) ≠ CLAUDE.md default (42). Reports `seed=1 used across 12 stochastic ops; CLAUDE.md default is 42`.
- **`genome-build-tag WARNING`** — fired *because* `organism_inferred=mouse` and `genome_build_declared=null`. This is the cross-field finding doc 04 §S23 predicted.
- **`relative-paths-only WARNING` at lines 62, 65, 81, 84** — every optparse default that resolves to an absolute path. Sites exactly match `04_realcase_DESeq2_addendum.md` table.
- **Path-template resolution through `file.path(source_dir, "CT/counts.tsv")`** — produces `{source_dir}/CT/counts.tsv`. Mixed `opt$x` and bare variables both handled.

## Gaps the probe exposed (ordered by audit value)

1. **No `models[]` extraction** — the three DESeq2 contrasts
   (`qstat_cki_vs_dmso_dds`, `cki_vs_dmso_dds`, `qstat_vs_dmso_dds`)
   at lines 516, 520, 524 are invisible to the auditor. The §3.3
   recipe in `02_inference_design.md` is written; round-1 parser
   doesn't implement it. **Highest-value next addition** — without
   `models[]` the audit can't say what was fit, with what design,
   against which subset.
2. **No `dataframes[]` lineage** — 7+ derived frames (`cts_coding`,
   `metadata_rown_df`, `tumor_rows`, per-contrast `*_metadata` and
   `*_df`) are not tracked. Means `figures[].derived_from` can't be
   resolved either.
3. **No `hardcoded_data[]`** — six curated gene lists with PMID
   citations are invisible. Doc 04 §S17 estimated this as a 6-block
   audit-relevant finding; currently zero blocks are surfaced.
4. **No `functions_defined[]`** — `save_figure_3fmt` is called dozens
   of times to emit the figure outputs. Currently each `ggsave` call
   is captured individually but the *intent* (3-format figure save
   from a single logical write) is lost; outputs are 29 instead of
   ~10 logical figure groups.
5. **No `pair_unit`** — the parser never sees
   `run_manually_run_DeSeq2.sh` because it's R-only. Bash
   front-end + pair-detection is needed for the launcher↔analysis
   binding (doc 04 §S11).
6. **`package_resources[]` not emitted** — `org.Mm.eg.db` informs
   `organism_inferred` but doesn't appear as its own `package_resources`
   entry. The presence-check is wired; the structured entry isn't.
7. **`outputs[].group:` not assigned** — 29 outputs are listed as one
   flat array. Should cluster by suffix into `per_contrast_de_results`,
   `per_contrast_gsea_hallmark`, etc. Heuristic: filename-prefix
   clustering after stripping `{contrast}_` patterns.
8. **`transformations[]` empty** — round-1 declares this deferred.
   Predicate extraction for `filter()` / `merge()` / `factor(levels=)`
   is in the §3 recipes but not yet coded.
9. **`figures[]` empty** — 12+ `ggsave` calls are in `outputs[]` but
   not promoted to the first-class `figures[]` array (doc 04 §S25).
10. **Helper-function I/O propagation** — `save_figure_3fmt`'s three
    ggsave calls fire per *outer* invocation; currently the parser
    sees them only at the definition site (562–602). Two-pass walk
    isn't implemented.

## Smaller polish wins observed

- `side_effects` for L575 / L1568 reports paths like
  `dirname(filepath(ext))` and `dirname(out_file)` — unresolved
  because the variable was assigned inside a helper. Mark
  `resolution_confidence: low` and move on; ground-truthing requires
  runtime trace.
- `coverage: stochastic_ops: 0.0` integer-vs-float YAML rendering
  was fixed by explicit `as.integer()` casts.
- `script-header-metadata` now accepts `# Name:` as well as
  `# Author:` (the DESeq2 script uses `#name:`). Header check still
  WARNs because the script lacks a Date or Purpose line in the first
  10 comments — accurate per CLAUDE.md §"Documentation".

## Recommendation for the next iteration

If we close the top three gaps (`models[]`, `dataframes[]`,
`hardcoded_data[]`), the auditor's coverage of the DESeq2 pair jumps
from "structural skeleton" to "useful". Each is bounded:

- **`models[]`** — pattern-match `DESeqDataSetFromMatrix` /
  `DESeq()` / `results()` calls; for each `DDS <- ...` track the
  `countData=` and `colData=` args (both are dataframe ids); extract
  `design=` formula literally; bind `reference_level` from any
  preceding `factor(x, levels=…)` on the design column. Probably
  ~80 lines.
- **`dataframes[]`** — every `id <- f(…)` where the RHS is a
  data-manipulating call or contains a known dataframe id; record
  `derived_from`. Use the `:=`, `mutate`, `merge`, `filter`, `[`
  vocabulary. Probably ~120 lines.
- **`hardcoded_data[]`** — every `id <- c(...)` or `id <- list(...)`
  with ≥5 character literals. Classify by content: gene symbols
  (mixed case + known suffix patterns), sample ids, contig names,
  threshold numerics. Citations: scan preceding ~5 comment lines for
  `PMID:` / `DOI:` tokens. Probably ~80 lines.

After landing those three, the DESeq2 inferred YAML moves from ~647
lines of mostly-correct skeleton to a defensibly complete static
description of the analysis. That's the natural Phase 1.5
checkpoint before Phase 2 wires the scored report.
