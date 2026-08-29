# Config Template and Run Script Conventions

## Config Template (`config_template.yaml`)

Copy this to each run directory and fill in REQUIRED fields.

```yaml
# config_template.yaml — {workflow_name}
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: {date}
#
# Usage:
#   1. Copy to your run directory:
#        mkdir -p outputs/{run_name} && cp config_template.yaml outputs/{run_name}/config.yaml
#   2. Fill in REQUIRED fields
#   3. Dry-run: bash run_snakemake.sh -n

# =============================================
# REQUIRED
# =============================================

output_dir: "FILL_ME"            # Run root — all outputs go under this directory
sample_manifest: "FILL_ME"       # TSV: sample, bam_path [, bam_index]
ref_fasta: "FILL_ME"
img: "FILL_ME"                   # Singularity/Apptainer image path (pinned version, never :latest)

# =============================================
# OPTIONAL — Feature A
# =============================================

# Set to enable feature A (null = skip)
feature_a_script: null
feature_a_extra_args: ""

# =============================================
# OPTIONAL — Feature B (requires Feature A)
# =============================================

# Set both to enable (null = skip)
feature_b_input: null
feature_b_map: null
```

### Config Conventions

- Config filename matches the run: `config.mm10_DMSO_LINE1.yaml`
- All cohort-specific details are config args, never hardcoded
- Use comments to explain each key
- Mark REQUIRED vs OPTIONAL sections clearly
- Container images use pinned versions, never `:latest`
- `output_dir` is the ONLY path key — all subdirs derived in Snakefile

## Run Script Template (`run_snakemake.sh`)

Place this at the run root alongside config.yaml.

```bash
#!/usr/bin/env bash
# run_snakemake.sh — Reproduce this workflow run
# Author: Samuel Ahuno (ekwame001@gmail.com)
# Date: {date}
#
# Usage:
#   bash run_snakemake.sh        # execute
#   bash run_snakemake.sh -n     # dry-run
#   bash run_snakemake.sh --forcerun rule_name  # force-rerun a specific rule

set -euo pipefail

# Prevent SLURM memory variable conflicts when coordinator is an sbatch job
unset SLURM_MEM_PER_NODE

export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache

SNAKEFILE="/abs/path/to/workflows/{workflow_name}/Snakefile"
CONFIGFILE="$(dirname "$0")/config.yaml"
PROFILE="/abs/path/to/workflows/{workflow_name}/profiles/slurm"

snakemake \
    --snakefile "$SNAKEFILE" \
    --configfile "$CONFIGFILE" \
    --workflow-profile "$PROFILE" \
    --use-singularity \
    --singularity-args "--bind /data1/greenbab/,/data1/collab001/" \
    --rerun-incomplete \
    --jobs 4 \
    "$@"
```

### Run Script Conventions

- `unset SLURM_MEM_PER_NODE` at the top — prevents coordinator's memory setting from propagating to child jobs
- `CONFIGFILE` is relative to script location (`$(dirname "$0")/...`) — works from any directory
- `SNAKEFILE` and `PROFILE` are absolute paths (workflow code lives elsewhere)
- `"$@"` passes extra flags (like `-n`, `--forcerun`, `--until`)
- `APPTAINER_CACHEDIR` avoids home directory quota issues on compute nodes

## Sample Manifest Format

TSV file with at minimum these columns:

```tsv
sample	bam_path
sample_A	/abs/path/to/sample_A.bam
sample_B	/abs/path/to/sample_B.bam
```

Optional additional columns: `bam_index`, `condition`, `patient_id`, etc.
