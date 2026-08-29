# Templates guide — how to fill each placeholder

Every template in `scripts/` uses `{{PLACEHOLDER}}` syntax. This page lists
what each placeholder means and where to find example values.

## Common placeholders (used across multiple templates)

| Placeholder | Meaning | Example |
|---|---|---|
| `{{TOOL_NAME}}` | Short tool name for run_id and dir naming | `samtools_sort`, `bcftools_call` |
| `{{COMMAND}}` | The actual command being benchmarked | `sort`, `mpileup`, `view`, `mem` |
| `{{TOOL_BIN}}` | Path or alias to the binary | `/home/ahunos/miniforge3/envs/snakemake/bin/samtools` |
| `{{INPUT_BAM}}` / `{{INPUT}}` | Calibration input path | `/data1/.../subset_chr17.bam` |
| `{{OUTPUT_DIR}}` | Where outputs go | `results/<date>_<stage>/runs` |
| `{{TMP_DIR}}` | Tmp-dir for the tool's spill / scratch | `/tmp` or `$TMPDIR` |
| `{{PROJECT_ROOT}}` | Top of the project tree | `/data1/greenbab/users/ahunos/projects/biotoolsBenchmarks/<tool>/<command>` |

## Per-template

### `01_inspect_input.sh.template`

Edit the `# === metadata extraction ===` block. The skeleton handles BAM,
VCF, FASTQ stubs — uncomment / adapt the right one.

For BAM:
```bash
"$TOOL_BIN" view -H "$INPUT" | grep '^@SQ' | wc -l         # contig count
"$TOOL_BIN" view -c "$INPUT"                                # total records
"$TOOL_BIN" view -c -F 0x900 "$INPUT"                       # primary records
```

For VCF:
```bash
bcftools view -h "$INPUT" | grep -c '^#CHROM'               # 1 if has header
bcftools view "$INPUT" | wc -l                              # variant count
```

For FASTQ:
```bash
seqkit stats "$INPUT"                                       # one-shot
```

### `03_run_one.sh.template`

The most important template. Edit:

1. **The command-construction block** (`# === Build command ===`). Replace
   the samtools-specific args with your tool's.
2. **The CSV header** (`HEADER=...`). Add columns specific to your factors.
3. **The CSV row** (`ROW=...`). Match the new header.

Don't change the `/usr/bin/time -v` resolution logic, the flock CSV
append, or the `unset SLURM_MEM_PER_NODE` — those are non-negotiable.

### `submit_grid.py.template`

Edit:

1. **`FACTORS` dict** — list of `{name, factor, values, static_overrides}`
   for OFAT mode, or a single product list for factorial mode. Examples:

```python
# OFAT (Stage 2)
SWEEPS = [
    {"name": "threads", "factor": "threads",
     "values": [1, 2, 4, 8, 16, 32], "static_overrides": {}},
    {"name": "mem", "factor": "mem_per_thread",
     "values": ["64M", "128M", "512M", "2G", "8G"], "static_overrides": {}},
]
```

```python
# Factorial (Stage 3)
FACTORS = {
    "threads":     [16, 32],
    "mem":         ["2G", "8G"],
    "compression": [1, 6],
    "tmp":         ["/tmp", "/data1/.../weka_tmp"],
}
```

2. **`BASELINE`** — held values for OFAT.
3. **The sbatch template body** — usually leave alone, but check `--mem`
   and `--time`.
4. **Run-id format** — must include all factor levels so it's unique.

### `summarise_stage.R.template`

Edit:

1. The factor names you're plotting (`threads_f`, `mem_f`, etc.).
2. The plot subtitle and labels to match your tool.
3. The list of `save_fig` calls — add or drop figures depending on what
   varies in your stage.

### `exec_summary.R.template`

Edit:

1. Title, author, date, hardware label.
2. The TL;DR text block (3–6 bullets).
3. The "Headline numbers" right-column data.
4. The two figures — usually Stage 3 main effects + Stage 5/6 obs-vs-pred.

Don't change the page geometry (US Letter portrait 8.5×11) unless you have
a specific reason; the layout was tuned for that size.

## Bundled scripts (no placeholders)

### `fit_model.py`

Run after Stage 5/6:

```bash
python fit_model.py \
  --csv results/<date>_stage5_inputscan/benchmark.csv \
  --validation-csv results/<date>_stage6_validate/benchmark.csv \
  --output model.yaml
```

Produces fit + validation residuals + caveats template.

### `cost_accounting.py`

Run after any benchmark CSV exists:

```bash
python cost_accounting.py \
  --csv results/<date>_stage3_factorial/benchmark.csv \
  --rate 0.05 \
  --output results/<date>_stage3_factorial/cost_pareto.csv
```

Default rate is `0.05` $/core-hour; user-configurable per project.

## Asset templates (in `assets/`)

### `REPORT_template.md`

Replace bracketed placeholders `[FILL IN: ...]` with your data. Key
sections to fill:

- **The math** — paste your fitted equations
- **TL;DR** — 5 bullets
- **Per-stage results** — link each stage's figures
- **Recommendations** — your production config
- **Limitations / future work** — be honest about what wasn't tested

### `model.yaml.template`

The machine-readable contract. Fill `wall_model`, `rss_model`,
`extrapolation`, `validation`, and `caveats` sections. The Python helper
function is generic — usually no edits needed.

### `PLAN_template.md`

A light planning doc to track progress through the stages. Optional —
write it if you want a running log; skip if the report is enough.
