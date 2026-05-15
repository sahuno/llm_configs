# sciAuditor — Phase 0: Target YAML for three real scripts

> Goal: validate the inferred-output schema from
> `02_inference_design.md` §4 against three real scripts (one per
> language). Each YAML below is what the *finished* auditor should
> produce. They define the regression-test fixture for the parser
> work in Phase 1.
>
> The point of this exercise is **schema discovery**: where the
> §4 draft fits, where it has to bend, and what fields are missing.
> Notes after each YAML capture the schema feedback.

---

## Locked defaults from round 3

- Q1 — inferred drafts in `.audit/<run>/` (gitignored); manifests
  committed after promotion.
- Q2 — head-of-real trace input by default; per-script
  `audit_fixture:` overrides.
- Q5 — cross-script handoffs deferred to a workflow-DAG audit round.

---

## Picks

| Lang   | Script                                                                                          | Why |
|--------|-------------------------------------------------------------------------------------------------|-----|
| R      | `cohort_overview/scripts/00_build_cohort_wide.R`                                                | optparse + `data.table` NSE; two merges with explicit `by=`; column lineage that branches & rejoins; hardcoded sample list. |
| Python | `biotoolsBenchmarks/samtools/sort/src/13_subsample_merged.py`                                   | driver-pattern (Python writes bash → submits SLURM); module-level hardcoded paths; explicit TSV header; seed used. |
| Bash   | `biotoolsBenchmarks/samtools/sort/src/03_run_one.sh`                                            | getopts CLI; explicit 29-column CSV header; flock-protected append; external-binary I/O (`samtools sort`). |

Each picks a different idiom for I/O configuration (optparse
defaults / Python constants / getopts CLI) and a different style of
output-schema declaration (default `fwrite` header / hand-written TSV
header / hand-written CSV header). Together they pressure-test the
schema along the axes that matter.

---

## YAML 1 — R: `00_build_cohort_wide.R`

```yaml
schema_version: 0.1
script:
  path: cohort_overview/scripts/00_build_cohort_wide.R
  language: R
  git_rev: <runtime>
  inferred_at: <runtime>
  layers_used: [static]

config_interface:
  framework: optparse
  options:
    - name: --metadata
      type: character
      default: /data1/greenbab/projects/janjigian_su2c_WGS-ONT_sam/DNAme_prod/scripts/coding_peptides_DNAme/metadata_merged.tsv
      role: input_path
      default_kind: absolute        # → WARNING (rules: warn-absolute-paths)
    - name: --meth_cohort
      type: character
      default: .../Q2exp_apm_burden_all36_tumors.tsv
      role: input_path
      default_kind: absolute        # → WARNING
    - name: --out
      type: character
      default: .../cohort_wide.tsv
      role: output_path
      default_kind: absolute        # → WARNING

inputs:
  - path_template: "{opt.metadata}"
    slot_bindings: { opt.metadata: from --metadata }
    format: tsv
    read_call: { fn: data.table::fread, site: 00_build_cohort_wide.R:24 }
    read_params: { na.strings: ["", "NA"] }
    schema_observed: null   # filled by Layer B
    referenced_columns:
      - patient_id          # join key, used by ~10 expressions
      - sample_type         # filter predicate (== "tumor", == "normal")
      - primary_site_tri
      - molecular_subtype
      - impact_msi
      - tp53_mutated
      - her2_overall
      - responder_status
      - purity.facets
      - purity.savana
      - line1_tpm
      - peptidome_set
      - dmp_sample_id
      - cGAS_mIF
      - ORF1_mIF
  - path_template: "{opt.meth_cohort}"
    slot_bindings: { opt.meth_cohort: from --meth_cohort }
    format: tsv
    read_call: { fn: data.table::fread, site: 00_build_cohort_wide.R:27 }
    referenced_columns: [patient_id]

outputs:
  - path_template: "{opt.out}"
    slot_bindings: { opt.out: from --out }
    format: tsv
    write_call: { fn: data.table::fwrite, site: 00_build_cohort_wide.R:119 }
    write_params: { sep: "\t", col.names: true }   # default; header preserved ✓
    schema_written:
      columns: [patient_id, sample_id, site,
                primary_site, molecular_subtype, MSI, TP53, HER2, Response,
                ONT_WGS, ONT_DNAme, RNA_seq, Immunopeptidomics, IMPACT,
                cGAS_mIF, ORF1_mIF]
      origin: keep_cols vector at 00_build_cohort_wide.R:111

dataframes:
  - id: meta
    origin: 00_build_cohort_wide.R:24
    derived_from: ["{opt.metadata}"]
  - id: meth
    origin: 00_build_cohort_wide.R:27
    derived_from: ["{opt.meth_cohort}"]
  - id: tumor_rows
    origin: 00_build_cohort_wide.R:33
    derived_from: [meta]
    transform: { op: filter, predicate: "sample_type == 'tumor'" }
  - id: tumor_rows_dedup
    origin: 00_build_cohort_wide.R:34
    derived_from: [tumor_rows]
    transform: { op: dedup, key: patient_id }
  - id: patient_level
    origin: 00_build_cohort_wide.R:40
    derived_from: [tumor_rows_dedup]
    transform: { op: select_rename, mapping: { primary_site: primary_site_tri, MSI: impact_msi, TP53: tp53_mutated, HER2: her2_overall, Response: responder_status } }
  - id: tumor_flags
    origin: 00_build_cohort_wide.R:51
    derived_from: [tumor_rows_dedup, meth_pts]
    transform:
      op: mutate
      new_columns: [ONT_WGS_T, ONT_DNAme_T, RNA_seq_T, Immunopeptidomics_T, IMPACT_T, cGAS_mIF_T, ORF1_mIF_T]
      derivation: fifelse on is.na() of source columns
  - id: normal_flags
    origin: 00_build_cohort_wide.R:80
    derived_from: [tumor_rows_dedup.patient_id, wb_measured, wb_meth_pts, normal_pts]
  - id: tumor_out
    origin: 00_build_cohort_wide.R:93
    derived_from: [patient_level, tumor_flags]
    transform: { op: merge, by: patient_id, join_type: inner_explicit }
  - id: wb_out
    origin: 00_build_cohort_wide.R:102
    derived_from: [patient_level, normal_flags]
    transform: { op: merge, by: patient_id, join_type: inner_explicit }
  - id: out
    origin: 00_build_cohort_wide.R:116
    derived_from: [tumor_out, wb_out]
    transform: { op: rbind, axis: rows }

transformations:
  - site: 00_build_cohort_wide.R:33
    op: filter
    predicate: "sample_type == 'tumor'"
  - site: 00_build_cohort_wide.R:34
    op: dedup
    key: patient_id
  - site: 00_build_cohort_wide.R:81
    op: merge
    left: normal_flags, right: wb_measured
    by_columns: [patient_id]
    join_type: left_outer
  - site: 00_build_cohort_wide.R:82-84
    op: na_fill
    columns: [ONT_WGS_N, RNA_seq_N, IMPACT_N, cGAS_mIF_N, ORF1_mIF_N]
    fill_value: "No"

models: []
stochastic_ops: []

hardcoded_data:
  - site: 00_build_cohort_wide.R:66-67
    binding: wb_meth_pts
    kind: sample_id_list
    values: [SU2C-264, SU2C-289, SU2C-320, SU2C-324, SU2C-342, SU2C-353]
    note: hardcoded sample-id list → AUDIT WARNING (looks like data; consider moving to config)

side_effects:
  - site: 00_build_cohort_wide.R:118
    kind: filesystem_mkdir
    path: dirname({opt.out})
    declared_in_outputs: true

environment:
  r_packages: [data.table, optparse]

unresolved: []

audit_findings_preview:
  - severity: WARNING
    rule: warn-absolute-paths
    sites: [00_build_cohort_wide.R:16, :18, :20]
    note: optparse defaults are absolute paths; override-able via CLI but defaults won't run on another machine
  - severity: WARNING
    rule: hardcoded-data-block
    site: 00_build_cohort_wide.R:66-67
    note: wb_meth_pts is a hardcoded sample list; promote to config
  - severity: NOTE
    rule: forbidden-variable-name
    site: 00_build_cohort_wide.R:33
    note: variable "tumor_rows" OK; if had used "results"/"counts"/"conditions" → WARNING
```

### Schema feedback from YAML 1
- Need `config_interface:` block to capture optparse / argparse /
  getopts contracts; not in §4 yet.
- Need `referenced_columns:` per input (Layer A can already infer this
  from `df$col` and `df[, col]` patterns).
- Need `dataframes[].transform` so the lineage graph carries
  human-readable operation semantics, not just edges.
- Need `hardcoded_data:` block — embedded sample lists / contig
  lists / threshold constants are a common audit concern.
- Need `audit_findings_preview:` (static findings can be emitted
  alongside the inferred YAML; finalized in the audit report).

---

## YAML 2 — Python: `13_subsample_merged.py`

```yaml
schema_version: 0.1
script:
  path: biotoolsBenchmarks/samtools/sort/src/13_subsample_merged.py
  language: python
  layers_used: [static]

config_interface:
  framework: module_constants     # no argparse; constants at top of file
  constants:
    - { name: REPO, value: "/data1/.../samtools/sort", kind: absolute_path }
    - { name: INPUT_BAM, value: "/data1/.../p17424_2_tumor_hg38_merged.bam", kind: absolute_path }
    - { name: SAMTOOLS, value: "/home/ahunos/miniforge3/.../samtools", kind: absolute_path }
    - { name: FRACTIONS_PCT, value: [6, 31, 63], kind: list_int }
    - { name: SBATCH_CPUS, value: 8 }
    - { name: SBATCH_MEM, value: "16G" }
    - { name: SBATCH_TIME, value: "00:30:00" }

inputs:
  - path_template: "{INPUT_BAM}"
    slot_bindings: { INPUT_BAM: module constant }
    format: bam
    read_call: null    # not read by this script; passed to spawned bash
    consumed_by: external_binary
    external_binary:
      name: samtools
      site: SBATCH_TEMPLATE:51 (embedded in 13_subsample_merged.py:30-66)
      command: samtools view -b -@ 8 -s "$SEED_FRAC" -o "$OUT" "$INPUT"

outputs:
  - kind: tabular
    path_template: "{REPO}/data/processed/hg38/subsamples_intermediate/record_counts_intermediate.tsv"
    format: tsv
    write_call: { fn: pathlib.Path.write_text, site: 13_subsample_merged.py:84 }
    write_params: { sep: "\t" }
    schema_written:
      columns: [fraction_pct, output_bam, total_records, primary_records, size_bytes]
      origin: literal header at 13_subsample_merged.py:84
    append_pattern:
      mechanism: flock_in_sbatch_template
      site: SBATCH_TEMPLATE:59-63
      concurrency_safe: true
  - kind: bam
    path_template: "{REPO}/data/processed/hg38/subsamples_intermediate/{base}.{frac:03d}pct.bam"
    slot_bindings:
      base: "Path(INPUT_BAM).stem"
      frac: "iter over FRACTIONS_PCT"
    cardinality: 3
    written_by: external_binary (samtools view -o), via spawned sbatch
  - kind: artifact
    path_template: "{REPO}/data/processed/hg38/subsamples_intermediate/_jobs/subsample_{frac:03d}pct.sbatch"
    cardinality: 3
    note: generated sbatch script files (intermediate)
  - kind: artifact
    path_template: "{REPO}/logs/stage6a_subsample_{date}/subsample_{frac:03d}pct.%j.{out,err}"
    cardinality: 6  # 3 fractions × {out, err}
    written_by: slurm

driver_pattern:
  kind: python_writes_bash_then_submits
  embedded_language: bash
  template_site: 13_subsample_merged.py:30-66 (SBATCH_TEMPLATE)
  embedded_analysis:
    inputs: [{INPUT_BAM}]
    outputs: [{out_bam}, {counts_tsv}]
    stochastic_ops:
      - fn: "samtools view -s"
        seed_expression: "42.{frac:02d}"
        seed_set: true
        seed_value_origin: literal_in_template
    side_effects:
      - kind: filesystem_lock
        site: SBATCH_TEMPLATE:59-63
        path: "{COUNTS_TSV}.lock"

dataframes: []   # this script doesn't manipulate dataframes; it submits jobs

transformations: []

models: []

stochastic_ops:
  - site: 13_subsample_merged.py:48 (template variable SEED_FRAC)
    fn: external samtools view -s
    seed_set: true
    seed_value_origin: "42.{frac:02d}"
    severity: OK   # CLAUDE.md mandates seed=42; partially compliant (uses 42.XX)

side_effects:
  - { site: 13_subsample_merged.py:78-80, kind: mkdir, paths: [OUT_DIR, LOGS_DIR, JOBS_DIR] }
  - { site: 13_subsample_merged.py:99, kind: filesystem_chmod, mode: "0o755" }
  - { site: 13_subsample_merged.py:101, kind: subprocess_run, cmd: ["sbatch", "{script}"] }

environment:
  python_packages: [pathlib, subprocess, re, sys, datetime]   # all stdlib

unresolved:
  - kind: external_runtime_state
    site: 13_subsample_merged.py:101
    note: outputs only materialize after spawned sbatch jobs complete; static layer cannot verify schema_written

audit_findings_preview:
  - severity: BLOCKER
    rule: warn-absolute-paths
    sites: [13_subsample_merged.py:12, :13, :14]
    note: module-level absolute paths with no override mechanism (no CLI args); script is non-portable
  - severity: NOTE
    rule: seed-policy
    site: 13_subsample_merged.py:48
    note: seed=42.{frac:02d} — uses default 42 base ✓; document the {frac:02d} suffix as intentional dispersion
  - severity: NOTE
    rule: driver-pattern-detected
    note: this script generates and submits bash; output schema can only be fully verified after spawned jobs run — gate runtime trace on sbatch completion if --deep
```

### Schema feedback from YAML 2
- Need `driver_pattern:` block — Python/R/bash that writes a script in
  *another* language and submits it. Common in HPC. The auditor must
  recurse into the embedded language to extract embedded I/O, seeds,
  side effects.
- Need `external_binary:` under inputs/outputs — when the script's
  reads/writes happen via a subprocess (samtools, bedtools, modkit),
  the binary's known I/O semantics determine the actual flow.
- Need to distinguish `kind:` of output: `tabular` / `bam` / `vcf` /
  `artifact` / `figure`. Different rules apply.
- `append_pattern:` is worth surfacing — flock-protected vs naive
  append vs single-shot write is an audit-relevant distinction.
- Module-level constants are a config interface even without argparse;
  the auditor should treat `INPUT_BAM = "/abs/path"` the same way as
  an optparse default with `default_kind: absolute`.

---

## YAML 3 — Bash: `03_run_one.sh`

```yaml
schema_version: 0.1
script:
  path: biotoolsBenchmarks/samtools/sort/src/03_run_one.sh
  language: bash
  layers_used: [static]

config_interface:
  framework: getopts
  options:
    - { flag: -i, name: INPUT_BAM,         required: true,  role: input_path }
    - { flag: -o, name: OUTPUT_DIR,        required: true,  role: output_dir }
    - { flag: -T, name: TMP_DIR,           required: true,  role: scratch_dir }
    - { flag: -c, name: CSV_PATH,          required: true,  role: output_path }
    - { flag: -t, name: THREADS,           default: 8 }
    - { flag: -m, name: MEM_PER_THREAD,    default: "2G" }
    - { flag: -l, name: COMPRESSION_LEVEL, default: 6 }
    - { flag: -k, name: SORT_KEY,          default: "coord", domain: [coord, name] }
    - { flag: -F, name: OUTPUT_FMT,        default: "BAM",   domain: [BAM, CRAM] }
    - { flag: -R, name: REFERENCE,         required_if: "$OUTPUT_FMT == CRAM" }
    - { flag: -s, name: SAMTOOLS_BIN,      default_from_env: SAMTOOLS_BIN, fallback: "samtools" }
    - { flag: -G, name: GTIME_BIN,         resolution: "sibling of samtools, else /usr/bin/time" }
    - { flag: -b, name: BUILD_MODE,        default: "conda", domain: [conda, container, native] }
    - { flag: -r, name: REPLICATE,         default: 1 }
    - { flag: -u, name: RUN_ID,            default: auto-from-factors }
    - { flag: -W, name: WARMUP,            default: 0 }
    - { flag: -K, name: KEEP_OUTPUT,       default: 0 }

inputs:
  - path_template: "{INPUT_BAM}"
    format: bam
    read_call: null   # consumed by samtools sort, not by this script directly
    consumed_by: external_binary
    validation:
      - { site: 03_run_one.sh:80, check: "[[ -f \"$INPUT_BAM\" ]]" }
  - path_template: "{REFERENCE}"
    format: fasta
    required_if: OUTPUT_FMT == CRAM
    consumed_by: external_binary

outputs:
  - kind: tabular
    path_template: "{CSV_PATH}"
    format: csv
    write_mode: append
    write_call: { mechanism: echo_redirect, site: 03_run_one.sh:202 }
    append_pattern:
      mechanism: flock
      site: 03_run_one.sh:198-203
      concurrency_safe: true
    schema_written:
      columns: [run_id, timestamp, host, cpu_model, partition, slurm_jobid,
                samtools_version, build_mode, input_bam, threads, mem_per_thread,
                compression_level, sort_key, output_fmt, tmp_dir, tmp_fs_type,
                replicate, wall_s, user_cpu_s, sys_cpu_s, cpu_pct, peak_rss_kb,
                minor_pf, major_pf, fs_in, fs_out, exit_status, output_bytes, output_path]
      origin: HEADER variable at 03_run_one.sh:194
      header_written_on_first_write: true   # `[[ ! -f "$CSV_PATH" ]] && echo "$HEADER"`
  - kind: bam_or_cram
    path_template: "{OUTPUT_DIR}/{RUN_ID}.{ext}"
    slot_bindings: { ext: "cram if OUTPUT_FMT==CRAM else bam" }
    written_by: external_binary (samtools sort -o)
    lifecycle: { deleted_if: "KEEP_OUTPUT == 0" }
  - kind: artifact
    paths:
      - "{OUTPUT_DIR}/{RUN_ID}.time.txt"
      - "{OUTPUT_DIR}/{RUN_ID}.stdout.log"
      - "{OUTPUT_DIR}/{RUN_ID}.stderr.log"

external_binaries:
  - name: samtools
    site: 03_run_one.sh:152
    command_template: "samtools sort -@ {THREADS} -m {MEM_PER_THREAD} -l {COMPRESSION_LEVEL} -T {TMP_DIR}/{RUN_ID}.tmp --output-fmt {OUTPUT_FMT} [-n] [-o {OUT_BAM}] {INPUT_BAM}"
    wrapped_by: "{GTIME_BIN} -v -o {TIME_FILE}"
  - name: GTIME_BIN
    site: 03_run_one.sh:152
    purpose: capture wall/cpu/rss/page-faults
    resolution: dynamic (samtools-sibling then /usr/bin/time)
  - name: flock
    site: 03_run_one.sh:200
    purpose: serialize concurrent CSV appends

env_vars_read:
  - SAMTOOLS_BIN
  - SLURM_JOB_PARTITION
  - SLURM_JOB_ID

dataframes: []   # bash doesn't have these
transformations: []
models: []
stochastic_ops: []   # samtools sort is deterministic

side_effects:
  - { site: 03_run_one.sh:101, kind: mkdir, paths: [OUTPUT_DIR, TMP_DIR] }
  - { site: 03_run_one.sh:157, kind: filesystem_delete, paths: ["{TMP_DIR}/{RUN_ID}.tmp.*"] }
  - { site: 03_run_one.sh:207, kind: filesystem_delete, paths: [OUT_BAM, OUT_BAM.bai, OUT_BAM.csi], guard: "KEEP_OUTPUT == 0" }

unresolved: []

audit_findings_preview:
  - severity: NOTE
    rule: external-binary-io
    note: samtools sort I/O is not directly statically traceable; runtime trace via strace -e openat will ground-truth it
  - severity: NOTE
    rule: csv-header-self-written
    site: 03_run_one.sh:201
    note: header written on first run; good. WARNING-promote if a parallel run could race the first-time header write (flock makes this safe here)
```

### Schema feedback from YAML 3
- Need `external_binaries:` block, both at the binary level and
  attached to specific I/O entries.
- Need `write_mode: append` and `header_written_on_first_write: bool`
  fields under outputs.
- Need `validation:` array under inputs for pre-flight checks
  (`[[ -f "$X" ]]`).
- Need `env_vars_read:` and `env_vars_written:` as top-level fields.
- For bash, dataframes/transformations/models/stochastic_ops fields
  should be allowed to be empty arrays rather than required — they're
  language-agnostic but not all languages populate them.

---

## Consolidated schema deltas (round 4 input)

Field additions / changes the three examples surface, ordered by how
load-bearing they are:

1. **`config_interface:`** — required top-level block. Captures
   optparse / argparse / getopts / Snakemake-config / module-constant
   surfaces. Drives portability and "what changes from run to run"
   analysis.
2. **`external_binaries:`** — required when present. Most bioinformatics
   I/O happens via spawned binaries. Needs a small companion catalogue
   `library_io_semantics.yaml` so the auditor knows `samtools sort -o
   {x}` writes to `{x}`.
3. **`driver_pattern:`** — for scripts that emit and submit code in
   another language. Recursive inference into the embedded script.
4. **`hardcoded_data:`** — sample lists, contig names, threshold
   constants embedded in code. Audit-relevant; often a refactor target.
5. **`audit_findings_preview:`** — static findings emitted alongside
   the YAML, finalized in the report. Avoids the auditor needing to
   re-parse its own inferred YAML.
6. **`validation:`** — inline pre-flight checks (`[[ -f $X ]]`,
   `command -v X >/dev/null`). Useful as positive evidence of
   defensive coding; absence of these in critical inputs is a NOTE.
7. **`append_pattern:`** + `write_mode: append` — distinguishes
   append-with-lock from naive append from single-shot write.
8. **`env_vars_read/written:`** — top-level.
9. **Output `kind:`** — `tabular` / `bam` / `vcf` / `figure` /
   `artifact`. Different audit rules apply per kind.
10. **Dataframes / transformations / models / stochastic_ops** all
    relaxed to "empty list permitted" for languages that don't have
    these abstractions.

The first three reshape the §4 schema substantially; the rest are
additive.

---

## What's next (round 4)

Two paths from here, not mutually exclusive:

- **A.** Roll the schema deltas above into `02_inference_design.md`
  §4 (revised schema v0.2), then commit. Mechanical.
- **B.** Pick one of the three scripts and start sketching the actual
  parser — likely R first because the NSE handling is the hardest and
  the most informative for the eventual Python/bash parsers. Write a
  short prototype that consumes the script and emits the YAML, then
  diff it against the hand-built target.

My instinct: **A first, then B on the R script**. A locks the schema;
B converts the schema into something machine-verifiable. Both should
happen in this branch.
