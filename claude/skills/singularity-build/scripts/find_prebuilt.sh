#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-05-20
# Purpose: Probe for a pre-built Apptainer/Docker image for a bioinformatics
#          tool BEFORE falling through to a from-scratch build. Implements the
#          source-priority + catalog-first logic of the singularity-build
#          skill's Step 0 (acquire-vs-build triage).
set -euo pipefail

NAME=""; VERSION=""; PROBE=1
CATALOG="${SOFTWARES_CONTAINERS_CONFIG:-/data1/greenbab/users/ahunos/apps/llm_configs/claude/profiles/software_configs/softwares_containers_config.yaml}"

usage() {
  cat <<EOF
Usage: find_prebuilt.sh --name TOOL --version VER [--no-probe] [--catalog FILE]
  --name      tool name as known to bioconda/biocontainers (required)
  --version   version string, e.g. 1.21 (required)
  --no-probe  skip network calls; print candidate templates only (offline/testable)
  --catalog   path to softwares_containers_config.yaml (default: lab config)
Exit codes: 0 candidates printed | 2 usage error | 3 already in catalog | 4 no candidates
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)    [[ $# -lt 2 ]] && { echo "--name requires a value" >&2; usage; exit 2; };    NAME="$2"; shift 2;;
    --version) [[ $# -lt 2 ]] && { echo "--version requires a value" >&2; usage; exit 2; }; VERSION="$2"; shift 2;;
    --no-probe) PROBE=0; shift;;
    --catalog) [[ $# -lt 2 ]] && { echo "--catalog requires a value" >&2; usage; exit 2; }; CATALOG="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2;;
  esac
done
[[ -z "$NAME" || -z "$VERSION" ]] && { usage; exit 2; }

# Escape ERE metacharacters in the tool name before using it in grep -E
NAME_ESCAPED="$(printf '%s' "$NAME" | sed 's/[][\\.^$*+?(){}|]/\\&/g')"

# 1. Lab catalog first — never re-acquire a registered image
if [[ -f "$CATALOG" ]] && grep -iqE "(^|[^a-z])${NAME_ESCAPED}([^a-z]|$)" "$CATALOG"; then
  echo "ALREADY REGISTERED in catalog ($CATALOG):"
  grep -inE "(^|[^a-z])${NAME_ESCAPED}([^a-z]|$)" "$CATALOG" || true
  echo ">> Reuse the registered SIF; no pull/build needed."
  exit 3
fi

# 2. (network tag resolution added in Task 2) — placeholder keeps offline path working
TAG=""

# 3. Emit candidates (offline template path; network-resolved path added in Task 2)
echo "=== Pre-built image candidates for ${NAME} ${VERSION} ==="
if [[ -z "$TAG" ]]; then
  echo "(TAG not yet resolved — offline template; resolve <TAG> = version--buildhash via quay tags):"
  echo "    apptainer pull https://depot.galaxyproject.org/singularity/${NAME}:<TAG>"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:<TAG>"
  exit 0
fi
