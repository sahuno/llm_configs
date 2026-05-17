# sciAuditor — Workflow DAG Audit Brainstorm (ROADMAP #3)

> Brainstorm doc for elevating sciAuditor from a per-script linter to a
> workflow-level static analyzer. Cross-references
> [`02_inference_design.md`](02_inference_design.md) §4 (the per-script
> YAML schema this audit consumes) and
> [`05_casetrack_integration_plan.md`](05_casetrack_integration_plan.md)
> §1 (the "three contracts" framing reused below).
>
> Status: pre-plan. Once the §3 decisions land, this becomes
> `08_workflow_dag_audit_plan.md` and round 1 ships.

## 0. Why elevate to the workflow level

The per-script audit catches drift within one file. The drift sciAuditor
*can't* see today, and that bites in real lab work, lives between rules:

- **Schema drift across rule boundaries.** Rule A writes a TSV with
  cols `[sample_id, depth_mean, depth_median]`. Rule B reads that TSV
  expecting `depth_median_50bp`. Today the failure surfaces at runtime
  (Python KeyError, R `NAs introduced by coercion`), often after hours
  of compute. The per-script YAMLs from rounds 1+2 already carry
  `dataframes[].columns` and `outputs[].written_by` — the data needed
  to catch this statically across rules.
- **Genome-build drift across rules.** Rule A aligns to hg38; rule B
  intersects with an mm10 BED that was accidentally pointed at by a
  config var. Per-script audit catches missing genome tags within one
  file; can't catch divergence between rules.
- **Container / conda-env drift.** Rule A uses `samtools:1.18`; rule B
  uses `samtools:1.10`. Same tool, different version, silent
  divergence in output formats / flag semantics.
- **Topology breakage.** Orphan rules (declared, never used as input by
  any other rule — usually a typo); dangling inputs (referenced but
  never produced — DAG-build failure at runtime).
- **Cohort-level casetrack coverage.** The current `--casetrack-project`
  flag audits per-script registration. The workflow-level question
  ("which rules are tracked in casetrack and which aren't") is invisible.

These are workflow-level invariants. The per-script YAMLs are already
the right substrate; what's missing is the DAG to walk and the rules to
fire across rule boundaries.

## 1. The contracts (what the workflow auditor can check)

Same framing as `05_casetrack_integration_plan.md` §1: split into
discrete contracts, ship one round per contract.

### D1. Output → downstream input *schema* consistency
For every edge `(rule_A → rule_B)` in the DAG where rule A's output file
is rule B's input file:
- Look up rule A's per-script YAML → find the matching output → walk
  `written_by` → dataframe → `columns`. (Round 1+2 already wires this.)
- Look up rule B's per-script YAML → find the matching input → if it
  reads with `usecols=[...]` (Py) / `col.names=c(...)` (R), or accesses
  named columns later in the script (`df["depth_median_50bp"]`), recover
  the expected col list.
- Diff. Cols in B's expectation not in A's output → `workflow-schema-drop`
  (BLOCKER, runtime KeyError).

Highest leverage — the per-script YAMLs we already produce *do* carry
this signal; only the DAG-walking glue is new.

### D2. DAG topology coherence
- **Orphan rule**: declared but never referenced as input by any other
  rule, AND not in the `rule all:` target set. NOTE.
- **Dangling input**: referenced as input by some rule but not produced
  by any other rule AND not declared in the workflow's `input:` /
  `raw_paths:` set. BLOCKER (Snakemake `MissingInputException`).
- **Unreachable rule**: present in the rule list but no path from
  `rule all` reaches it. NOTE.

Pure topology — no per-script audit needed. Free signal.

### D3. Cross-rule consistency of shared assumptions
- **`workflow-genome-drift`** (BLOCKER): two rules declare different
  `genome_build_declared` in their YAMLs.
- **`workflow-container-drift`** (WARNING): two rules invoking the same
  tool name (extracted from `external_binaries[]`) reference different
  container images / conda envs.
- **`workflow-seed-divergence`** (WARNING): stochastic rules use
  different `set.seed()` / `np.random.seed()` values when there's no
  declared reason (multi-seed sweeps are legitimate; flag once and
  let the user `--ignore` the rule if intentional).
- **`workflow-uneven-logging`** (NOTE): some rules have
  `logging-dual-capture: pass`, others fail. Inconsistent within one
  workflow is usually a regression, not a deliberate choice.

### D4. Path-template / wildcard / channel-shape agreement
Snakemake-specific:
- Wildcard set in rule A's `output:` must be a superset of (or equal
  to) the wildcards rule B's `input:` references for that file.
- `{sample}` in rule A's output but rule B reads the file without
  `{sample}` → wildcard mismatch at DAG-build time.

Nextflow-specific:
- `process A` emits `tuple val(meta), path(bam)`. `process B` expects
  `tuple val(meta), path(bam), path(bai)`. Channel shape mismatch.
- The meta map's *keys* must agree across consumer/producer (e.g.,
  rule A puts `meta.run_tag` into the map; rule B reads `meta.runtag`
  — silent NA in the downstream Groovy).

Hardest to do statically. Defer to round 3+ within ROADMAP #3.

### D5. Workflow-level resource & reproducibility audit
- Cumulative wall-time estimate from per-rule benchmarks (if `benchmark:`
  blocks present).
- Memory peak across the DAG (no rule allocates more than the partition
  ceiling).
- Container/conda pinning: every rule uses an explicit version, no
  floating `:latest` tags.
- Every rule's stdout/stderr is captured to `logs/{rule}/{wildcards}.log`.

Defer to round 4. Lower leverage; semi-redundant with the
`runtime-resource-study` skill that already covers per-tool resource
characterisation.

### D6. Workflow-casetrack cohort coverage
For projects that pass both `--workflow-file` and `--casetrack-project`:
- Every rule that produces a summary-TSV-shaped output should have an
  outgoing edge into a rule that calls `casetrack append` (the
  nf-subworkflow's CASETRACK_REGISTER process, in the user's lab).
- Conversely, every declared `[analyses.X]` in the TOML should have at
  least one workflow rule that writes its `summary_tsv`.

Bridges ROADMAP #1 (casetrack) and #3 (DAG). Defer to round 2 within
ROADMAP #3 — needs D1 + D2 first.

## 2. Phasing (one round each)

| Round | Ships | Why this order |
|---|---|---|
| **1** | D2 (topology) + D1 (output→input schema) | Topology is free signal (no per-script audit dependency); schema-drift exercises the per-script YAML infra we just hardened. Together they catch the two most common DAG-time runtime failures. |
| **2** | D3 (cross-rule consistency) + D6 (workflow ↔ casetrack coverage) | Builds on the DAG-walking machinery from round 1. D6 is the natural bridge between #1 and #3. |
| **3** | D4 (wildcard / channel shape) | Hardest — needs DSL-aware expansion. Lands after we know what the real false-positive rate looks like on rounds 1+2. |
| **(out of round-3 scope)** | D5 (workflow-level resource + reproducibility audit) | Defer; semi-redundant with `runtime-resource-study` skill. |

## 3. Architecture: how to *get* the DAG

Two options. Pick one for round 1.

### Option A: Parse the DSL directly
- **Snakemake**: import `snakemake.parser` / `snakemake.workflow`,
  hand it the Snakefile, walk the workflow object. Snakemake's own
  Python API surface. Brittle across snakemake major versions.
- **Nextflow**: would need Groovy AST tools (e.g., the
  [nextflow-language-server](https://github.com/nextflow-io/language-server)).
  Significant work just to load the AST.

Pro: full fidelity, no subprocess. Con: tightly coupled to the workflow
engine's internal API surface; breaks on engine upgrades.

### Option B (recommended): Bootstrap from the engine's introspection commands

The engines already know their own DAG; we just need to ask.

- **Snakemake** — verified usable surface:
    - `snakemake --rulegraph --dag mermaid-js` → DOT or mermaid graph of rule dependencies.
    - `snakemake --summary` / `--detailed-summary` → TSV: one row per
      output file with the rule that produces it, the input files,
      timestamps, etc.
    - `snakemake --list-input-changes` / `--list-changes input` → which
      input files have changed since last run (useful for incremental audit).
    - `snakemake --dry-run --printshellcmds` → which rules would run
      and the shell command for each (gives us the script path to
      hand off to the per-script parser).
    - `snakemake --list-rules` → rule names.
    - `snakemake --notemp -np` → resolved output paths after wildcard
      expansion.

- **Nextflow** — verified usable surface:
    - `nextflow inspect <pipeline> -profile X -format json` →
      structured JSON description of all processes and configs.
    - `nextflow run <pipeline> -with-dag dag.html` → renders the DAG
      (but requires running the pipeline).
    - `.nextflow/cache/<run>/...` → cached resolution artifacts.
    - **Best entry point**: parse the channel `take:` / `emit:` blocks
      of subworkflows + the `script:` blocks of processes from the
      `.nf` files directly. The standard pattern in nf-core modules is
      structured enough to regex-extract.

Recommendation: **Option B**. Subprocess out to the engine for DAG
extraction; only fall back to DSL parsing for fields the engine doesn't
surface (like the rule's `script:` path → for which `--summary` works
in snakemake, and the `script:` block of `.nf` files needs a small
regex extractor for nextflow).

**For nf-core specifically**: the [`meta.yml`](https://nf-co.re/docs/contributing/modules)
file ships alongside every nf-core module and declares typed inputs and
outputs *in the same shape* as our per-script YAML's `inputs[]` /
`outputs[]`. This is a free, ground-truth schema. Round-1 should
detect nf-core modules and short-circuit to `meta.yml` instead of
running the per-script audit on `main.nf`.

## 3.5. The shared rule index, not per-engine

Same pattern as the casetrack architecture (`aggregator/casetrack_check.py`):

```
sciAuditor/aggregator/
    workflow_check.py        # NEW — shared workflow-rule index + checkers
    workflow_loaders/
        snakemake_loader.py  # NEW — subprocess to snakemake --summary etc.
        nextflow_loader.py   # NEW — parses .nf files + nf-core meta.yml
```

`workflow_check.py` exports:
```python
@dataclass
class WorkflowRule:
    name: str                   # rule name in Snakemake / process name in nextflow
    engine: str                 # "snakemake" | "nextflow"
    script_path: Path | None    # the analysis script for this rule, if any
    inferred_yaml: dict | None  # cached per-script audit output
    inputs:  list[str]          # resolved input paths (or path templates with wildcards)
    outputs: list[str]          # same
    edges_in:  list[str]        # rule names that produce this rule's inputs
    edges_out: list[str]        # rule names that consume this rule's outputs
    declared_genome: str | None
    declared_container: str | None
    wildcards: set[str]
    meta_yml_inputs:  list[dict] | None   # nf-core only
    meta_yml_outputs: list[dict] | None   # nf-core only

@dataclass
class WorkflowIndex:
    engine: str
    workflow_file: Path
    rules: dict[str, WorkflowRule]
    edges: list[tuple[str, str, str]]   # (upstream_rule, downstream_rule, shared_path)

def load_workflow(workflow_file: Path, engine: str = "auto") -> WorkflowIndex:
    ...

def check_workflow(index: WorkflowIndex) -> list[Finding]:
    ...
```

Findings flow through the same per-script `audit_findings.tsv` model
the cohort aggregator already uses — appended to the rule's per-script
TSV when the finding is rule-attributable, or to a new
`workflow_findings.tsv` when it's a DAG-level (multi-rule) finding.

## 4. CLI surface

Two options for the CLI:

### Option α: Augment `sciauditor_aggregate.py` with `--workflow-file`
```
sciauditor_aggregate.py \
    --project-dir <scripts/> \
    --workflow-file <Snakefile|main.nf> \   # NEW
    --workflow-engine snakemake|nextflow|auto \   # NEW
    --casetrack-project <cohort/> \
    --output-dir <out/>
```
Pro: single CLI surface, single output directory. Con: blurs the
distinction between "audit my script bag" and "audit my pipeline".

### Option β (recommended): New top-level `sciauditor_workflow.py`
```
sciauditor_workflow.py \
    --workflow-file <Snakefile|main.nf> \
    --workflow-engine snakemake|nextflow|auto \
    --casetrack-project <cohort/> \   # optional, enables D6
    --output-dir <out/> \
    --jobs 8 --fail-on BLOCKER
```
Internally calls `sciauditor_aggregate.py` (or the same per-script
parsers it dispatches to) for each rule's script. Cohort report is
produced *alongside* a workflow report (`workflow_audit_report.md`)
that shows the DAG annotated with findings.

Recommendation: Option β. Cleaner separation of concerns; the cohort
auditor stays the right tool for "I have a folder of scripts and want
to lint them all". The workflow auditor is a distinct higher-level tool.

## 5. Decisions to make before round 1 starts

### Q1 — Engine support order: **Snakemake first, Nextflow second**
The lab uses both, but snakemake's introspection surface (`--summary`,
`--dry-run --printshellcmds`, `--rulegraph`) is mature and Python-
accessible. Nextflow's `inspect` command is younger and less stable.
Snakemake-first lets round 1 ship faster; round 2 adds Nextflow once
the rule-index abstraction is proven.

### Q2 — DAG extraction: **subprocess `snakemake --summary` + `--rulegraph`, not import**
Importing snakemake's Python API into our aggregator couples us to
snakemake's internal surface — that breaks every major version. A
subprocess call to a stable CLI flag is more durable. Cost: one
subprocess invocation per workflow load.

### Q3 — Rules with no external script (`shell:` only): **audit topology, skip per-script**
Many rules in real lab Snakefiles are inline shell:
```
rule samtools_sort:
    input:  "{sample}.bam"
    output: "{sample}.sorted.bam"
    shell:  "samtools sort -@ {threads} -o {output} {input}"
```
No analysis script to audit per-script. Topology checks (D2) still
fire; schema checks (D1) can't. Round 1 should emit a NOTE for
inline-shell rules that produce a TSV-shaped output (so the user knows
the audit's blind on that edge).

### Q4 — Snakemake `include:` and Nextflow subworkflows: **fully expand the DAG before audit**
A workflow that includes 4 sub-Snakefiles should be audited as one DAG,
not 4. `snakemake --rulegraph` already expands includes; we just need
to use its output. Nextflow subworkflows similarly: walk includes in
`.nf` files until the leaves.

### Q5 — Wildcard expansion: **rule-template validation in round 1, expanded-DAG validation in round 2**
Rule-template validation catches typos in static paths (`coverage.tvs`
vs declared `coverage.tsv`). Expanded-DAG validation catches actual
mismatches when wildcards resolve (e.g., a sample-sheet entry missing
the column expected by rule B). Two different bugs; two different
rounds.

### Q6 — nf-core `meta.yml`: **use as schema ground truth, short-circuit per-script audit**
When a rule points at a `main.nf` that has an adjacent `meta.yml`,
read meta.yml's `input:` / `output:` blocks directly into the
`WorkflowRule.meta_yml_inputs/outputs` fields. Skip the per-script audit
of `main.nf` (it would re-derive the same info less accurately).
**This is the single biggest accuracy boost in this audit.** nf-core's
meta.yml is hand-authored and typed; per-script inference is
necessarily lossy.

### Q7 — Output: **annotate the existing rulegraph dot, plus a workflow_findings.tsv**
The DAG visualisation already exists (snakemake `--rulegraph`,
nextflow `-with-dag`). Round 1 should *annotate* it with finding
counts per rule and per edge, not replace it. Visually:

```
rule samtools_sort  [B0 W0 N0 OK]
    │
    │  ⚠ workflow-schema-drop: rule produces 'specimen_id' col,
    │     downstream rule expects 'sample_id'
    ▼
rule modkit_pileup  [B1 W0 N1 OK]
```

A `workflow_findings.tsv` complements the cohort `audit_findings.tsv`
with rule-pair and DAG-level findings.

### Q8 — Severity ladder for round-1 rules

| Rule ID | Severity | Reason |
|---|---|---|
| `workflow-orphan-rule` | NOTE | Could be target rule, could be typo; flag don't block |
| `workflow-dangling-input` | BLOCKER | Runtime `MissingInputException` certainty |
| `workflow-schema-drop` (B reads a col A doesn't produce) | BLOCKER | Runtime KeyError certainty |
| `workflow-schema-extra` (A produces cols B doesn't read) | NOTE | Wasteful but not a bug |
| `workflow-genome-drift` (round 2) | BLOCKER | Silent corruption |
| `workflow-container-drift` (round 2) | WARNING | Non-deterministic; common in legacy pipelines |

Don't soften BLOCKERs for legacy workflows — the aggregator's
`--ignore` is the right escape hatch for known-bad subtrees (same
principle as casetrack §4 Q2).

### Q9 — Snakemake config + Nextflow params threading
Per-script parsers see variable assignments but not workflow-level
config (`configfile: "config/config.yaml"` in Snakemake, `params.*`
in Nextflow). For D3 genome-build drift to work, the auditor needs
to resolve config var references.

Recommendation: pre-pass that materialises config into a `dict`,
exposed to the per-script parsers via a new `--workflow-params <json>`
flag. Parsers consume it the way they currently consume `--pair_launcher`
data.

### Q10 — Re-parse caching
Re-running parser_py on every rule's script every audit cycle is
wasteful for large workflows (50+ rules). Cache by
`(script_path, mtime, parser_version)` → inferred YAML location.
Defer cache invalidation to round 2 polish; round 1 always re-parses.

## 6. First MVP target

End-to-end on one real lab pipeline:
`/data1/greenbab/users/ahunos/projects/CCV-neoquality-pipeline/wf_snakemake/workflow/Snakefile`

Concrete deliverable for round-1 demo:
1. `sciauditor_workflow.py --workflow-file <Snakefile>` loads the rule
   graph via `snakemake --summary` + `--rulegraph`.
2. Builds `WorkflowIndex` with N rules + M edges.
3. For each rule with a `script:` directive, runs the existing
   per-script parser, caches the YAML.
4. Runs D2 (topology) checks: orphan rules, dangling inputs.
5. Runs D1 (schema) checks across every edge: walk producer YAML's
   `outputs[].written_by.dataframes[].columns`, walk consumer YAML's
   `inputs[]` + col-usage references, diff.
6. Emits `workflow_audit_report.md` with:
   - Rule list + per-rule audit grade
   - Annotated DAG (mermaid block in markdown)
   - DAG-level findings table
7. Aggregator regression: cohort-level audit on the same project still
   passes; new tool doesn't break the existing surface.

Acceptance: at least ONE real finding fires on a real lab pipeline.
If we can't find one, we're not testing the right pipelines.

## 7. Out of scope (round-3 series, even at the ambitious level)

- **Snakemake checkpoints** — re-evaluation of the DAG after a
  checkpoint run is dynamic; falls into Layer B territory.
- **Nextflow channel operators** (`combine`, `groupTuple`, `mix`) —
  full channel-algebra parsing is its own multi-quarter project.
- **Conditional rules** (Snakemake `if rule_x_enabled:` blocks) —
  partial; round 4.
- **Workflow-level resource budgeting** (D5) — semi-redundant with
  `runtime-resource-study` skill.
- **Workflow versioning audit** ("did the pipeline diff since last
  cohort run?") — out of audit scope, belongs in CI.

## 8. Open questions

1. **Nextflow's `inspect` JSON format stability.** Need a small probe
   on the real `casetrack-nf-subworkflows/main.nf` to confirm the
   inspect output is parseable across nextflow versions. Pre-round-1
   investigation, ~30 min.
2. **Caching collisions across multiple cohort runs.** If two cohorts
   audit the same Snakefile with different configs, the per-script
   YAML cache might collide. Probably keys-include-config-hash.
3. **Auditing `snakemake.shell.shell()` calls.** Rules that invoke
   sub-scripts via the shell directive that themselves do real work
   are a sub-tree of audit. Today's per-script parser handles bash
   launchers; the question is whether the workflow audit should walk
   THOSE bash launchers as separate rule nodes.
4. **What about Snakemake's `wrapper:` directive?** A rule that uses a
   community-maintained wrapper imports an external Python module.
   Auditing wrappers is similar to nf-core meta.yml — they ship
   schemas (`wrappers/<name>/meta.yaml`). Worth one bullet of design
   thought in the round-1 plan.

## 9. Where this connects to Layer B (ROADMAP #2)

The workflow DAG audit is **static-only** by design. Once Layer B
runtime trace ships (ROADMAP #2), the workflow audit gains:
- Real wildcard resolution (no more rule-template-only validation;
  D4 becomes tractable).
- Real schema validation (no more "couldn't infer cols" NOTE; D1's
  BLOCKERs become confident).
- Workflow-level reproducibility audit (D5) can ground against actual
  resource consumption from a tracer-decorated run.

i.e., the workflow audit and Layer B compose: workflow audit shows
*where* in the DAG to instrument; Layer B *instruments* and produces
real traces. Both build on the same per-script YAML schema.

The MVP for ROADMAP #3 makes sense to ship before ROADMAP #2 because:
1. The per-script YAML infra is already production-grade (rounds 1+2 of
   casetrack proved this).
2. Subprocess-based DAG extraction is days, not weeks.
3. Real findings fire on real lab pipelines on day 1 of round 1.
4. ROADMAP #2 has months of sandboxing + fixture work to do first.
