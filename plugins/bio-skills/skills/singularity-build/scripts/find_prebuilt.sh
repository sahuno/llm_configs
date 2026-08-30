#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-05-20
# Purpose: Probe for a pre-built Apptainer/Docker image for a bioinformatics
#          tool BEFORE falling through to a from-scratch build. Implements the
#          source-priority + catalog-first logic of the singularity-build
#          skill's Step 0 (acquire-vs-build triage).
set -euo pipefail

NAME=""; VERSION=""; PROBE=1
# Container catalog. Resolution order: explicit --catalog, then
# $SOFTWARES_CONTAINERS_CONFIG, then the active site profile's containers.yaml
# (hpc-site plugin). The previous default was an absolute /data1 literal that
# existed on exactly one machine and silently resolved to "no catalog"
# everywhere else, so the catalog-first check quietly never fired.
CATALOG="${SOFTWARES_CONTAINERS_CONFIG:-}"
if [[ -z "$CATALOG" && -n "${SITE_CONFIG:-}" && -f "$SITE_CONFIG/containers.yaml" ]]; then
  CATALOG="$SITE_CONFIG/containers.yaml"
fi

usage() {
  cat <<EOF
Usage: find_prebuilt.sh --name TOOL --version VER [--no-probe] [--catalog FILE]
  --name      tool name as known to bioconda/biocontainers (required)
  --version   version string, e.g. 1.21 (required)
  --no-probe  skip network calls; print candidate templates only (offline/testable)
  --catalog   path to the container catalog (default: \$SOFTWARES_CONTAINERS_CONFIG,
              else \$SITE_CONFIG/containers.yaml)
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

# 2. Resolve the exact biocontainers tag (version + build suffix)
TAG="${FORCE_TAG:-}"
if [[ -z "$TAG" && "$PROBE" -eq 1 ]]; then
  # NAME/VERSION assumed URL-safe ([a-z0-9_.-], typical for biocontainers tags)
  API="https://quay.io/api/v1/repository/biocontainers/${NAME}/tag/?onlyActiveTags=true&filter_tag_name=like:${VERSION}"
  TAG="$(curl -sf --connect-timeout 5 --max-time 10 "$API" 2>/dev/null | VERSION="$VERSION" python3 -c '
import sys, os, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ver = os.environ.get("VERSION", "")
tags = [t["name"] for t in d.get("tags", [])]
exact = [t for t in tags if t.startswith(ver + "--")]
withbuild = [t for t in tags if "--" in t]
chosen = exact or withbuild or tags
print(chosen[0] if chosen else "")
' 2>/dev/null || true)"
fi

# 3. Emit ranked candidates
echo "=== Pre-built image candidates for ${NAME} ${VERSION} ==="
if [[ -n "$TAG" ]]; then
  echo "[1] Galaxy depot (direct SIF, no auth, no rate-limit) — PREFERRED:"
  echo "    apptainer pull ${NAME}_${TAG}.sif https://depot.galaxyproject.org/singularity/${NAME}:${TAG}"
  echo "[2] biocontainers via quay (anonymous pull is RATE-LIMITED):"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:${TAG}"
  echo "[3] nf-core module (canonical, version-pinned container line):"
  echo "    https://github.com/nf-core/modules/tree/master/modules/nf-core/${NAME}"
  echo
  echo ">> After pull: VERIFY on RHEL 8 — run '<tool> --version' AND exercise one real path."
  echo ">> Watch for: GLIBC_2.xx-not-found, and SSL_CERT_FILE httpx crashes (use --cleanenv to split env-leak from a real defect)."
  echo ">> If verification fails or no image works, fall through to a build: scripts/generate_def.sh ..."
  exit 0
fi
if [[ "$PROBE" -eq 0 ]]; then
  echo "(TAG not yet resolved — offline template; resolve <TAG> = version--buildhash via quay tags):"
  echo "    apptainer pull https://depot.galaxyproject.org/singularity/${NAME}:<TAG>"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:<TAG>"
  exit 0
fi
echo "No biocontainers tag matched '${VERSION}'. Check then build:"
echo "  - nf-core module: https://github.com/nf-core/modules/tree/master/modules/nf-core/${NAME}"
echo "  - tool's official Docker Hub / GHCR image"
echo "  - else from-scratch: scripts/generate_def.sh --name ${NAME} --version ${VERSION} --tier <0|1|2|3> ..."
exit 4
