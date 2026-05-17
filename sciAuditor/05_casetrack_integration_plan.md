# sciAuditor — Casetrack Integration Plan (ROADMAP #1)

> Plan for the manifest-integration round originally listed as ROADMAP
> item 1. Drafted after reading casetrack v0.6 docs at
> `/data1/greenbab/users/ahunos/apps/casetrack/`. This doc supersedes
> the one-paragraph sketch in `ROADMAP.md` §1.

## 0. Reframing

ROADMAP #1 was written when casetrack was v0.2 — a flat-TSV "manifest".
Casetrack today is **v0.6** (SQLite-backed):

- `casetrack.toml` — declared cohort schema (columns per level, types)
- `casetrack.db` — SQLite runtime state (one row per `assay × analysis`)
- `provenance.jsonl` — append-only audit log of every `casetrack append`
- **Per-analysis contract**: every script ends with
  `casetrack append --analysis NAME --results summary.tsv`, where
  `summary.tsv`'s first column is the level key (`assay_id` /
  `specimen_id` / `patient_id`)

There is no single "manifest" to diff against. "Manifest integration"
splits into **three separate contracts** the auditor can check, of which
two are casetrack-specific.

## 1. The three contracts

### C1. Script ↔ `casetrack append` call contract (casetrack-specific)
For any script in a casetrack-tracked workflow:
- Does the script call `casetrack append` at all? (gap if no, *and* it
  writes a results.tsv)
- Does `--results <path>` appear in the script's inferred `outputs[]`?
  (orphan TSV if no — the TSV isn't actually produced by this script)
- Does `--analysis <name>` match the script basename or a declared
  analysis tag? (rename drift)
- Does the summary TSV's first column == the level key the analysis
  registers at? (FK break before `append` is even called)

### C2. Summary-TSV ↔ `casetrack.toml` schema contract (casetrack-specific)
- Parse `casetrack.toml` → extract declared columns per analysis per
  level
- Inspect the script's summary-TSV write call (already in `outputs[]` +
  `dataframes[]`) → extract written column names + dtypes
- Diff: declared-but-not-written, written-but-not-declared, dtype
  mismatch

### C3. Per-script "declared vs inferred" contract (NOT casetrack)
The optional per-script manifest the brainstorm asked about
(`01_first_principles_brainstorm.md` §1 open question: "should we
require a `manifest.yaml` per script?"). Declares the script's expected
`inputs[]` / `outputs[]` / `dataframes[]` / `models[]` so the auditor
can diff inferred against declared. Independent of casetrack; useful
for any analysis script.

## 2. Phasing (one round each)

| Round | Ships | Why this order |
|---|---|---|
| **1** | C2 — `casetrack.toml` schema diff (+ provenance.jsonl source) | Highest leverage. The contract artifact (`casetrack.toml`) already exists in every casetrack project; no new file format imposed. Catches the most common drift (someone added a column to the summary TSV but forgot `casetrack schema apply`). |
| **2** | C1 — `casetrack append` call contract | Builds on C2 (need the indexed analyses from round 1). Adds the audit for "is this script actually wired into casetrack". |
| **3** | C3 — per-script declared/inferred diff | Defers the "force a new artifact on the user?" question. By round 3, real C1/C2 usage will tell us whether per-script manifests are still worth it. |

## 3. CLI surface (round 1)

```
sciauditor_aggregate.py \
    --project-dir <scripts/> \
    --casetrack-project <cohort_v3/> \   # NEW (always explicit, no walk-up magic)
    --output-dir <out/> --jobs 8 --fail-on BLOCKER
```

The aggregator opens `<cohort_v3>/casetrack.toml` once, dispatches rules
by `schema_v` (see §4 Q3), indexes declared schemas by analysis name,
then for each audited script:

1. Detect `casetrack append --analysis X --results Y` calls (Layer A
   static — bash + Python + R parsers, via a new `casetrack_appends[]`
   field in the inferred YAML).
2. Look up `X` in the indexed schema.
3. Diff `Y`'s inferred write-schema (from `dataframes[]`) against
   declared columns from `[analyses.X]` + `[levels.<level>.columns]`.
4. Stream `<cohort_v3>/provenance.jsonl` to compute results-checksum
   drift (§4 Q4 / Q6).
5. Append findings to each script's `audit_findings.tsv` *before*
   the aggregator runs `severity_counts()`, so the per-script row and
   the cohort totals both reflect casetrack rules.

Per-script audit still works without `--casetrack-project`; casetrack
rules just don't fire.

## 3.5 Architecture: one shared check module, not per-parser

`sciAuditor/aggregator/casetrack_check.py` (new) — single file. It:

- Loads `casetrack.toml` once (`tomllib`, Python ≥3.11 stdlib).
- Indexes declared analyses by name → `{level, column_prefix,
  summary_tsv, declared_cols: {col: type}}`.
- Streams `provenance.jsonl` once, builds a dict
  `{(analysis, results_file): latest_append_record}` keyed on the
  most recent append per analysis-output pair.
- Exports `check_script(inferred_yaml: dict, index: CasetrackIndex)
  -> list[Finding]`.

The aggregator imports this module, calls `load_index()` once before
the parse phase, then calls `check_script()` per script after the
parser finishes but before `severity_counts()`.

**Why shared, not per-parser**: three parsers (R / Py / bash) would
each need their own TOML loader, schema_v dispatch, and provenance
streamer — three implementations of the same logic, three places to
fix a bug, three places to add a new schema_v rule. The inferred YAML
is already unified across languages (`02_inference_design.md` §4),
so post-hoc checking against the YAML works language-agnostically.

**What parsers still add**: a single new YAML field
`casetrack_appends: [{analysis: STR, results: STR, project_dir: STR}]`
populated by a ~30-line extractor (regex for bash, AST visit for
Python, call walker for R). The parsers don't apply casetrack rules
themselves — they just surface the data the shared module needs.

Findings the shared module returns are appended to each per-script
`audit_findings.tsv` as 4-col rows like every other rule, so they
flow through the existing severity_counts → headline → cohort_report
pipeline unchanged.

## 4. Decisions

### Q1 — `--casetrack-project` discovery: **explicit**
No magic walk-up search. The flag is required for casetrack rules to
fire. Reasoning: silent project discovery makes failure modes
("wrong cohort matched") hard to debug; explicit is cheaper to read.

### Q2 — Severity placement: **split by failure mode at runtime**

| Rule | Severity | Why |
|---|---|---|
| `casetrack-fk-mismatch` (summary TSV col 1 ≠ level key) | BLOCKER | `casetrack append` refuses at runtime — catching this before a long SLURM job is the auditor's job. |
| `casetrack-schema-drift` (type mismatch on a *declared* column) | BLOCKER | SQLite rejects the INSERT. |
| `casetrack-schema-drift` (extra / missing columns, types compatible) | WARNING | `append` succeeds — casetrack does `ALTER TABLE ADD COLUMN` for extras, NULL-fills for missing. Drift worth flagging but doesn't break. |
| `casetrack-untracked-output` (script writes results.tsv, never calls `append`) | WARNING | Some scripts legitimately don't register (exploratory analyses, side outputs). |
| `casetrack-stale-registration` (script AST changed since last `append`) | WARNING | The next register may produce different semantics from what's currently in the DB. See Q4. |

**Don't soften BLOCKERs for legacy scripts.** The aggregator already
ships `--ignore` globs — that's the right escape hatch for "this
subtree predates casetrack". Softening rule severities to accommodate
legacy quietly trains people to ignore the audit, which defeats the
whole layer.

### Q3 — `schema_v` awareness: **yes, from day one**

Read `schema_v` at TOML load, dispatch rules per version, maintain a
`RULE_INTRODUCED_IN` table. Reasoning: v0.6 added per-level ID regex
validation; v0.4 added QC/censoring; v0.7+ will add more. An auditor
that ignores `schema_v` will either apply new rules to old projects
(false-positives) or old rules to new projects (silent misses).
Both failure modes erode trust faster than the dispatch layer costs.

Implementation shape: one `apply_rules(schema_v, …)` dispatch with
`case schema_v >= "0.6": check_id_regex(...)` per version-gated rule.
Same pattern Black / ruff / eslint use for language-version awareness.

### Q4 — `provenance.jsonl` as a source: **yes, in scope for round 1 (Layer A)**

Revising the initial classification. `provenance.jsonl` is a static
file on disk; reading it is pure static analysis, not runtime. So it
belongs in Layer A and ships with round 1, not deferred to Layer B.

What it unlocks (revised after reading real `provenance.jsonl` shape;
see Q6):
- Cross-check declared `--analysis` names in TOML against what's
  *actually* been registered (catches dead analyses, typo-renamed
  analyses).
- `casetrack-results-drift` rule (WARNING): for each `append`, the
  log stores the `results_checksum` (md5 of the summary TSV at
  register time). Recompute on disk, compare. Drift means the script
  has overwritten its summary TSV without re-running `casetrack
  append` — the DB is stale relative to the file on disk.
- Per-analysis last-registered timestamp surfaces in the cohort
  report as a freshness signal.

Cost is small (provenance.jsonl is append-only JSONL, trivially
streamable). Activates a class of finding nothing else catches.

### Q5 — `--analysis` name validation: **no validation, accept any string**

Defer enforcement until we have ~10 real analysis names in production.
Premature standardization risks rejecting names that turn out to be
fine. The auditor still cross-checks `--analysis` names against
`casetrack.toml` for typos via the `casetrack-orphan-analysis` rule
(NOTE), so silent renames don't go unflagged — they just don't BLOCK.
Revisit if the cohort report shows naming chaos.

### Q6 — Drift detection mechanism: **results-checksum, not AST hash**

**Revised after reading real `provenance.jsonl` shape.** The original
plan called for an AST hash of the script at last register, compared
to the script's current AST hash. That mechanism is **not feasible at
Layer A** because `provenance.jsonl` does not record the script path
or the script's git commit — only `results_file`, `results_checksum`,
the slurm_job_id, and (separately) the casetrack-codebase git state.
There is no foreign key from a provenance entry back to the analysis
script that produced it.

What is feasible — and is a stronger signal — is
`casetrack-results-drift`:

- For each `(analysis, results_file)` in the latest append per pair,
  compute `md5(results_file)` on disk now.
- Compare to `results_checksum` stored in the append record.
- Differ → the summary TSV has been overwritten since last register,
  but the DB hasn't been updated. WARNING.

Why this is better than AST hashing:
- Ground-truths against the *actual output* the script produced, not
  a proxy (source-code AST may change without changing outputs, and
  outputs may change without source-code changes — env vars, library
  updates, input data drift).
- Doesn't require coupling sciAuditor's checks to the analysis
  script's git history.
- Zero plumbing change required in casetrack — `results_checksum` is
  already logged for every `append`.

**Trade-off acknowledged**: this rule fires only after `casetrack
append` has been run at least once. A script that has never been
registered against casetrack will be silent on this rule (which is
correct — it's `casetrack-untracked-output` in round 2's C1 that
catches "never registered at all").

Promoting AST-based stale-registration to Layer B (where actual
execution can produce a fresh checksum to compare) is the right home
if we still want it later. Filed in §6 out-of-scope.

### Q7 — Multi-cohort: `--casetrack-project` is **single-valued; error on second**

Defer multi-cohort support until a real script registers against >1
cohort. Simpler CLI, simpler rule dispatch, simpler cohort report.
Real multi-cohort scripts are rare in this lab; absent evidence,
build for the common case. Revisit if/when a single script genuinely
spans cohorts.

## 5. New rule IDs (round 1 inventory)

| Rule ID | Severity | Source | Layer |
|---|---|---|---|
| `casetrack-schema-drift` | BLOCKER (dtype) / WARNING (missing/extra col) | C2 | A |
| `casetrack-untracked-output` | WARNING | C1 (defer to round 2) | A |
| `casetrack-fk-mismatch` | BLOCKER | C1 (defer to round 2) | A |
| `casetrack-results-drift` | WARNING | provenance.jsonl `results_checksum` vs disk | A |
| `casetrack-orphan-analysis` | NOTE | TOML × provenance cross-check | A |

Round 1 ships `casetrack-schema-drift`, `casetrack-results-drift`,
`casetrack-orphan-analysis`. Round 2 ships the C1 rules. Round 3
ships C3 declared/inferred rules (IDs TBD).

## 6. Out of scope

- Layer B (runtime trace) — cross-project ROADMAP #2.
- AST-based `casetrack-stale-registration` — re-home to Layer B if
  still wanted; provenance doesn't store the linkage needed to do it
  at Layer A.
- Casetrack v0.2 flat-TSV mode — deprecated, removed in v1.0.
- Snakemake/Nextflow DAG audit — ROADMAP #3, separate effort.
- Cohort-level coverage audit ("this analysis covers 15 of 20 assays")
  — casetrack's own `status` / `query` does this; not the auditor's job.
- Upstream change to casetrack to log script path on `append` — would
  enable AST-based stale-registration at Layer A, but is an upstream
  feature request, not a sciAuditor task.
