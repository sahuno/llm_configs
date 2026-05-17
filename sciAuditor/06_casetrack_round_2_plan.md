# sciAuditor — Casetrack Integration Round 2 Plan (ROADMAP #1)

> Round 2 of the work begun in
> [`05_casetrack_integration_plan.md`](05_casetrack_integration_plan.md).
> Round 1 shipped 2026-05-17 at commit `162bc3f`. This doc plans the
> next round: activating the two inert rules, closing parser gaps,
> adding the C1 contract, regenerating per-script reports, and
> correcting one design decision from round 1.

## 0. What round 1 left undone

Logged at the end of `05_casetrack_integration_plan.md` §5 and in
`STATUS.md`. Four open items, ordered by leverage:

| # | Open item | Why it matters |
|---|---|---|
| 1 | Activate `casetrack-fk-mismatch` (BLOCKER) and `casetrack-prefix-collision` (WARNING) | Two real rules are shipped-but-inert because `resolve_results_cols()` always returns None. The data is already in `dataframes[]` + `outputs[]`; just no explicit link. |
| 2 | R parser `casetrack_appends[]` extractor | Coverage gap — R scripts that register via `system2("casetrack", ...)` are silent on every casetrack rule. |
| 3 | C1 contract: `casetrack-untracked-output` rule | New rule. Detects "script writes a summary-TSV-shaped output but never calls `casetrack append`". Catches the most common drift: pipeline added, registration forgotten. |
| 4 | Per-script `audit_report.md` regeneration after casetrack findings append | Today the per-script headline + rule table is stale w.r.t. appended casetrack findings; only the per-script TSV and the cohort report reflect them. |

Plus one correction to surface before round 2 starts, see §1.

## 1. Correction to round 1: `schema_v` is NOT a casetrack tool-version

Q3 of the round-1 plan ("make rules `schema_v`-aware") was based on
a misreading of casetrack's docs. From `CASETRACK_SYNOPSIS.md`:

> "`schema_v` lives in the TOML and bumps on every `schema apply` —
> this doubles as a cheap version stamp in provenance entries."

`schema_v` is a **per-project revision counter** that bumps every time
`casetrack schema apply` runs on that specific project. It tracks
how many times THIS PROJECT's schema has been altered. Two projects
on the same casetrack version can have wildly different `schema_v`s.

**What this means for sciAuditor:**

- The `schema_v` field on `CasetrackIndex` is still useful for
  *reporting* ("audited against project at schema_v=3"), but the
  field should NOT be used to dispatch validation rules.
- The real signal for "what casetrack features exist in this project"
  is **TOML section presence**:
  - `[qc]` → v0.4+ (QC/censoring subsystem)
  - `[layout]` and `[layout.path_templates]` → v0.5+ (tool-first results)
  - `[project].project_id` → v0.6+ (project identity layer)
  - `[levels.<level>].id_pattern` → v0.6+ (per-level ID regex)
- Round 2 should rename the dispatch concept from "schema_v-aware" to
  "feature-aware", with a `feature_supported(index, feature: str) -> bool`
  helper that introspects sections. Future rules that only make sense
  against, e.g., v0.6+ id-pattern validation, will gate on
  `feature_supported(index, "id_pattern")`.

This correction does not affect any currently-shipped rule (none of
them gate on `schema_v`), so no behavior change in round 1. Just a
clearer design going forward.

## 2. Round 2 work items

### Item 1 — Activate `casetrack-fk-mismatch` + `casetrack-prefix-collision`

**Motivation.** Both rules are shipped and exercised by tests, but
their precondition — `resolve_results_cols()` returning a non-None
column list — never fires because the inferred YAML doesn't link an
output file back to the dataframe that wrote it. Activating these
rules is the highest-leverage round-2 work: zero new severity tiers,
zero new rules, just unlocking the two we already paid for.

**Mechanism — add a `written_by` field to outputs.** The Python
parser already collects `dataframes[]` and `outputs[]` with `site`
line numbers. The clean fix is a small post-pass that matches each
`outputs[].write_call.site` to the nearest preceding `dataframes[].site`
(within ~10 lines or via `dataframes[].id` substring match against
`outputs[].write_call.fn`), and writes the resolved dataframe id into
`outputs[].written_by`.

Same logic for bash launchers (post-pass over `invocation` + any
detected `echo > FILE` lines). Bash doesn't have a real dataframe
concept, so `written_by` on a bash output is `null` unless the
launcher composed an explicit dataframe via inline awk/sql/python
heredoc; defer that to round 3.

R parser: same post-pass over the existing call walker that already
collects `outputs[]` and `dataframes[]`.

Then `resolve_results_cols()` in `casetrack_check.py` becomes:

```python
def resolve_results_cols(append_info, inferred_yaml):
    # find output whose path_template basename == basename of --results
    # follow output.written_by → dataframe id
    # return dataframe's column list (from dataframes[i].columns)
```

**Severity unchanged**: `casetrack-fk-mismatch` stays BLOCKER (runtime
INSERT will fail), `casetrack-prefix-collision` stays WARNING (drift
worth flagging).

**Cost**: ~30 lines per parser for the post-pass, ~15 lines in
`casetrack_check.py` for the resolver. Affects: `parser_py`,
`parser_bash`, `parser_r`, `casetrack_check.py`.

**Open decision**:
- **Should `dataframes[]` always include the column list?** Python
  parser today populates `columns` only when it can statically resolve
  the `pd.DataFrame({...})` literal or the read function's `usecols`.
  For dynamically-built dataframes (most real cases), `columns` is
  null. **Recommendation**: keep `columns` null when unknown; emit
  `casetrack-fk-mismatch` as NOTE-severity ("couldn't verify FK")
  instead of BLOCKER in that case, so the rule isn't silent on
  un-resolvable inputs but also doesn't false-positive.

### Item 2 — R parser `casetrack_appends[]` extractor

**Motivation.** R analyses that call `system2("casetrack", ...)` or
`system("casetrack append ...")` are currently silent on every
casetrack rule. Lab uses both R (RNA-seq, methylation downstream,
elastic-net work) and Python; closing this gap is needed before
casetrack rules can be trusted on cohort runs that mix languages.

**Mechanism.** Same regex shape as the Python/bash extractors,
implemented in R inside `parser_r/sciauditor_r.R`. R has the
`stringr` package available in r-env (already a dependency).
Pattern:

```r
ct_re <- regex(
  "\\bcasetrack\\b[\\s'\\\",)\\]]{1,40}\\bappend\\b([\\s\\S]{0,500}?)(\\n\\n|\\Z|;;)",
  ignore_case = TRUE)
matches <- str_match_all(source_text, ct_re)
# then per-match: str_extract for --analysis, --results, --project-dir
```

Return a list-of-lists in the same shape as the Python/bash
extractors so `casetrack_check.py` consumes it identically.

**Cost**: ~20 lines of R. Affects: `parser_r/sciauditor_r.R`.

**Open decision**:
- **Should we extract from both `system()` AND `system2()` calls,
  or just scan the raw source as the Python/bash extractors do?**
  **Recommendation**: scan raw source for symmetry. The regex catches
  literal `"casetrack"` in any context — `system2`, `system`,
  `processx::run`, even a string passed to `glue()`. Less code, same
  coverage as parser-Py.

### Item 3 — `casetrack-untracked-output` (C1 rule)

**Motivation.** The opposite asymmetry to the round-1 rules. Today
sciAuditor catches "script tries to register with the wrong analysis
name", but cannot catch "script forgot to register at all". This is
the single most common drift in the 3-phase casetrack pattern: a new
pipeline ships, the bash wrapper runs the tool + writes a summary
TSV, but the `casetrack append` step gets commented out for a
test run and never restored.

**Mechanism.** For each script with `casetrack-project` set:
1. Look at the script's `outputs[]` — any whose `path_template`
   basename matches a declared `[analyses.X].summary_tsv` from the
   TOML index?
2. Look at the script's `casetrack_appends[]` — does it call
   `casetrack append --analysis X` for that match?
3. If (1) yes and (2) no → emit `casetrack-untracked-output`
   (WARNING).

**Severity rationale**: WARNING not BLOCKER because some scripts
legitimately write a summary TSV without registering (preliminary
runs, exploratory analyses). User can `--ignore` per-script.

**Cost**: ~20 lines in `casetrack_check.py`. No parser changes.
Affects: `casetrack_check.py`.

**Open decision**:
- **What about scripts whose output basename *looks* like a summary
  TSV but doesn't match any declared analysis?** E.g. a script
  writes `modkit_summary_v2.tsv` (close but not exact). **Recommendation**:
  scope round 2 to exact basename matches only. Fuzzy matching is
  round-3 polish if false-negative rate is high in practice.

### Item 4 — Per-script `audit_report.md` regeneration

**Motivation.** Today, when casetrack findings are appended to a
per-script `audit_findings.tsv`, the per-script `audit_report.md`
headline (`Score | Grade`) and rolled-up rule table are stale —
they were written by the parser before the aggregator post-processed.
User reading the per-script report sees a clean grade that doesn't
reflect a casetrack BLOCKER. Cohort report is correct; per-script is
inconsistent.

**Mechanism.** Three options:

| Option | Approach | Tradeoff |
|---|---|---|
| A (recommended) | Regenerate the per-script `audit_report.md` from scratch after appending findings. Aggregator owns a `regenerate_report(yaml_path, findings_tsv_path) -> str` function that calls the same scoring logic the parsers use. | Cleanest. One source of truth for the report template. Cost: refactor each parser's `emit_report()` into a shared helper. |
| B | Write a sidecar `audit_report.casetrack.md` per script; cohort report links both. | Cheap (no refactor) but creates two reports per script — UX confusion. |
| C | Don't regenerate; rely on `audit_findings.tsv` as the per-script source of truth, and document that the .md is a snapshot. | Cheapest. Adds a footnote to STATUS.md. Doesn't actually fix the inconsistency. |

**Recommendation: Option A**, but only if §2 Item 1's resolver work
turns up usable column lists. Otherwise the regenerated headline
won't differ much from the parser-emitted one (only `casetrack-*`
findings shift the score, which is a few per cohort). If A is
expensive to refactor, fall back to C and document.

**Cost (Option A)**: ~80–150 lines (extract each parser's report
generator into `aggregator/report_template.py`; call from both
parsers and aggregator). Affects: `parser_py`, `parser_bash`,
`parser_r`, `aggregator/`.

**Open decision**: A vs C. Resolve at the start of round 2 based on
how much each parser's `emit_report()` diverges. If they're already
near-identical, the refactor is cheap; if each has substantial
language-specific logic, defer to C.

## 3. Decisions to make before round 2 starts

Listed inline above per work item. Summary:

1. **Item 1**: `casetrack-fk-mismatch` severity when cols can't be
   resolved → recommend NOTE (vs silent skip).
2. **Item 2**: R extraction strategy → recommend raw-source regex
   (symmetric with Py/bash).
3. **Item 3**: Fuzzy basename matching → recommend exact match only
   for round 2.
4. **Item 4**: Report regeneration → A vs C; decide after looking at
   `emit_report()` divergence across parsers.

Plus the §1 correction (rename `schema_v` dispatch concept to
`feature_supported`) — a pure refactor with no decision needed.

## 4. Order of operations

Recommended order within round 2:

1. **§1 correction first** — small, no decision. Cleans up before
   adding new feature-gated rules later.
2. **Item 1 (activate inert rules)** — highest leverage. Two rules
   already on disk; unlocking them is the smallest unit of work
   with the largest user-visible behavior change.
3. **Item 2 (R extractor)** — coverage gap. Independent of Item 1.
4. **Item 3 (C1 untracked-output)** — new rule. Independent of 1, 2.
5. **Item 4 (report regen)** — last, because the decision (A vs C)
   depends on what casetrack findings look like in practice after
   the new rules from 1, 2, 3 land.

Items 1–3 are independent and could ship as one batched commit or
three. Item 4 is a separate commit (or a deferral to round 3).

## 5. Out of scope for round 2

- **`casetrack schema apply` validation** — the auditor could in
  principle warn when a script writes a column not yet in the
  declared schema. Belongs to round 3 once Item 1's column resolver
  is solid.
- **Coverage gap audit** — "this analysis covers 12 of 15 declared
  assays" is casetrack's `status`/`query` job, not sciAuditor's.
- **Bidirectional drift** — comparing `casetrack.db` SQLite state
  against the inferred YAML directly (not just `provenance.jsonl`).
  Round 3 if results-drift turns out to be insufficient.
- **`--casetrack-project` multi-cohort support** — locked as Q7 in
  round-1 plan to single-project. Revisit only if a real script
  registers against >1 cohort.
