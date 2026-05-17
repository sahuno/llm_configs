# sciAuditor — Workflow DAG Audit Plan (ROADMAP #3 round 1)

> Round-1 plan for the workflow-level static analyzer. Supersedes the
> brainstorm at
> [`07_workflow_dag_audit_brainstorm.md`](07_workflow_dag_audit_brainstorm.md),
> which captured the open questions, alternatives considered, and
> the trade-off framing. This doc carries the **locked decisions** and
> the concrete work items for round 1.
>
> Decisions framed against high-stakes audit work: false positives erode
> trust (audits get muted), false negatives let corrupt data downstream
> (wasted compute, retracted figures, in the lab's domain potentially
> clinical harm). Every lock below was chosen with both costs in view.

## 0. Round-1 scope (one paragraph TL;DR)

Round 1 ships two contracts — **D2 (topology)** and **D1 (cross-rule
schema consistency)** — for Snakemake only, via subprocess
introspection (not DSL parsing). A new top-level
`sciauditor_workflow.py` loads a rule graph from `snakemake --summary`
+ `--rulegraph`, hands each rule's script to the existing per-script
parsers, and validates the DAG. Output is a
`workflow_audit_report.md` with an annotated rulegraph plus a
`workflow_findings.tsv` for CI. **Acceptance**: ≥ 1 real finding
fires on a real lab Snakefile
(`CCV-neoquality-pipeline/wf_snakemake/workflow/Snakefile` is the
round-1 fixture).

## 1. Round-1 rule inventory

| Contract | Rule ID | Severity | Source signal |
|---|---|---|---|
| D2 topology | `workflow-dangling-input` | BLOCKER | rule's `input:` not produced by any other rule AND not in the workflow's declared raw inputs |
| D2 topology | `workflow-orphan-rule` | NOTE | rule's `output:` never referenced as input by another rule AND not in `rule all:` |
| D2 topology | `workflow-unreachable-rule` | NOTE | rule present in `--list-rules` but no forward path from `rule all:` reaches it |
| D1 schema | `workflow-schema-drop` | BLOCKER | consumer rule reads col not in producer's emitted cols |
| D1 schema | `workflow-schema-extra` | NOTE | producer writes col no consumer reads (wasteful, not corrupt) |
| D1 schema | `workflow-inline-blind` | NOTE | producer is inline `shell:`, audit can't infer cols on this edge |
| D6 (preview) | `workflow-meta-yml-drift` | WARNING | nf-core rule's `meta.yml` schema disagrees with inferred `main.nf` schema |

D3, D4, full-D6 ship in round 2 (see §2).

**Severity philosophy (high-stakes lens):**
- BLOCKER is reserved for runtime-certain failures (KeyError, MissingInputException). False-positive cost is high (people will mute), so we restrict to certainties.
- WARNING is for "valid pipeline behaviour but smells like a bug" (meta.yml drift, container drift in round 2). User judgement required.
- NOTE is for "audit blind here" (inline-blind, schema-extra, orphan-rule). Acknowledges the audit's limits without forcing action.

## 2. Round-2 and -3 scope (deferred from round 1)

| Round | Contracts | Highlights |
|---|---|---|
| 2 | D3 + full D6 + Nextflow loader | `workflow-genome-drift` BLOCKER, `workflow-container-drift` WARNING, full workflow ↔ casetrack coverage check, `nextflow inspect` plumbing |
| 3 | D4 wildcard / channel-shape | Snakemake wildcard set agreement; Nextflow tuple shape agreement |
| Out of #3 | D5 workflow-resource budget | Defer (semi-redundant with `runtime-resource-study` skill) |

## 3. Architecture (locked: Option B from §3 of brainstorm)

Bootstrap from the engine's introspection commands, not DSL parsing.
The risk of DSL parsing (importing `snakemake.workflow`) is a silent
breakage class every snakemake major bump; subprocess to a stable CLI
flag is a contract we can pin.

```
sciAuditor/aggregator/
    workflow_check.py            # NEW — WorkflowIndex + D1/D2 checkers
    workflow_loaders/
        __init__.py
        snakemake_loader.py      # NEW round 1
        # nextflow_loader.py     # round 2
```

`workflow_check.py` exports the same shape the casetrack module
already established:

```python
@dataclass
class WorkflowRule:
    name: str
    engine: str                  # "snakemake" (round 1) | "nextflow" (round 2)
    script_path: Path | None
    inferred_yaml: dict | None
    inputs:  list[str]
    outputs: list[str]
    edges_in:  list[str]
    edges_out: list[str]
    wildcards: set[str]
    declared_genome: str | None      # round 2
    declared_container: str | None   # round 2
    meta_yml_inputs:  list[dict] | None
    meta_yml_outputs: list[dict] | None
    rule_kind: str                   # "script" | "shell_inline" | "wrapper" | "module"

@dataclass
class WorkflowIndex:
    engine: str
    workflow_file: Path
    rules: dict[str, WorkflowRule]
    edges: list[tuple[str, str, str]]   # (upstream, downstream, shared_path)
    target_rules: set[str]              # rules in `rule all:` target sets

def load_workflow(workflow_file: Path, engine: str = "auto") -> WorkflowIndex: ...
def check_workflow(index: WorkflowIndex) -> list[Finding]: ...
```

Findings reuse the casetrack `Finding` dataclass — 4-tuple
(severity, rule, sites, note) — so they roll up through the existing
severity_counts pipeline unchanged.

## 4. CLI surface (locked: Option β — new top-level)

```
sciauditor_workflow.py \
    --workflow-file <Snakefile> \
    --workflow-engine snakemake \         # round 1 only accepts snakemake
    --casetrack-project <cohort/> \       # optional; enables meta-yml-drift
    --output-dir <out/> \
    --jobs 8 \
    --fail-on BLOCKER
```

Why a separate CLI (not a flag on `sciauditor_aggregate.py`): different
audit unit (workflow vs. script bag), different output shape (annotated
DAG vs. cohort table), different failure modes. Augmenting the cohort
aggregator with `--workflow-file` would blur the contract and
complicate the failure-mode taxonomy.

**Internally**, `sciauditor_workflow.py` calls the existing
`run_parser()` from `sciauditor_aggregate.py` for each rule's script.
No duplication; the per-script parsers are reused as-is.

## 5. Locked decisions (full restatement of §5 + §8 from brainstorm)

### Q1 — Engine: Snakemake only in round 1
Snakemake's introspection surface (`--summary`, `--rulegraph`,
`--list-rules`) is mature. Nextflow's `inspect` is younger.
**Trust budget**: ship to one well-understood engine before adding a
second; round 2 brings Nextflow once the rule-index abstraction is
proven.

### Q2 — DAG extraction: subprocess, not import
Subprocess to `snakemake --summary` / `--rulegraph`. Importing
`snakemake.workflow` couples us to internals that break on major
version bumps — a silent breakage class. **Mitigation**: pin the
snakemake version used by the auditor in fixture tests; snapshot the
parsed output of `--summary` per round so regressions surface as test
failures, not as silently-wrong audits.

### Q3 — Inline-shell rules: audit topology, NOTE for schema-blind edges
For any rule with no `script:` directive (inline `shell:` only), D2
checks still fire; D1 cannot. Emit `workflow-inline-blind` NOTE with
note text "manually verify this edge — audit cannot infer producer
columns from inline shell." NOTE — not WARNING — because the rule
itself isn't broken; the audit is just blind. Wording matters: a
reviewer must not read this as "everything's fine here."

### Q4 — `include:` / subworkflow chains: fully expanded before audit
`snakemake --rulegraph` already expands includes; we use its output
directly. **Mitigation against silent miss**: assertion that
`rules from --list-rules` ⊆ `rules from --rulegraph`; failure aborts
the audit with a clear error (`workflow-rulegraph-mismatch`, fatal —
not a finding, an exit code).

### Q5 — Wildcard expansion: rule-template validation in round 1, expanded-DAG in round 2
Round 1 catches static-path typos (`coverage.tvs`). Round 1 does NOT
catch wildcard-resolution mismatches (a sample-sheet entry missing the
column rule B expects). **Documented false-negative class**, listed in
round-1 release notes. Closed by round 2 + Layer B.

### Q6 — nf-core `meta.yml`: ground truth; short-circuit per-script inference
The audit-quality multiplier. When a rule points at a `main.nf` with
an adjacent `meta.yml`, read meta.yml's `input:` / `output:` blocks
directly into `WorkflowRule.meta_yml_inputs/outputs`. Cross-check by
ALSO running per-script inference on `main.nf` and emitting
`workflow-meta-yml-drift` WARNING when the two disagree — this catches
upstream nf-core module bugs the per-script audit alone wouldn't find.

### Q7 — Output: annotate the existing `--rulegraph` DOT + emit `workflow_findings.tsv`
Reuse the engine's own DAG visualisation; the audit is auxiliary, not
authoritative. The findings TSV is the machine-readable contract for
CI. Annotated DAG renders as a mermaid block in
`workflow_audit_report.md`.

### Q8 — Severity ladder
Locked per §1 table above. `workflow-schema-drop` is BLOCKER
(runtime-certain KeyError); `workflow-schema-extra` is NOTE (wasteful
but not corrupt); `workflow-dangling-input` is BLOCKER
(MissingInputException certainty); orphan/unreachable are NOTE.
**No softening for legacy** — `--ignore <glob>` is the documented
escape hatch; softening trains the audit out.

### Q9 — Workflow config: materialised to JSON pre-pass
Snakemake `configfile:` resolved before the per-script parsers run;
passed via a new `--workflow-params <json>` flag. Every unresolvable
config reference in a rule emits its own NOTE so the user knows the
genome-build / container check was partial on that rule.

### Q10 — Caching: none in round 1
Round 1 always re-parses every rule's script. Correct beats fast.
Cache invalidation is a separate bug class; round 2 polish.

### OQ1 — Nextflow `inspect` JSON stability: pre-round-1 probe
Before round 2 starts, run `nextflow inspect` against
`/data1/greenbab/users/ahunos/apps/casetrack-nf-subworkflows/main.nf`
on two nextflow versions; snapshot the JSON. Result either confirms
subprocess-introspection works for nextflow, or pushes round 2 to a
.nf-regex extraction fallback.

### OQ2 — Cache-collision: documented design, not implemented in round 1
Cache key (when round 2 lands): `(script_path, mtime, parser_version,
sha256(workflow_config_json))`.

### OQ3 — `shell.shell()` sub-scripts: separate rule nodes
Generalises the per-script auditor's existing bash-launcher pattern.
A rule whose `shell:` block delegates real work to an external bash
script is treated as TWO rule nodes in the WorkflowIndex: the
snakemake rule (audit-blind on cols) plus the bash launcher (audited
fully). Closes a false-negative class.

### OQ4 — Snakemake `wrapper:` directive: read `wrappers/<name>/meta.yaml`
Treated analogously to nf-core meta.yml. Round 1 ships a minimal
wrapper-reader (≤ 30 lines); deep wrapper-internal audit deferred to
round 3.

## 6. Implementation work items (round 1)

Items 1–4 are independent and could ship as one batched commit or
four. Item 5 is the verification milestone.

### Item 1 — Snakemake loader
**File**: `sciAuditor/aggregator/workflow_loaders/snakemake_loader.py` (new)
**What**:
- Subprocess `snakemake --summary --quiet` → parse one row per output file (rule, file, input file, ...)
- Subprocess `snakemake --rulegraph` → parse DOT edges
- Subprocess `snakemake --list-rules` → cross-check rule set
- Subprocess `snakemake --dry-run --printshellcmds --quiet` → recover `script:` paths and inline-shell bodies
- Build and return `WorkflowIndex`
**Cost**: ~200 lines.
**Open**: how to detect `rule kind` (`script` | `shell_inline` | `wrapper` | `module`) — peek at the rule directive listing from `--detailed-summary` or a small regex pass over the Snakefile.

### Item 2 — Shared workflow checker
**File**: `sciAuditor/aggregator/workflow_check.py` (new)
**What**:
- `WorkflowRule` / `WorkflowIndex` dataclasses (§3)
- `check_workflow(index)` runs D1 + D2 rules
- D1 schema diff: walks producer `outputs[].written_by → dataframes[].columns` (already wired in casetrack rounds 1+2), walks consumer `inputs[]` + col-access references in source
- Reuses `Finding` from casetrack_check.py
**Cost**: ~250 lines.

### Item 3 — Per-rule script audit dispatch
**File**: `sciAuditor/aggregator/workflow_check.py` (same file as Item 2)
**What**:
- For each `WorkflowRule.script_path is not None`, invoke per-script parser via `run_parser()` reused from `sciauditor_aggregate.py`
- Materialise inferred YAML at `<out>/per_rule/<rule_name>.yaml`
- Populate `WorkflowRule.inferred_yaml`
**Cost**: ~80 lines (mostly glue).

### Item 4 — Workflow report + findings TSV
**File**: `sciAuditor/aggregator/workflow_report.py` (new)
**What**:
- Annotated rulegraph as mermaid in `workflow_audit_report.md`
- Per-rule findings table
- Per-edge findings (BLOCKER edges marked with ⚠)
- `workflow_findings.tsv` (same 4-col shape as casetrack: severity / rule / sites / note)
- `--fail-on BLOCKER` honored
**Cost**: ~150 lines.

### Item 5 — Top-level CLI + end-to-end demo
**File**: `sciAuditor/aggregator/sciauditor_workflow.py` (new)
**What**:
- `argparse` interface from §4
- Calls Items 1–4 in order
- Runs against
  `/data1/greenbab/users/ahunos/projects/CCV-neoquality-pipeline/wf_snakemake/workflow/Snakefile`
  → must produce ≥ 1 real finding to satisfy acceptance
- Writes round-1 release notes (the documented false-negative classes from §5 Q5)
**Cost**: ~80 lines glue + verification + docs.

**Total round-1 budget**: ~760 lines + verification.

## 7. Acceptance criteria

Round 1 ships when ALL of these pass:

1. **Engine compatibility**: snakemake ≥ 9.0 confirmed via the lab's `snakemake` env (`/home/ahunos/miniforge3/envs/snakemake`). Pin in fixture.
2. **Load latency**: `WorkflowIndex` built for a 50-rule fixture in < 30s wall (no quadratic blow-ups in edge construction).
3. **Real finding**: ≥ 1 finding fires on `CCV-neoquality-pipeline/.../Snakefile` (any rule severity). If we can't surface one, we're not testing the right fixture — fail and pick a different one.
4. **No cohort-aggregator regression**: pre-existing `sciauditor_aggregate.py` smoke runs on `casetrack_su2c_git` and `project_17424/validation` produce identical totals to round 2 of casetrack.
5. **CI gate**: `--fail-on BLOCKER` honored — exit code 1 iff `workflow_findings.tsv` has any BLOCKER row.
6. **Release notes** committed alongside, listing the documented round-1 false-negative classes (wildcards unresolved, Nextflow unaudited, inline-shell-blind, dynamically-built dataframes from the casetrack-round-2 NOTE-fallback).

## 8. Order of operations (recommended)

1. **Item 1** (snakemake_loader) — independent foundation.
2. **Item 2** (workflow_check) — D2 first (topology, no per-script deps), then D1.
3. **Item 3** (per-rule dispatch) — glue Items 1+2 to the existing parsers.
4. **Item 4** (report + TSV) — depends on Items 1–3 producing real data.
5. **Item 5** (CLI + demo) — verification milestone; locks the round.

Commit + push between items, same cadence as casetrack rounds 1+2.
End-to-end smoke against the lab Snakefile after each item to catch
regressions early.

## 9. Out of scope (round 1)

- **Nextflow** — round 2.
- **Wildcard resolution validation** — round 2 / Layer B.
- **Genome / container drift** (D3 full) — round 2.
- **Full workflow ↔ casetrack coverage** — round 2.
- **Snakemake checkpoints** — Layer B (dynamic DAG; static audit can't resolve).
- **`workflow_findings.tsv` rollup into cohort aggregator's `cohort_findings.tsv`** — open question, decide in round 2 once we know the access pattern.

## 10. Layer B coupling (ROADMAP #2)

Workflow-level static audit and Layer B runtime trace compose:
- Workflow audit shows *where* in the DAG to instrument.
- Layer B *instruments* and produces real traces — collapses every
  round-1 false-negative class to a confident BLOCKER/WARNING (no more
  NOTE-fallback for unresolved cols, no more rule-template-only
  wildcard validation).
- Both build on the same per-script YAML schema, so the data-model
  refactor cost between the two is zero.

ROADMAP #3 round 1 ships first because:
1. Per-script YAML infra is production-grade (casetrack rounds 1+2).
2. Subprocess DAG extraction is days, not weeks.
3. Real findings fire on real lab pipelines on day 1.
4. ROADMAP #2 has months of sandboxing + fixture work to do first.
