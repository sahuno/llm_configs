# sciAuditor — STATUS

Snapshot of where the framework is. Updated per work round so a new
session can pick up without re-reading the full design docs.

**Last update**: 2026-05-17 · ROADMAP #1 round 1 (casetrack integration)
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
| **casetrack integration** (`--casetrack-project DIR` on aggregator) | `aggregator/casetrack_check.py` + parser_{bash,py} extractor |

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

## Casetrack-integration rules (ROADMAP #1 round 1, ships 2026-05-17)

Fires only when the aggregator is invoked with `--casetrack-project DIR`.
Findings are computed by `aggregator/casetrack_check.py` and appended
to each per-script `audit_findings.tsv` before severity counts roll
up. Parsers (bash + Python) extract `casetrack_appends[]` into the
inferred YAML. **R parser does NOT extract `casetrack_appends[]` yet
— round 2 polish.**

| Severity | Rule | Status |
|---|---|---|
| BLOCKER | `casetrack-fk-mismatch` (summary TSV col 1 ≠ level key) | Shipped, inert (gated on dataframe→TSV col link, round-2 polish) |
| WARNING | `casetrack-filename-mismatch` (`--results` basename ≠ declared `summary_tsv`) | **Shipped, firing** |
| WARNING | `casetrack-prefix-collision` (`<prefix>_<col>` collides with declared level col) | Shipped, inert (gated on same link) |
| WARNING | `casetrack-results-drift` (disk md5 ≠ `provenance.jsonl` `results_checksum`) | **Shipped, firing** |
| NOTE    | `casetrack-results-missing` (`--results` not on disk but registered) | **Shipped, firing** |
| NOTE    | `casetrack-orphan-analysis` (`--analysis X` not declared, not registered) | **Shipped, firing** |

**Verified against real cohorts:**
- `casetrack_su2c_git` (schema_v=1): 1 declared analysis, 176 latest appends — index loads cleanly.
- `project_17424` (schema_v=3): 8 declared analyses, 76 latest appends — index loads cleanly. Real example scripts (`flagstat` / `modkit_methylation` / `sniffles`) correctly flagged as orphan-analysis vs. declared (`samtools_flagstat` / `modkit_pileup` / `sniffles2`).

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

## What's open

See `ROADMAP.md`.
