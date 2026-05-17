# sciAuditor — Layer B Runtime Trace Brainstorm (ROADMAP #2)

> Brainstorm doc for the runtime-trace layer that complements Layer A
> (static inference). Cross-references
> [`02_inference_design.md`](02_inference_design.md) §4 (the YAML
> schema this layer enriches in place) and
> [`08_workflow_dag_audit_plan.md`](08_workflow_dag_audit_plan.md) §10
> (the composition story with ROADMAP #3).
>
> Status: pre-plan. Layer B is more speculative than the workflow
> audit — sandboxing, fixtures, language runtimes, and trust models
> all enter the design space. Several decisions stay open in §5; I'll
> flag them so we can resolve in another round of conversation rather
> than locking defaults at brainstorm time.
>
> High-stakes framing (same lens as ROADMAP #3 round 1):
> - **FP cost**: tracer reports a phantom bug → researcher chases a
>   ghost; trust erodes; the audit gets muted.
> - **FN cost**: fixture didn't exercise the buggy path → false
>   confidence; corrupt result lands in a figure or a clinical report.
> - **The fixture-coverage problem is THE central reliability
>   question for Layer B.** Most of the design tension below comes
>   from balancing FP-from-tracer-bugs against FN-from-shallow-fixtures.

## 0. What static analysis can't see — concrete failure cases

Layer A is fundamentally blind to these. Each example comes from real
cases in the lab's recent work:

1. **Dynamically-built dataframe columns.**
   The casetrack-round-2 `casetrack-fk-mismatch` NOTE-fallback exists
   precisely because `pd.DataFrame.groupby(...).sum()` or
   `df.pivot_table(...)` can't be statically column-resolved. A real
   `specimen_id` vs `sample_id` FK mismatch would slip past as NOTE.
2. **Dynamic path resolution.**
   `output_path = f"{OUTDIR}/{run_tag}/{sample}.bedmethyl"` where any
   of those vars come from `argparse`, `os.environ`, or a config
   YAML. Layer A records `path_template`; can't know `path_resolved`.
3. **Filter row counts.**
   `df = df[df.qc_pass]` — the script's log file *should* record
   the before/after counts (CLAUDE.md mandates this), but the audit
   has no way to verify that the LOG numbers reflect REAL drops vs.
   off-by-one logic errors.
4. **Library-internal I/O.**
   `DESeqDataSetFromMatrix(countData=cts, colData=meta, design=~x)`
   internally accepts implicit sample-order alignment. If `meta`
   columns don't match `cts` columns *by order*, the model silently
   pairs the wrong rows. No static inference catches this.
5. **Seed reachability.**
   `set.seed(SEED_VAR)` where `SEED_VAR` is set elsewhere or read
   from an env var. Layer A flags "stochastic op present, seed call
   present"; can't prove the seed call's value reached the
   stochastic call at runtime.
6. **Wildcard-expansion mismatches** (cross-references
   `08_workflow_dag_audit_plan.md` §5 Q5).
   Rule A's `{sample}` set in `--rulegraph` template doesn't match
   the consumer rule's expansion when a sample sheet row is missing
   a column.
7. **Container vs. host-env drift.**
   Per-script audit says "uses samtools 1.18 per the conda env";
   runtime says "PATH actually resolved to /usr/bin/samtools 1.10
   because the container's PATH order was different." Real bugs the
   lab has hit.

Each of these is a confidence upgrade Layer B can deliver — they go
from Layer A NOTE / WARNING ("can't verify") to Layer B BLOCKER /
PASS ("verified true / verified false").

## 1. The contracts (what Layer B can ground-truth)

Same framing as casetrack & workflow brainstorms: discrete contracts,
ship one per round, with explicit FP/FN cost framing per contract.

### B1. Materialised `dataframes[].columns`
For every dataframe produced at runtime in a Python or R script,
record its *actual* column list at the moment of `to_csv` / `fwrite`.
Replaces Layer A's NOTE-fallback. Output enriches the inferred YAML's
`dataframes[].columns` in place: static → runtime where present, with
a `resolved_by: layer_b` marker.
- **FP risk**: tracer crashes (bug in monkey-patch) → script appears
  broken when it isn't.
- **FN risk**: fixture has wrong dtype → tracer produces a column
  list that doesn't reflect real cohort data.

### B2. Filter pass-through row counts
For every `df.query` / `df[mask]` / `dplyr::filter` / `subset` call,
record `(rows_before, rows_after)` at runtime. Validates the script's
log claims; catches off-by-one filter bugs.
- **FP risk**: low — row counts are concrete.
- **FN risk**: medium — fixture might not exercise the filtered path.

### B3. Resolved paths
For every `to_csv` / `fwrite` / `saveRDS` / file open call, record
`path_resolved` alongside `path_template`. Catches typos, missing
directories, and env-var resolution failures.
- **FP risk**: low.
- **FN risk**: medium — fixture may resolve to a tmpdir; production
  path resolution differs.

### B4. Seed reachability
Wrap `random.seed` / `np.random.seed` / `set.seed` and every
stochastic call. For each stoch call, record whether a seed was set
in this stack frame's reachable call path. Replaces Layer A's
inferential `seed-coverage` rule with a runtime certainty.
- **FP risk**: low — execution is the ground truth.
- **FN risk**: low for the same reason.

### B5. Library-internal I/O & ordering checks
Hook into known-risky entry points: `DESeqDataSetFromMatrix` (counts ↔
metadata column alignment), `Seurat::CreateSeuratObject` (cell
identity / metadata alignment), `sklearn.fit(X, y)` (length match),
`anndata.AnnData(obs=..., var=...)` (axis match). Emit BLOCKER on
detected misalignment.
- **FP risk**: medium — these libraries have heuristic ordering
  rescue logic that might accept what looks broken. Need to test
  against real failure modes.
- **FN risk**: low when the hook fires; high when a hook is missing
  (need to inventory the library entry points).

### B6. Resource consumption (composes with `runtime-resource-study` skill)
Per-script wall time, peak RSS, file system in/out. Re-derives the
benchmark surface but on-script (whereas the skill is on-tool). Lower
priority for round 1; flagged here for completeness.

### B7. Workflow-level wildcard / channel-shape ground truth
Once the workflow audit (ROADMAP #3) lands, Layer B can validate
wildcard expansion: run rule A on the fixture, capture the `{sample}`
set in its outputs; run rule B on rule A's outputs, verify the
expansion matches. Closes the round-1 workflow-audit FN class around
wildcards. Cross-references
[`08_workflow_dag_audit_plan.md`](08_workflow_dag_audit_plan.md) §5 Q5.

## 2. The execution model — three big design questions

Each of these has FP/FN implications and needs a deliberate answer
before round 1 of Layer B starts. The two extremes for each are
sketched; my leaning is marked, but I'm explicitly LEAVING THEM
OPEN for you to redirect.

### Q-exec — How does Layer B actually run the user's script?

**Option E1: In-process tracer via `sys.settrace()`**
Python's per-line callback hook. Captures every function entry and
return; can mutate locals. Same approach as `pdb`, `coverage.py`.
- Pro: zero modifications to user scripts; deep introspection.
- Con: 50–100× slowdown; tracer crashes take the audit process down;
  no isolation from side effects.

**Option E2: AST-instrumented copy of the script**
Read the script, rewrite it (add tracer calls around dataframe ops),
exec the rewritten copy in a subprocess.
- Pro: tracer overhead concentrated at known points (~5–10×); user
  script unchanged on disk; subprocess isolates failures.
- Con: AST rewrite is per-language (separate work for Py + R);
  rewrites can break in unexpected ways (decorators, exec strings).

**Option E3: Library-level monkey-patches**
Wrap the script's invocation: `sys._sciauditor_patched = True`,
then `exec` the script in a process where `pandas.DataFrame.to_csv`
is patched to also log to a trace file. No AST rewrite; no
per-line tracer.
- Pro: simplest implementation; near-zero overhead outside patched
  calls; same approach works for Py and R (with R's `trace()`).
- Con: only sees patched entry points; misses arbitrary code (custom
  filter loops, raw NumPy ops). Limited to "known interesting"
  library APIs.

**Recommended for round 1**: E3 — library-level monkey-patches.
Most lab scripts touch pandas + numpy + sklearn + a few R packages,
all of which have well-defined entry points. Round 2 can add E2 (AST
rewrite) for the long tail.

### Q-fixture — How does Layer B get "head-of-real" data?

**Option F1: Truncate inputs to first N rows / records**
For every script input (tabular, BAM, VCF, fastq), generate a
head-N fixture deterministically. N defaults to 1000 rows, 1000
reads, etc.
- Pro: minimal upfront work; fixture is auto-generated.
- Con: most genomics analyses break on truncated data (DESeq2 needs
  ≥3 replicates per condition; methylation calling needs coverage
  diversity; alignment quality changes with read count).

**Option F2: Per-script `audit_fixture:` declaration**
Each script declares its own fixture path in a companion file (or in
the script header). The fixture is hand-curated to exercise the
script's logic without consuming TB of input.
- Pro: scientist controls coverage; fixture is biological enough to
  exercise real failure paths.
- Con: requires upfront fixture creation per script; coverage gap if
  scripts get added without fixtures.

**Option F3: Casetrack-backed fixture pool**
Tie into casetrack's existing test-cohort manifests. The audit
fixture for a script tracked in casetrack is the casetrack
test-cohort row set. Layer B reads the cohort, takes a fixed
representative slice (e.g., first patient's first sample), runs.
- Pro: one fixture pool serves N scripts; reproducible because
  casetrack tracks the fixture exactly.
- Con: only works when the script is registered with casetrack;
  exploratory scripts get F2 fallback.

**Recommended for round 1**: F2 (explicit declaration) as the
primary mechanism, with F1 as fallback for scripts that don't
declare. F3 as a future composition once casetrack-round-3 ships
fixture-pool semantics. The pragmatic ordering: declare fixtures for
the audit-critical scripts first; F1-auto-truncate the rest with a
visible WARNING ("fixture-auto-truncated, results approximate").

### Q-sandbox — How does Layer B prevent the script from corrupting the world?

The script we're tracing might:
- Write to the lab's shared `/data1/` filesystem.
- Push to S3.
- Send a Slack notification on completion.
- Submit a downstream SLURM job.
- Modify the casetrack DB.

Layer B execution must NOT trigger any of these.

**Option S1: Untrusted by default, container-isolated**
Wrap every Layer B execution in Apptainer (the lab's standard) with
`--bind <fixture_dir>:rw --no-network --containall`. Default-deny
everything else.
- Pro: production-grade isolation; lab already uses Apptainer.
- Con: slower startup (~1–2s container cold start); breaks scripts
  that depend on host conda envs not in the SIF.

**Option S2: Process-level sandbox via `bwrap` / `unshare`**
Linux user-namespaces; no container required. Cheaper.
- Pro: faster than Apptainer; no SIF management.
- Con: less stable across kernel versions; harder to reproduce
  failures; some lab compute nodes restrict user namespaces.

**Option S3: Monkey-patch I/O at the Python/R level**
Override `open`, `os.makedirs`, `subprocess.run`, `requests.*`,
`boto3.*`. Default-deny writes outside `tmpdir`; default-deny network.
No OS-level isolation.
- Pro: simplest; works with the host conda env directly.
- Con: incomplete — a script that uses C-extension I/O bypasses the
  monkey-patches entirely. **Single dropped check = silent corruption.**

**Recommended for round 1**: S1 (Apptainer). The lab's container
infra is mature, and "untrusted by default" is the right stance for
high-stakes audit work. The cold-start cost is real but worth it; we
amortise it by batching N scripts per container invocation.
Document the SIF requirements (Python ≥3.12, pandas/numpy/sklearn,
R + tidyverse if R audit on) so users can build their own when
the standard one doesn't fit.

## 3. Phasing (one contract or contract-group per round)

| Round | Ships | Why this order |
|---|---|---|
| **1** | B1 (cols) + B2 (filter counts) + B3 (paths) for **Python only**, monkey-patch tracer (E3), per-script fixture (F2), Apptainer isolation (S1) | Lowest sandboxing complexity; pandas hooks are well-known; biggest practical FP-replacement (casetrack-fk-mismatch NOTE → BLOCKER/PASS); zero genomics-fixture engineering. |
| **2** | Same contracts for **R**; B4 (seed reachability) for both; F1 fixture auto-truncate fallback for scripts without F2 declaration | R execution semantics; lifts the requirement that EVERY script have a hand-curated fixture. |
| **3** | B5 (library-internal I/O hooks for DESeq2 / Seurat / sklearn); B7 workflow wildcard ground truth (composes with ROADMAP #3 round 2). | Highest signal-per-script for the analytical core of the lab; genomics-fixture engineering for BAM/VCF/fastq head-of-real begins. |
| Out of #2 scope | B6 (resource benchmarks) | Defer; `runtime-resource-study` skill already covers this for the per-tool case. |

This is more rounds than ROADMAP #3 because Layer B's per-language and
per-domain work is genuinely additive — Python ground-truth helps
Python-heavy DGE analyses; R ground-truth helps Bioconductor/Seurat
analyses. Both ship value independently.

## 4. Architecture (round 1)

```
sciAuditor/
    layer_b/                           # NEW directory
        __init__.py
        tracer_py.py                   # Python monkey-patch tracer
        # tracer_r.R                   # round 2
        sandbox.py                     # Apptainer wrapper
        fixture.py                     # F2 declaration parsing, F1 fallback (round 2)
        merge_into_yaml.py             # post-process: enrich inferred YAML with trace
    aggregator/
        sciauditor_layer_b.py          # NEW top-level CLI
```

### Tracer model (E3, round 1)

```python
# tracer_py.py — runs inside the sandboxed subprocess BEFORE user script
import pandas as pd
import numpy as np
import os, sys, json, atexit
from pathlib import Path

_TRACE_PATH = Path(os.environ["SCIAUDITOR_TRACE_FILE"])
_TRACE: list[dict] = []

def _record(event_type: str, **fields):
    fields["t_us"] = time.monotonic_ns() // 1000
    fields["event"] = event_type
    _TRACE.append(fields)

# Hook pd.DataFrame.to_csv
_orig_to_csv = pd.DataFrame.to_csv
def _to_csv_traced(self, path_or_buf=None, sep=",", *a, **kw):
    _record("dataframe_write",
            cols=list(self.columns), nrows=len(self),
            path=str(path_or_buf), sep=sep)
    return _orig_to_csv(self, path_or_buf, sep=sep, *a, **kw)
pd.DataFrame.to_csv = _to_csv_traced

# Hook df.query / df.__getitem__(mask)
# Hook np.random.seed / random.seed
# Hook open() for path resolution
# ...

@atexit.register
def _flush():
    with _TRACE_PATH.open("w") as f:
        for e in _TRACE: f.write(json.dumps(e) + "\n")
```

User script then runs as: `python -c "import sciauditor.layer_b.tracer_py;
exec(open('user_script.py').read())"`.

### Trace artifact format

JSON Lines, one event per row. Fields:
```
{event: "dataframe_write", path: "...", cols: [...], nrows: N, t_us: ..., site: line}
{event: "filter", op: "df.query", rows_before: N, rows_after: M, t_us: ..., site: line}
{event: "path_resolve", template: "{OUT}/{S}.tsv", resolved: "/tmp/...", t_us: ...}
{event: "seed_set", value: 42, generator: "np.random", t_us: ..., site: line}
{event: "stochastic_call", fn: "np.random.normal", seeded_before: true, t_us: ..., site: line}
```

### Merge into per-script YAML

After trace completion, `merge_into_yaml.py` reads `<script>.trace.jsonl`
and updates the inferred YAML in place:
```yaml
dataframes:
- id: my_df
  site: 42
  columns: [a, b, c]          # was: null (Layer A couldn't resolve)
  resolved_by: layer_b        # marker: this came from runtime
  trace_site: 42
```

casetrack_check.py and workflow_check.py both already read
`dataframes[].columns` — they get the runtime-resolved value
transparently. No downstream code changes for Layer B round 1.

## 5. Decisions to make before round 1 of Layer B

I'm leaving more of these OPEN than in the workflow plan because
Layer B has more genuine design tension. My leaning is noted; the
high-stakes lens demands a deliberate user call on each.

### Q1 — Execution mechanism: **leaning E3 (monkey-patch)**
Why: simplest; lowest FP risk (tracer is small + focused);
covers ~90% of lab dataframe ops without AST work.
Open: do we need E2 (AST rewrite) for cases E3 misses? Postpone the
decision to round 2 once we have FN data from real audits.

### Q2 — Fixture mechanism: **leaning F2 (explicit declaration) for round 1, F1 fallback round 2**
Why: F2 puts the FN responsibility on the human author (correct
ownership). F1 auto-truncation is too fragile for biological data
without explicit per-script knowledge.
Open: what does the F2 declaration FORMAT look like? Companion file
(`my_script.audit_fixture.yaml`)? In-script comment block? Per-
project manifest?

### Q3 — Sandboxing: **leaning S1 (Apptainer) for round 1**
Why: production-grade isolation; lab already uses it.
Open: do we mandate a single shipped SIF, or let users bring their
own? Single SIF = reproducibility + slow to update. BYO SIF =
flexible + footgun.

### Q4 — Trust model: **OPEN — needs explicit user decision**
Layer B *executes* user code. Options:
  - Default off; opt-in per-script via `audit_b: enable: true`.
  - Default off; opt-in per-cohort via aggregator CLI flag.
  - Default on for audit-critical scripts (identified by `audit_priority:`
    in the manifest), off otherwise.
  - Default on for ALL Python scripts (R round-2).
Each has different FP/FN implications for the operator. **Strongly
recommend** option 1 or 2: Layer B should never run unprompted.

### Q5 — Fixture caching across cohort runs: **leaning yes, content-addressed**
Cache the trace JSON by `(script_sha256, fixture_sha256, tracer_version)`.
Avoids re-running the same script + fixture between audits.
Open: cache invalidation when the script's *dependencies* (libraries)
change — we don't reliably detect this. Worst-case: a pandas upgrade
silently invalidates a cached trace.

### Q6 — Failure mode when a script crashes during trace: **leaning emit NOTE, don't BLOCK**
A script that fails on the fixture might fail because:
  - The fixture is too small for the script's logic.
  - The script has a real bug.
  - The tracer broke the script.
Three orthogonal causes. **Strongly recommend** NOTE not BLOCKER
("script failed during trace; reason unknown"), with a separate
`layer-b-tracer-crash` finding when the tracer itself raised.

### Q7 — Side effects: read-only network, RW only on tmpdir: **leaning yes, mandatory**
The sandbox must deny network by default; must deny writes outside
the designated tmpdir. Any attempt to violate gets recorded as a
finding (`layer-b-side-effect-attempt` BLOCKER).
Open: do we ALSO record reads from non-fixture paths? A script that
reads `/data1/cohort/raw/...` outside its fixture is doing something
it shouldn't. Could be a fixture-coverage gap OR a script bug.

### Q8 — Reporting: **leaning enrich inferred YAML + emit `layer_b_trace.jsonl`, no separate report.md**
Layer B's findings flow through the existing per-script audit_report
once the inferred YAML is enriched. The raw trace is the audit
artifact for forensic analysis. Avoids creating a third report
format.

### Q9 — Composition with workflow audit: **leaning Layer B is the "deep audit", workflow audit is the "fast audit"**
Workflow audit runs in seconds, in CI, on every PR. Layer B runs in
minutes, on a schedule (nightly?), on a fixture cohort. Different
cadence; same finding model.

### Q10 — High-leverage first hooks: which library entry points for round 1?
Round 1 monkey-patches:
- `pandas.DataFrame.to_csv`, `to_tsv`, `to_parquet`
- `pandas.DataFrame.__getitem__` (boolean-mask filter)
- `pandas.DataFrame.query`
- `pandas.read_csv`, `read_table`, `read_parquet` (resolved path)
- `numpy.random.seed`, `random.seed`, `numpy.random.*` (stochastic ops)
- `open()` (path resolution)

R hooks (round 2) follow the same pattern with `data.table::fwrite`,
`base::write.csv`, `dplyr::filter`, `set.seed`, etc.

## 6. MVP target — round 1

End-to-end on one or two real lab Python scripts:
- A casetrack-registered analysis where Layer A emits the
  `casetrack-fk-mismatch` NOTE (cols-unresolvable). Layer B should
  EITHER promote it to BLOCKER (real mismatch) OR resolve to PASS
  (cols match). Replaces the NOTE.
- A DGE-style script (DESeq2 or pyDESeq2) where we test B5 hooks on
  count-data ↔ metadata alignment.

Acceptance:
1. Layer B runs the script in Apptainer sandbox; produces
   `trace.jsonl` with ≥ 10 events.
2. Enriched YAML has populated `dataframes[].columns` from the trace
   for at least one dataframe that was null after Layer A.
3. casetrack-fk-mismatch on the test script flips from NOTE to
   BLOCKER or PASS (no longer "couldn't infer").
4. Sandbox correctly blocks an attempted write to `/data1/`.
5. Round-1 release notes document the known false-negative classes
   (fixture coverage; libraries without hooks).

## 7. Out of scope (round 1)

- **R scripts** — round 2.
- **Genomics tool I/O** (BAM/VCF parsers, modkit, dorado) —
  round 3 or out of #2 entirely.
- **GPU / CUDA-dependent code** — Layer B sandbox is CPU-only.
- **Real cohort data execution** — always fixture-only by design.
- **Streaming / generator-based dataframes** — only materialised
  dataframes get column traces.
- **Multi-process / multi-thread tracing** — round 1 assumes
  single-threaded user scripts. Re-evaluate in round 2.

## 8. Open questions (deeper than §5 — really requires more lab data)

1. **Coverage measurement.** How do we know Layer B's fixtures
   actually exercise the audit-relevant code paths? Coverage tools
   like `coverage.py` give line coverage; we want "audit-finding
   coverage" — what fraction of the static-A findings get Layer B
   confirmation? Round 1 can baseline this but not solve it.
2. **Drift between fixture data and real cohort.** A fixture that
   passes Layer B today might fail when run on next quarter's
   cohort. Versioning of fixtures + the trace artifacts is its own
   design problem. casetrack-style provenance possibly composes here
   (the `.fixture_version` field on the trace).
3. **The "stochastic but deterministic-on-fixture" problem.** Some
   scripts have legitimate non-determinism (Monte Carlo sims with no
   fixed seed). Layer B must distinguish "intentional non-determinism"
   from "missing-seed bug" — and CLAUDE.md's "always set seed 42"
   rule helps but isn't universal.
4. **Layer B for `pair_unit` scripts.** Round 1 of Layer A already
   handles R analysis + bash launcher pairs. Layer B's equivalent
   means running the launcher (which sets vars) in the sandbox; then
   tracing the launched R/Py script. Round 1 of Layer B might
   defer pair-unit support to round 2.
5. **Distributed execution.** Scripts that submit downstream SLURM
   jobs (the lab's `submit_*.sh` pattern). The trace can record
   the *intent to submit*, but the downstream job runs outside the
   sandbox. Round 1 should record the intent as a NOTE; round 2 can
   trace the downstream job if it's also fixture-able.

## 9. Composition with ROADMAP #3 (workflow audit)

The two layers compose tightly:

| Capability | ROADMAP #3 round 1 (static) | Layer B round 1 |
|---|---|---|
| Cross-rule schema check | NOTE fallback when cols unresolvable | BLOCKER / PASS via traced col list |
| Wildcard expansion | Rule-template validation only | Verified via traced producer→consumer match |
| Genome-build drift | Static YAML lookup | Verified via traced reference paths |
| Inline-shell rules | NOTE blind edge | Traced through sandbox if shell command is Pythonisable; still NOTE otherwise |

The data-model refactor cost between #3 and Layer B is zero — both
layers enrich the same per-script YAML schema. Layer B fields
(`resolved_by`, `trace_site`) extend the schema; no field semantics
change.

**Execution ordering**: Layer B *follows* the workflow audit in any
realistic deployment. The workflow audit produces the rule list +
dependency graph; Layer B traces each rule's script. A Layer B
cohort run on a 30-rule pipeline is 30 sandbox invocations driven
by the WorkflowIndex from ROADMAP #3.

This is why I argued for ROADMAP #3 round 1 before Layer B round 1:
the workflow auditor's WorkflowIndex is Layer B's dispatch loop. We
ship one, the other becomes much easier.

## 10b. Validation against a real lab artifact (calibration data)

The SU2C coverage-QC archive at
`/data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/results/archived/coverage_qc_cohort/`
is a natural Layer B fixture: it contains the cohort-level outputs
(`cohort_qc_summary.tsv` 190×20; `qc_traceback_report.tsv` 190×15)
plus runtime logs from a production analysis. Probing the producer
scripts at `data/src/build_qc_report.py` and
`data/src/trace_qc_inputs_and_plot.py` gives concrete Layer A → B
gap numbers:

| Script | Output | Layer A cols inferred | Reality | Path template | Path resolved |
|---|---|---|---|---|---|
| `build_qc_report.py` | `cohort_qc_summary.tsv` | None | 20 cols | `{args.output}` | unresolved |
| `trace_qc_inputs_and_plot.py` | `qc_traceback_report.tsv` | None | 15 cols | `{out_tsv}` | unresolved |

**Resolution rate: 0/35 cols (0%) on two real audit-critical scripts.**
Both scripts build their output dataframes via `pd.DataFrame(rows)`
where `rows` is a list-of-dicts assembled inside a loop — the exact
pattern Layer A's `_columns_from_df_call` heuristic cannot resolve
statically. Layer B B1 would close this from runtime data; B3 would
resolve the `{args.output}` / `{out_tsv}` path templates to concrete
paths against any given fixture.

**Qualitative finding**: `trace_qc_inputs_and_plot.py` is itself a
*hand-rolled Layer B trace*. Its `trace_one(sample, bam_path,
provenance, qc_dir)` function performs the contracts Layer B
automates: file-existence checks (B5), byte-size capture (B3),
provenance string consistency (cross-cohort version of B5), and
re-parse-and-cross-check against the cohort summary's numbers (B2).
The 190×15 output schema is essentially a per-sample trace artifact
with one row per audited sample. The lab has already built the
pattern by hand for the one analysis where it mattered most —
generalising it across every audited script is exactly Layer B's
job.

**Implications for the round-1 plan (when 09 promotes to 10)**:

1. **Fixture validation**: the `archived/coverage_qc_cohort/` outputs
   are the ground-truth answer key. Round 1 of Layer B should
   reproduce the 20-col / 15-col schemas from the two producer
   scripts on a sliced fixture, and the regression test for round 1
   is "Layer B traces match the archive's TSV columns exactly."
2. **Trace artifact shape**: `qc_traceback_report.tsv` is a working
   template for what Layer B's per-script trace should look like.
   The artifact format proposal in §4 (JSON Lines events) should be
   re-evaluated against the lab's actual hand-rolled flat-TSV-per-
   sample shape — flat TSV may be friendlier for downstream R/Py
   inspection than JSONL.
3. **Resource budget**: the SU2C archive ran on 189 samples; a
   round-1 Layer B execution on a 5-sample fixture should be ≤ 1/30
   of the wall time, which the archive's `logs/mosdepth/<sample>.log`
   timing data can calibrate.


## 10. Calibration: how much do we trust Layer B?

The high-stakes lens says: **trust is earned per-finding, per-script,
per-fixture**. A Layer B BLOCKER on script X with fixture Y is only
as trustworthy as fixture Y's coverage of script X's behavior. The
audit must be honest about this:

- Every Layer B finding carries a `fixture_id` field.
- Every Layer B finding carries a `coverage_estimate` (lines hit /
  lines total) — initial proxy until "audit-finding coverage" exists.
- Layer B's headline grade is REPORTED SEPARATELY from Layer A's, not
  merged. A user reading the audit sees "Layer A: B" and "Layer B: A
  (fixture coverage 67%)" — they can weigh both.
- "Layer B disagrees with Layer A" gets its own rule
  (`layer-disagreement`): Layer A inferred col list `[a, b, c]`,
  Layer B traced `[a, b, c, d]`. Either the static inference was
  incomplete OR the fixture exercises an extra branch. Both are
  audit-relevant.

This calibration discipline is what separates Layer B from "just run
the script and trust the result" — the latter is a recipe for
silent FN.
