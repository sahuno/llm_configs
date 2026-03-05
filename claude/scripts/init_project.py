#!/usr/bin/env python3
"""Initialize a new computational biology project.

Author: Samuel Ahuno
Date: 2026-03-02
Purpose: Scaffold a lean, parameterized project directory with useful starter
         files (.gitignore, sample_sheet.tsv, config.yaml) instead of empty READMEs.

Usage:
    # Scaffold into the current directory (uses cwd name as project name):
    cd /path/to/my_project && python init_project.py --type analysis --genome hg38

    # Override name to create a new subdirectory:
    python init_project.py --name my_project --type analysis --genome hg38
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Valid genome builds (mirrors CLAUDE.md §2)
# ---------------------------------------------------------------------------
VALID_GENOMES = [
    "mm10", "mm39", "GRCm39",
    "hg38", "GRCh38", "hg19", "GRCh37",
    "t2t", "chm13",
]

PROJECT_TYPES = ["analysis", "pipeline", "ml"]
WORKFLOW_ENGINES = ["snakemake", "nextflow"]


# ---------------------------------------------------------------------------
# Directory definitions by project type
# ---------------------------------------------------------------------------

def _core_dirs(genome, include_default_workflow=True):
    """Directories created for every project type.

    Parameters
    ----------
    genome : str
        Genome build tag (e.g. 'hg38', 'mm10').
    include_default_workflow : bool
        If True, include the default wf_snakemake dirs. Set to False
        for --type pipeline, which provides its own engine-specific dirs.

    Returns
    -------
    list[str]
        Directory paths relative to project root.
    """
    dirs = [
        "data/raw",
        f"data/processed/{genome}",
        "data/inbox",
        "src",
        "logs",
        "docs",
        "softwares/containers",
    ]
    if include_default_workflow:
        dirs += [
            "workflows/wf_snakemake/configs",
            "workflows/wf_snakemake/profiles/slurm",
            "workflows/wf_snakemake/rules",
            "workflows/wf_snakemake/scripts",
        ]
    return dirs


def _analysis_dirs():
    """Extra directories for --type analysis."""
    return [
        "docs/deepResearch",
    ]


def _pipeline_snakemake_dirs():
    """Directories for --type pipeline --engine snakemake.

    Follows the Snakemake workflow catalog layout so the pipeline
    is publishable/shareable from day one.
    """
    return [
        "workflows/wf_snakemake/rules",
        "workflows/wf_snakemake/scripts",
        "workflows/wf_snakemake/envs",
        "workflows/wf_snakemake/schemas",
        "config",
        "profiles/slurm",
        "tests/data",
    ]


def _pipeline_nextflow_dirs():
    """Directories for --type pipeline --engine nextflow."""
    return [
        "workflows/wf_nextflow/modules",
        "workflows/wf_nextflow/bin",
        "workflows/wf_nextflow/envs",
        "workflows/wf_nextflow/conf",
        "config",
        "profiles/slurm",
        "tests/data",
    ]


def _ml_dirs():
    """Extra directories for --type ml."""
    return [
        "src/models",
        "src/features",
        "notebooks",
    ]


def _results_dirs(genome):
    """Starter results directory with figures subdirs.

    Real runs use results/{date}_{genome}_{description}/figures/{png,pdf,svg}.
    We create a placeholder v1 to show the pattern.
    """
    today = datetime.now().strftime("%Y%m%d")
    base = f"results/{today}_{genome}_v1"
    return [
        base,
        f"{base}/figures/png",
        f"{base}/figures/pdf",
        f"{base}/figures/svg",
    ]


# ---------------------------------------------------------------------------
# Generated file contents
# ---------------------------------------------------------------------------

def _gitignore_content():
    """Pre-populated .gitignore for genomics projects."""
    return """\
# === Raw / large genomic files ===
*.bam
*.bam.bai
*.cram
*.crai
*.pod5
*.fast5
*.fastq
*.fastq.gz
*.fq
*.fq.gz
*.sif

# === Processed genomic files (commit summaries, not full files) ===
*.bigwig
*.bw
*.bigbed
*.bcf
*.vcf.gz
*.vcf.gz.tbi

# === Data directories ===
data/raw/
data/inbox/

# === Environment / IDE ===
.snakemake/
.nextflow/
work/
__pycache__/
*.pyc
.ipynb_checkpoints/
.Rhistory
.RData
.DS_Store
*.egg-info/
.venv/
.env

# === Logs (keep structure, ignore contents) ===
logs/*.log
"""


def _sample_sheet_content():
    """Blank sample sheet with the canonical header."""
    return "patient\tsample\tcondition\tassay\tpath\tgenome\n"


def _config_content(project_name, genome, project_type):
    """Starter config.yaml.

    Parameters
    ----------
    project_name : str
    genome : str
    project_type : str

    Returns
    -------
    str
        YAML content.
    """
    return f"""\
# Project configuration
# Generated: {datetime.now().strftime('%Y-%m-%d')}

project_name: "{project_name}"
genome: "{genome}"
project_type: "{project_type}"

# Output directory — all results live under here.
# Naming convention: results/{{date}}_{{description}}
# Derive FIGDIR and LOGDIR from this in Snakefile; never add separate keys.
output_dir: "results/"

# Reference paths — load from profiles/databases/databases_config.yaml
# Uncomment and fill for your genome build:
# reference_fasta: ""
# reference_gtf: ""
# chrom_sizes: ""

# Sample sheet
sample_sheet: "sample_sheet.tsv"

# Random seed (default per CLAUDE.md)
seed: 42
"""


def _readme_content(project_name, genome, project_type):
    """Top-level README.md.

    Parameters
    ----------
    project_name : str
    genome : str
    project_type : str

    Returns
    -------
    str
        Markdown content.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    results_date = datetime.now().strftime("%Y%m%d")
    return f"""\
# {project_name}

**Date**: {today}
**Genome**: {genome}
**Type**: {project_type}
**Author**: Samuel Ahuno

## Aims

1. _TODO: define objectives_

## Directory structure

```
{project_name}/
├── config.yaml                 # project parameters, genome paths
├── sample_sheet.tsv            # patient/sample/condition/assay/path/genome
├── data/
│   ├── inbox/                  # staging area — review before promoting to raw/
│   ├── raw/                    # IMMUTABLE after initial deposit
│   └── processed/{genome}/     # all transformed outputs, tagged by build
├── src/                        # analysis scripts (numbered: 01_, 02_, ...)
├── results/
│   └── {results_date}_{genome}_v1/  # one dir per run
│       └── figures/{{png,pdf,svg}}/
├── workflows/wf_snakemake/     # Snakefile, configs, profiles, rules
├── softwares/containers/       # .def files and third-party images
├── logs/                       # timestamped script logs
└── docs/
```

## How to add a new run

```bash
# Create a new results directory for each run:
mkdir -p results/$(date +%Y%m%d)_{genome}_<description>/figures/{{png,pdf,svg}}
```
"""


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def create_project(project_name, project_type, genome, engine=None, in_place=False):
    """Create the project directory structure and starter files.

    Parameters
    ----------
    project_name : str
        Name of the project. Used in README/config and as root directory
        name when ``in_place`` is False.
    project_type : str
        One of 'analysis', 'pipeline', 'ml'.
    genome : str
        Genome build tag.
    engine : str or None
        Workflow engine ('snakemake' or 'nextflow'). Only used when
        project_type is 'pipeline'.
    in_place : bool
        If True, scaffold into the current working directory instead of
        creating a new subdirectory.
    """
    if in_place:
        root = Path.cwd()
    else:
        root = Path(project_name)
        if root.exists():
            print(f"ERROR: Directory '{project_name}' already exists. Aborting.", file=sys.stderr)
            sys.exit(1)

    # Collect directories
    # Pipeline projects get engine-specific workflow dirs instead of the default
    skip_default_wf = (project_type == "pipeline")
    dirs = _core_dirs(genome, include_default_workflow=not skip_default_wf) + _results_dirs(genome)

    if project_type == "pipeline":
        pipeline_extras = {
            "snakemake": _pipeline_snakemake_dirs,
            "nextflow": _pipeline_nextflow_dirs,
        }
        dirs += pipeline_extras[engine]()
    elif project_type == "analysis":
        dirs += _analysis_dirs()
    elif project_type == "ml":
        dirs += _ml_dirs()

    # Create directories
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Write starter files
    files = {
        ".gitignore": _gitignore_content(),
        "sample_sheet.tsv": _sample_sheet_content(),
        "config.yaml": _config_content(project_name, genome, project_type),
        "README.md": _readme_content(project_name, genome, project_type),
    }

    for filename, content in files.items():
        (root / filename).write_text(content)

    # Summary
    dir_count = sum(1 for _ in root.rglob("*") if _.is_dir())
    file_count = sum(1 for _ in root.rglob("*") if _.is_file())
    print(f"Project '{project_name}' initialized: {dir_count} directories, {file_count} files")
    print(f"  Type:   {project_type}")
    if engine:
        print(f"  Engine: {engine}")
    print(f"  Genome: {genome}")
    print(f"  Root:   {root.resolve()}")


def parse_args():
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Initialize a new computational biology project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Scaffold into current directory (default):
  cd methylation_study && %(prog)s --type analysis --genome mm10

  # Build a Snakemake pipeline:
  %(prog)s --name variant_pipeline --type pipeline --engine snakemake --genome hg38

  # Build a Nextflow pipeline:
  %(prog)s --name ont_pipeline --type pipeline --engine nextflow --genome mm10

  # ML project:
  %(prog)s --name classifier --type ml --genome hg38
""",
    )
    cwd_name = Path.cwd().name
    parser.add_argument(
        "--name",
        default=None,
        help=f"Project name. Default: current directory name ('{cwd_name}'). "
        "When using the default, files are scaffolded in-place. "
        "When a name is given, a new subdirectory is created.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=PROJECT_TYPES,
        help="Project type: analysis | pipeline | ml",
    )
    parser.add_argument(
        "--engine",
        default=None,
        choices=WORKFLOW_ENGINES,
        help="Workflow engine (required for --type pipeline): snakemake | nextflow",
    )
    parser.add_argument(
        "--genome",
        required=True,
        choices=VALID_GENOMES,
        help="Primary genome build",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")

    args = parser.parse_args()

    # Validate: --engine is required for pipeline, ignored otherwise
    if args.type == "pipeline" and args.engine is None:
        parser.error("--engine is required when --type is 'pipeline'")

    return args


if __name__ == "__main__":
    args = parse_args()
    in_place = args.name is None
    project_name = args.name if args.name else Path.cwd().name
    create_project(project_name, args.type, args.genome, engine=args.engine, in_place=in_place)
