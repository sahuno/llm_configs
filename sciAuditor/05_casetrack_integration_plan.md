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
   static — bash + Python + R parsers).
2. Look up `X` in the indexed schema.
3. Diff `Y`'s inferred write-schema against declared.
4. Stream `<cohort_v3>/provenance.jsonl` (round 1) to pick up
   stale-registration findings (§4 Q4).
5. Emit findings under new rule IDs (see §5).

Per-script audit still works without `--casetrack-project`; casetrack
rules just don't fire.

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

What it unlocks:
- Cross-check declared `--analysis` names in TOML against what's
  *actually* been registered (catches dead analyses, typo-renamed
  analyses).
- New rule `casetrack-stale-registration` (WARNING): the script's
  current AST hash differs from its AST hash at last `casetrack
  append`. Means "next register may produce different semantics from
  what's currently in the DB" — the silent-semantic-drift class the
  project exists to surface.
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

### Q6 — AST hashing scheme for `casetrack-stale-registration`: **SHA256 of source minus whitespace + comments**

Simplest thing that could work. One implementation across R / Py /
bash (regex-strip comments per language, collapse whitespace, hash).
Cost: cosmetic edits (reformatting, adding a comment) will *not* be
flagged as drift — that's the point. Real semantic edits will. Promote
to per-language AST normalizers (`ast.dump` for Python, `parse()` for
R, `shfmt` for bash) only if false-positive rate from
near-semantic-equivalent edits is high in practice.

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
| `casetrack-stale-registration` | WARNING | provenance.jsonl | A |
| `casetrack-orphan-analysis` | NOTE | TOML × provenance cross-check | A |

Round 1 ships `casetrack-schema-drift`, `casetrack-stale-registration`,
`casetrack-orphan-analysis`. Round 2 ships the C1 rules. Round 3 ships
C3 declared/inferred rules (IDs TBD).

## 6. Out of scope

- Layer B (runtime trace) — cross-project ROADMAP #2.
- Casetrack v0.2 flat-TSV mode — deprecated, removed in v1.0.
- Snakemake/Nextflow DAG audit — ROADMAP #3, separate effort.
- Cohort-level coverage audit ("this analysis covers 15 of 20 assays")
  — casetrack's own `status` / `query` does this; not the auditor's job.
