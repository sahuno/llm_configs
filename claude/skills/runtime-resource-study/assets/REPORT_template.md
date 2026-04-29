# {{TOOL_NAME}} {{COMMAND}} — runtime and resource benchmarking report

- **Author**: {{USER}}
- **Date**: {{DATE}}
- **Status**: [draft | complete]
- **Tool under test**: {{TOOL_NAME}} {{COMMAND}} v{{TOOL_VERSION}}
- **Hardware**: MSKCC HPC, `cpushort` partition, Intel Xeon Gold 6348 @ 2.60 GHz (Ice Lake-SP)
- **Project root**: `{{PROJECT_ROOT}}`
- **Companion docs**: `model.yaml`, `exec_summary.pdf`

---

## The math

```
wall_seconds  =  [FILL IN: fitted equation from model.yaml]
peak_rss_GB   =  [FILL IN: fitted equation from model.yaml]
```

- **N_primary_records** = `[command to compute, e.g. `samtools view -c -F 0x900 input.bam`]`
- **file_size_bytes** = `stat -c '%s' <input>`
- Calibrated at `{{HEADLINE_CONFIG}}` on Intel Xeon Gold 6348.

**Fit:** R² = [FILL IN] across [FILL IN] data points.
**Out-of-sample validation:** within ±[FILL IN]% on held-out inputs.
**Apply +30% safety margin** for production resource directives.

---

## TL;DR

1. **Production config**: `{{HEADLINE_CONFIG}}` → [headline wall on baseline input].
2. **Dead factors**: [list factors that didn't move the needle].
3. **Trap**: [list any factor levels to avoid, e.g., `-l 9` for samtools sort].
4. **Build mode**: [container vs conda verdict].
5. **Predictive model**: [headline R² + validation error].

---

## 1. Research questions

| # | Question | Answer | Source |
|---|---|---|---|
| 1 | Minimum cores / memory and corresponding runtimes | See §6 helper formula | Stages 2-5 |
| 2 | Empirical throughput | [records/sec] at baseline | Stage 5 model |
| 3 | When do we get diminishing returns? | [thread elbow] | Stage 2 threads sweep |
| 4 | Effect of input size | [linear / non-linear?] | Stage 5 |
| 5 | Container vs conda vs alternative implementation | [verdict] | Stage 4 |
| 6 | Hardware variability | [observed range] | Stages 1-7 |

---

## 2. Input data

### Calibration input

`{{CALIBRATION_INPUT}}` — preflight at `results/preflight/<input>.preflight.yaml`.

| Field | Value |
|---|---|
| File size | [FILL IN] |
| Total records | [FILL IN] |
| Primary records | [FILL IN] |
| Mean record size | [FILL IN] |
| Format / technology | [FILL IN] |

### Validation inputs

[FILL IN: held-out inputs used in Stage 6, with their record counts and file sizes]

---

## 3. Methodology

All controls per the skill's non-negotiables (skill: `runtime-resource-study`):

1. One condition per SLURM job (`--exclusive`, fresh node — cold page cache)
2. `--exclude=isca071` (slow CPU vintage on cpushort)
3. GNU time `-v` via dynamic resolution (sibling of tool binary)
4. ≥3 replicates per condition (5+ for build-mode); CV>20% flag
5. flock-guarded CSV appends; manifest separate from benchmark CSV
6. Random seed 42 for all stochastic ops

Total compute: [FILL IN: ~X jobs, ~Y minutes cumulative].

---

## 4. Stage-by-stage results

### Stage 1 — Preflight
[Brief summary of what the input looks like.]

### Stage 2 — OFAT factor scan
**Driver**: `src/04_submit_grid.py` | **Results**: `results/<date>_stage2_ofat/`

[FILL IN: per-sweep table showing which factors moved the needle.]

![Threads scaling](results/<date>_stage2_ofat/figures/png/sweep_threads_wall.png)

### Stage 3 — Confirmation factorial
**Driver**: `src/06_submit_stage3.py` | **Results**: `results/<date>_stage3_factorial/`

[FILL IN: main effects table; identify the optimum.]

![Main effects](results/<date>_stage3_factorial/figures/png/main_effects.png)

**Headline winner**: [FILL IN: `--option1 X --option2 Y` → wall, CV, RSS].

### Stage 4 — Build-mode + alternative-implementation comparison
**Driver**: `src/08_submit_stage4.py` | **Results**: `results/<date>_stage4_buildmode/`

[FILL IN: container vs conda vs alternative-implementation table.]

[Optional: include the page-faults plot if relevant — see samtools sort exemplar.]

### Stage 5 — Input-size scan
**Driver**: `src/10_submit_input_scan.py` | **Results**: `results/<date>_stage5_inputscan/`

[FILL IN: regression equation, R², throughput.]

![Wall vs input](results/<date>_stage5_inputscan/figures/png/wall_vs_records.png)

### Stage 6 — Out-of-sample validation
**Driver**: `src/12_validate_predictions.py` | **Results**: `results/<date>_stage6_validate/`

| Input | N | Predicted wall | Observed wall | Error |
|---|---|---|---|---|
| [FILL IN] | | | | |

[Note whether 1-term or 2-term model is used in production.]

### Stage 7 — Variance partitioning + cost + report

**Variance partitioning** (`fit_model.py --variance-partition`):
- Condition (fixed): [FILL IN]%
- Host (random): [FILL IN]%
- Replicate (residual): [FILL IN]%

[If host > 25%, document which nodes were excluded.]

**Cost-Pareto frontier** (`cost_accounting.py --rate 0.05`):
- Cheapest config: [FILL IN]
- Fastest config: [FILL IN]
- Recommended trade-off: [FILL IN]

---

## 5. Predictive model

Full machine-readable spec: `model.yaml`.

### Drop-in helper

```python
def {{TOOL_NAME}}_resources(n_primary, file_size_gb, threads={{THREADS_REC}}):
    """Recommended resources for {{TOOL_NAME}} {{COMMAND}}.
    Calibrated on Intel Xeon Gold 6348; see model.yaml for caveats."""
    wall_s   = max([FILL IN: formula], 5)
    runtime_s = int(wall_s * 1.3)            # 30% safety
    rss_gb   = min([FILL IN: rss formula], [FILL IN: cap])
    mem_mb   = int(rss_gb * 1.3 * 1024)
    m_per_thread_gb = max(2, int(rss_gb / threads * 1.3))
    return dict(threads=threads, m=f"{m_per_thread_gb}G", l=1,
                runtime_s=runtime_s, mem_mb=mem_mb)
```

---

## 6. Practical recommendations

1. **{{TOOL_NAME}} on long-read mod-base BAMs** (or whatever input class): use `{{HEADLINE_CONFIG}}`.
2. **Container** (apptainer SIF) when available — avoids NFS cold-start tax.
3. **`-l 1`** for compression on long-read BAMs (`-l 9` is 8× slower for marginal size win).
4. **Allocate +30% over the model's prediction** for both wall time and memory.

---

## 7. Limitations and future work

| Limitation | Impact | How to fix |
|---|---|---|
| [FILL IN] | | |

---

## 8. Reproducibility — file inventory

### Source code (`src/`)

| File | Purpose |
|---|---|
| `01_inspect_input.sh` | Preflight |
| `03_run_one.sh` | Single-condition runner |
| `04_submit_grid.py` | Stage 2 OFAT driver |
| `06_submit_stage3.py` | Stage 3 factorial driver |
| `08_submit_stage4.py` | Stage 4 build mode |
| `10_submit_input_scan.py` | Stage 5 input scan |
| `12_validate_predictions.py` | Stage 6 validation |
| ... | |

### Results (`results/`)

[Stage-by-stage directory listing.]

### Figures

[Headline figures with relative paths.]

---

## 9. Appendix: study timeline

| Stage | Date | Jobs | Wall time | Compute |
|---|---|---|---|---|
| Preflight + pilot | | | | |
| Stage 2 (OFAT) | | | | |
| Stage 3 (factorial) | | | | |
| Stage 4 (build mode) | | | | |
| Stage 5 (input scan) | | | | |
| Stage 6 (validation) | | | | |
| Stage 7 (report) | | | | |
| **Total** | | | | |
