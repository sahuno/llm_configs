#!/usr/bin/env bash
# add_to_monorepo.sh — Add a new tool to an existing containers/self_made/ monorepo
# Author: Samuel Ahuno
# Purpose: Clone/update monorepo, add Dockerfile, commit, push, tag
#
# Usage:
#   bash add_to_monorepo.sh \
#     --repo sahuno/softwares \
#     --tool-name samtools \
#     --version 1.21 \
#     --dockerfile /path/to/approved/Dockerfile \
#     --token-var DOCKERHUB_TOKEN

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOW_TEMPLATE="$SKILL_DIR/templates/workflows/monorepo.yml"

# Parse args
REPO=""
TOOL_NAME=""
VERSION=""
DOCKERFILE=""
TOKEN_VAR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)        REPO="$2";       shift 2 ;;
        --tool-name)   TOOL_NAME="$2";  shift 2 ;;
        --version)     VERSION="$2";    shift 2 ;;
        --dockerfile)  DOCKERFILE="$2"; shift 2 ;;
        --token-var)   TOKEN_VAR="$2";  shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

for var in REPO TOOL_NAME VERSION DOCKERFILE TOKEN_VAR; do
    if [[ -z "${!var}" ]]; then
        echo "ERROR: --${var,,} is required"
        exit 1
    fi
done

if [[ ! -f "$DOCKERFILE" ]]; then
    echo "ERROR: Dockerfile not found at: $DOCKERFILE"
    exit 1
fi

REPO_NAME="${REPO##*/}"
CLONE_DIR="/tmp/docker-hpc-monorepo-${REPO_NAME}"

echo "=== Adding ${TOOL_NAME} to monorepo: ${REPO} ==="

# 1. Clone or update the monorepo into a temp dir
if [[ -d "$CLONE_DIR/.git" ]]; then
    echo "[OK] Monorepo already cloned — pulling latest"
    git -C "$CLONE_DIR" pull --ff-only
else
    echo "Cloning $REPO..."
    gh repo clone "$REPO" "$CLONE_DIR"
fi

# 2. Create tool directory
TOOL_DIR="$CLONE_DIR/containers/self_made/${TOOL_NAME}"
mkdir -p "$TOOL_DIR"
cp "$DOCKERFILE" "$TOOL_DIR/Dockerfile"
echo "[OK] Dockerfile placed at containers/self_made/${TOOL_NAME}/Dockerfile"

# 3. Ensure the monorepo workflow is present and up to date
mkdir -p "$CLONE_DIR/.github/workflows"
WORKFLOW_DEST="$CLONE_DIR/.github/workflows/docker-build.yml"
if [[ ! -f "$WORKFLOW_DEST" ]]; then
    cp "$WORKFLOW_TEMPLATE" "$WORKFLOW_DEST"
    echo "[OK] Monorepo workflow installed"
else
    echo "[OK] Monorepo workflow already present"
fi

# 4. Ensure DOCKERHUB_TOKEN secret is set on the monorepo
TOKEN_VALUE="${!TOKEN_VAR}"
gh secret set DOCKERHUB_TOKEN --repo "$REPO" --body "$TOKEN_VALUE"
echo "[OK] DOCKERHUB_TOKEN secret set on $REPO"

# 5. Commit and push
cd "$CLONE_DIR"
git add "containers/self_made/${TOOL_NAME}/" .github/workflows/
git commit -m "Add ${TOOL_NAME} v${VERSION} Docker image" || echo "[INFO] Nothing new to commit"
git push
echo "[OK] Pushed to ${REPO}"

echo ""
echo "=== Ready. Tag to trigger build ==="
echo "  cd $CLONE_DIR"
echo "  git tag ${TOOL_NAME}-v${VERSION} && git push origin ${TOOL_NAME}-v${VERSION}"
echo "  Then monitor: gh run watch --repo ${REPO}"
