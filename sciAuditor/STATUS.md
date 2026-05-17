# sciAuditor — STATUS

Snapshot of where the framework is. Updated per work round so a new
session can pick up without re-reading the full design docs.

**Last update**: 2026-05-17 · ROADMAP #1 rounds 1 + 2 (casetrack integration)
shipped on `claude/scientific-auditor-framework-wkKAi`.

## What works end-to-end

| Capability | Files |
|---|---|
| v0.2 inferred YAML for R analyses | `parser_r/sciauditor_r.R` |
| v0.2 inferred YAML for Python analyses | `parser_py/sciauditor_py.py` |
| v0.2 inferred YAML for bash launchers | `parser_bash/sciauditor_bash.py` |
| `pair_unit` composition (R analysis + bash launcher) | parser_r `--pair_launcher` |
| Scored audit report (`audit_report.md`) | all 3 parsers + aggregator |
| Machine-readable findings (`audit_findings.tsv`) | all 3 parsers + aggregator |
| Multi-script cohort aggregation | `aggregator/sciauditor_aggregate.py` |
| CI gate (`--fail-on BLOCKER\|WARNING\|NOTE`) | aggregator |
| Parallel per-script audit (`--jobs N`) | aggregator |
| `--include` / `--ignore` glob filters | aggregator |
| **casetrack integration** (`--casetrack-project DIR` on aggregator) | `aggregator/casetrack_check.py` + parser_{bash,py,r} extractor |
| **per-script report regen** after casetrack findings appended | `aggregator/sciauditor_aggregate.py::regenerate_findings_section` |
| **feature-aware rule dispatch** (`feature_supported(index, name)`) | `aggregator/casetrack_check.py` |

## Schema state

Schema v0.2 is locked in `02_inference_design.md` §4. 27 top-level
fields. Three required positive findings (`logging-dual-capture`,
`alignment-guard-before-DDS`, `seed-coverage`) and eight rules
across BLOCKER / WARNING / NOTE severity. Do not invent new schema
fields without updating doc 02.

## Compliance check inventory (Layer A)

| Severity | Rule | R | Py | Bash |
|---|---|:-:|:-:|:-:|
| BLOCKER | `raw-data-write` | ✓ | ✓ | ✓ |
| BLOCKER | `header-preserved` | ✓ | ✓ | n/a |
| BLOCKER | `hardcoded-contig` | ✓ | ✓ | ✓ |
| WARNING | `relative-paths-only` | ✓ | ✓ | ✓ |
| WARNING | `forbidden-variable-names` | ✓ | ✓ | ✓ |
| WARNING | `seed-coverage` | ✓ | ✓ | n/a |
| WARNING | `genome-build-tag` | ✓ | ✓ | ✓ |
| NOTE | `logging-dual-capture` | ✓ | ✓ | ✓ |
| NOTE | `script-header-metadata` | ✓ | ✓ | ✓ |
| NOTE | `set-strict-mode` | n/a | n/a | ✓ |
| NOTE | `seed-policy` (auto, non-default seed) | ✓ | ✓ | n/a |
| NOTE | `pair-binding-coverage` (auto) | ✓ | n/a | n/a |

## Casetrack-integration rules (ROADMAP #1 rounds 1 + 2, ships 2026-05-17)

Fires only when the aggregator is invoked with `--casetrack-project DIR`.
Findings are computed by `aggregator/casetrack_check.py` and appended
to each per-script `audit_findings.tsv` before severity counts roll
up. Parsers (bash + Python + R) extract `casetrack_appends[]` into the
inferred YAML. R was added in round 2; the raw-source regex shape is
symmetric across all three.

| Severity | Rule | Status |
|---|---|---|
| BLOCKER | `casetrack-fk-mismatch` (summary TSV col 1 ≠ level key) | **Shipped, firing** when cols resolvable; **NOTE-fallback** when cols can't be statically inferred |
| WARNING | `casetrack-filename-mismatch` (`--results` basename ≠ declared `summary_tsv`) | **Shipped, firing** |
| WARNING | `casetrack-prefix-collision` (`<prefix>_<col>` collides with declared level col) | **Shipped, firing** when cols resolvable |
| WARNING | `casetrack-results-drift` (disk md5 ≠ `provenance.jsonl` `results_checksum`) | **Shipped, firing** |
| WARNING | `casetrack-untracked-output` (script writes a declared summary TSV but never calls `casetrack append`) | **Shipped, firing** (new in round 2) |
| NOTE    | `casetrack-results-missing` (`--results` not on disk but registered) | **Shipped, firing** |
| NOTE    | `casetrack-orphan-analysis` (`--analysis X` not declared, not registered) | **Shipped, firing** |

**Activation mechanism (round 2):** parsers now emit `outputs[].written_by`
linking each write call to the dataframe id that fed it (receiver heuristic
+ nearest-preceding-line fallback). `dataframes[].columns` are populated
where statically inferable (`pd.DataFrame({...})`, `data.frame(a=..., b=...)`,
`pd.read_csv(usecols=[...])`, `tibble(...)`). `resolve_results_cols()` then
walks output → dataframe → columns to give `casetrack-fk-mismatch` and
`casetrack-prefix-collision` real signal; when the chain doesn't resolve
(dynamically-built dataframes), `casetrack-fk-mismatch` degrades to NOTE
("couldn't infer") rather than silent skip.

**Feature dispatch (round 2 §1 correction):** rule gating now uses
`feature_supported(index, name)` rather than `schema_v`. The TOML section
presence (`[qc]`, `[layout]`, `[project].project_id`, per-level
`id_pattern`) is the real signal for what casetrack features the project
declares; `schema_v` is just a per-project revision counter that bumps on
every `schema apply`. No currently-shipped rule gates yet, but future
v0.6+ id-pattern validation will gate on `feature_supported(index, "id_pattern")`.

**Per-script report regen (round 2 Item 4):** after the aggregator appends
casetrack findings to each per-script `audit_findings.tsv`, it rewrites
the report's `## Findings` section in place using
`regenerate_findings_section()`. Headline / By category / Inventory stay
parser-owned (they're driven by `compliance_checks` and inferred structure,
unaffected by appended casetrack rules).

**Verified against real cohorts:**
- `casetrack_su2c_git` (schema_v=1, features=layout,project_id,qc): 1 declared analysis, 176 latest appends — index loads cleanly.
- `project_17424` (schema_v=3, features=layout,project_id,qc): 8 declared analyses, 76 latest appends — index loads cleanly. Real example scripts (`flagstat` / `modkit_methylation` / `sniffles`) correctly flagged as orphan-analysis vs. declared (`samtools_flagstat` / `modkit_pileup` / `sniffles2`). Validation/ aggregator regression: 4 bash launchers, BLOCKER=0 WARNING=4 NOTE=4 OK=20 across rounds 1 and 2 (unchanged — those launchers don't compose summary TSVs directly so the new rules don't fire on them).
- Synthetic Python suite verifies all four round-2 paths: fk-mismatch BLOCKER (col1=wrong), fk-mismatch NOTE (cols-unresolvable), prefix-collision gate, untracked-output WARNING (writes summary, no append).

## Validated fixtures

See `~/.claude/.../memory/reference_sciauditor_fixtures.md` for the
full list. Headline results:

- `00_build_cohort_wide.R` — C grade (5/7), exact line numbers
  match `03_phase0_target_yaml.md` §"YAML 1".
- `manually_run_DeSeq2.R` + `run_manually_run_DeSeq2.sh` (pair) —
  6/9 D, 5 models, 12 stochastic ops, all 12 PMIDs harvested
  correctly. See `04_realcase_DESeq2_addendum.md`.
- `30_plotly_html.R` — F grade (4/7), fires 2 BLOCKERs at L396 / L398.
- `30_anchor_check_methylation.py` — A grade (7/7).
- `aggregate_DNAme_across_regions.py` — C grade (5/7), real
  forbidden-variable-names hit at L146.
- `04_clock_and_eaa.py` (ElasticNetCV) — B grade (6/7), 2 sklearn
  models + 6 dataframes.
- **Cohort: `coding_peptides_DNAme/scripts/`** — 52 files, 35
  audited, 0 parser errors, ~12s wall at `--jobs 8`. Distribution:
  A=4 B=18 C=4 D=1 F=8. 8 BLOCKER / 33 WARNING / 31 NOTE / 191 OK.

## How to run

```bash
# Single script — R
/home/ahunos/miniforge3/envs/r-env/bin/Rscript parser_r/sciauditor_r.R \
    --input <script.R> --output <out.yaml> --report_dir <out.audit/>

# Single script — Python (3.7+)
/home/ahunos/miniforge3/envs/snakemake/bin/python3 parser_py/sciauditor_py.py \
    --input <script.py> --output <out.yaml> --report_dir <out.audit/>

# Single script — bash
/home/ahunos/miniforge3/envs/snakemake/bin/python3 parser_bash/sciauditor_bash.py \
    --input <script.sh> --output <out.yaml> --report_dir <out.audit/>

# R analysis + bash launcher pair
/home/ahunos/miniforge3/envs/r-env/bin/Rscript parser_r/sciauditor_r.R \
    --input <analysis.R> --pair_launcher <launcher.sh> \
    --output <out.yaml> --report_dir <out.audit/>

# Whole project (cohort)
/home/ahunos/miniforge3/envs/snakemake/bin/python3 aggregator/sciauditor_aggregate.py \
    --project-dir <project/scripts> --output-dir <cohort_out> \
    --jobs 8 --fail-on BLOCKER \
    --ignore 'archived' --ignore 'submit_*.sh'

# Whole project + casetrack rules
/home/ahunos/miniforge3/envs/snakemake/bin/python3 aggregator/sciauditor_aggregate.py \
    --project-dir <project/scripts> --output-dir <cohort_out> \
    --casetrack-project /data1/.../casetrack_cohort/ \
    --jobs 8 --fail-on BLOCKER
```

## Next round (ROADMAP #3)

Workflow-level DAG audit. Brainstorm + plan committed:
- `07_workflow_dag_audit_brainstorm.md` — alternatives considered + open questions
- `08_workflow_dag_audit_plan.md` — locked decisions for round 1 (Snakemake-only, D2 topology + D1 schema contracts; MVP fixture = CCV-neoquality-pipeline Snakefile; ≥ 1 real finding = acceptance)

Total round-1 budget per the plan: ~760 lines + verification, split
across 5 work items. Order: snakemake_loader → workflow_check (D2,
then D1) → per-rule dispatch → report+TSV → CLI+demo.

## Round-after-next (ROADMAP #2 — Layer B)

Runtime trace layer. Brainstorm committed:
- `09_layer_b_runtime_trace_brainstorm.md` — 7 contracts (B1–B7), 3
  big execution-model questions (E1/E2/E3 tracer; F1/F2/F3 fixture;
  S1/S2/S3 sandbox), calibration discipline (per-fixture trust),
  composition story with ROADMAP #3.

Several §5 decisions deliberately OPEN at the brainstorm — needs
another conversation round to lock before promotion to plan. Notable
opens: Q4 trust model (default-off opt-in); Q2 fixture format (in-
script comment vs companion file vs casetrack-pool); E1 vs E2 vs E3
tracer mechanism. Layer B execution naturally *follows* ROADMAP #3
in deployment (workflow audit produces the WorkflowIndex; Layer B
traces each rule's script via that index).

## What's open

See `ROADMAP.md`.
