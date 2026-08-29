#!/usr/bin/env python3
"""
generate_dockerfile.py — Template engine for HPC Docker images
Author: Samuel Ahuno
Purpose: Render a principle-compliant Dockerfile from a tool-type template

Usage:
    python3 generate_dockerfile.py \
        --tool-name samtools \
        --tool-type biocli \
        --version 1.21 \
        --packages-conda "samtools=1.21 htslib=1.21" \
        --packages-pip "" \
        --validation-cmd "samtools --version" \
        --maintainer sahuno

Tool types: ont | cuda | r | python-ml | biocli | generic

For R tool type, also pass:
    --packages-r-bioc "DESeq2 edgeR"     (Bioconductor packages)
    --packages-r-cran "ggplot2 dplyr"    (CRAN packages)
"""

import argparse
import os
import sys
from string import Template

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(SKILL_DIR, "templates", "dockerfiles")

# Default base images per tool type
BASE_IMAGES = {
    "ont":       "nanoporetech/dorado:sha",   # user should pin to specific SHA
    "cuda":      "nvidia/cuda:12.4.1-base-ubuntu22.04",
    "r":         "bioconductor/bioconductor_docker:devel",
    "python-ml": "condaforge/miniforge3:latest",
    "biocli":    "condaforge/miniforge3:latest",
    "generic":   "condaforge/miniforge3:latest",
}

TEMPLATE_FILES = {
    "ont":       "ont_tools.Dockerfile",
    "cuda":      "cuda_base.Dockerfile",
    "r":         "r_base.Dockerfile",
    "python-ml": "cuda_base.Dockerfile",
    "biocli":    "conda_base.Dockerfile",
    "generic":   "conda_base.Dockerfile",
}


def load_template(tool_type: str) -> str:
    tfile = TEMPLATE_FILES.get(tool_type)
    if not tfile:
        print(f"ERROR: Unknown tool type '{tool_type}'. "
              f"Choose from: {', '.join(TEMPLATE_FILES.keys())}", file=sys.stderr)
        sys.exit(1)
    path = os.path.join(TEMPLATE_DIR, tfile)
    if not os.path.exists(path):
        print(f"ERROR: Template not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return f.read()


def format_conda_install(packages: str) -> str:
    if not packages.strip():
        return "# No additional conda packages"
    pkgs = packages.strip().split()
    return "RUN mamba install -y \\\n    " + " \\\n    ".join(pkgs) + " \\\n    && mamba clean --all -y"


def format_bioc_install(packages: str) -> str:
    if not packages.strip():
        return "# No Bioconductor packages"
    pkgs = '", "'.join(packages.strip().split())
    return (
        'RUN Rscript -e "\\\n'
        '    if (!requireNamespace(\'BiocManager\', quietly = TRUE)) '
        'install.packages(\'BiocManager\'); \\\n'
        f'    BiocManager::install(c(\\"{pkgs}\\"), ask = FALSE, update = FALSE)"'
    )


def format_cran_install(packages: str) -> str:
    if not packages.strip():
        return "# No CRAN packages"
    pkgs = '", "'.join(packages.strip().split())
    return (
        'RUN Rscript -e "\\\n'
        f'    install.packages(c(\\"{pkgs}\\"), repos=\'https://cloud.r-project.org\')"'
    )


def format_pip_install(packages: str) -> str:
    if not packages.strip():
        return "# No pip packages"
    pkgs = packages.strip().split()
    return "RUN pip install --no-cache-dir " + " ".join(pkgs)


def main():
    parser = argparse.ArgumentParser(description="Generate a principle-compliant Dockerfile")
    parser.add_argument("--tool-name",       required=True, help="Tool name (Docker Hub image name)")
    parser.add_argument("--tool-type",       required=True, help="Tool type: ont|cuda|r|python-ml|biocli|generic")
    parser.add_argument("--version",         required=True, help="Tool version (semver)")
    parser.add_argument("--packages-conda",   default="",  help="Space-separated conda packages")
    parser.add_argument("--packages-pip",     default="",  help="Space-separated pip packages")
    parser.add_argument("--packages-r-bioc",  default="",  help="Space-separated Bioconductor packages (r type only)")
    parser.add_argument("--packages-r-cran",  default="",  help="Space-separated CRAN packages (r type only)")
    parser.add_argument("--validation-cmd",  required=True, help="Command to verify install, e.g. 'samtools --version'")
    parser.add_argument("--maintainer",      default="unknown", help="Maintainer name or GitHub username")
    parser.add_argument("--base-image",      default="",   help="Override base image (optional)")
    args = parser.parse_args()

    tool_type = args.tool_type.lower()
    base_image = args.base_image if args.base_image else BASE_IMAGES.get(tool_type, "condaforge/miniforge3:latest")

    template_str = load_template(tool_type)

    substitutions = {
        "TOOL_NAME":       args.tool_name,
        "VERSION":         args.version,
        "MAINTAINER":      args.maintainer,
        "BASE_IMAGE":      base_image,
        "CONDA_INSTALL":   format_conda_install(args.packages_conda),
        "PIP_INSTALL":     format_pip_install(args.packages_pip),
        "BIOC_INSTALL":    format_bioc_install(args.packages_r_bioc),
        "CRAN_INSTALL":    format_cran_install(args.packages_r_cran),
        "VALIDATION_CMD":  args.validation_cmd,
    }

    try:
        result = Template(template_str).substitute(substitutions)
    except KeyError as e:
        print(f"ERROR: Template placeholder missing in substitutions: {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
