#!/usr/bin/env bash
# setup_repo.sh — Create a standalone GitHub repo with Docker CI
# Author: Samuel Ahuno
# Purpose: git init, copy workflow, create GitHub repo, set secret, commit and push
#
# Usage:
#   bash setup_repo.sh \
#     --tool-name samtools \
#     --version 1.21 \
#     --dockerfile /path/to/approved/Dockerfile \
#     --docker-user sahuno \
#     --token-var DOCKERHUB_TOKEN \
#     [--visibility public|private]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOW_TEMPLATE="$SKILL_DIR/templates/workflows/standalone.yml"

# Parse args
TOOL_NAME=""
VERSION=""
DOCKERFILE=""
DOCKER_USER=""
TOKEN_VAR=""
VISIBILITY="public"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool-name)   TOOL_NAME="$2";   shift 2 ;;
        --version)     VERSION="$2";     shift 2 ;;
        --dockerfile)  DOCKERFILE="$2";  shift 2 ;;
        --docker-user) DOCKER_USER="$2"; shift 2 ;;
        --token-var)   TOKEN_VAR="$2";   shift 2 ;;
        --visibility)  VISIBILITY="$2";  shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Validate required args
for var in TOOL_NAME VERSION DOCKERFILE DOCKER_USER TOKEN_VAR; do
    if [[ -z "${!var}" ]]; then
        echo "ERROR: --${var,,} is required"
        exit 1
    fi
done

if [[ ! -f "$DOCKERFILE" ]]; then
    echo "ERROR: Dockerfile not found at: $DOCKERFILE"
    exit 1
fi

REPO_NAME="${TOOL_NAME}-docker"
GH_USER=$(gh api user --jq '.login')
FULL_REPO="${GH_USER}/${REPO_NAME}"

echo "=== Setting up standalone repo: $FULL_REPO ==="

# 1. Init git repo if not already
if [[ ! -d .git ]]; then
    git init
    echo "[OK] git init"
fi

# 2. Copy Dockerfile to current dir (if not already here)
if [[ "$(realpath "$DOCKERFILE")" != "$(realpath ./Dockerfile)" ]]; then
    cp "$DOCKERFILE" ./Dockerfile
    echo "[OK] Dockerfile copied"
fi

# 3. Create .github/workflows dir and copy workflow
mkdir -p .github/workflows
# Substitute tool name and docker user into workflow template
sed \
    -e "s|{{TOOL_NAME}}|${TOOL_NAME}|g" \
    -e "s|{{DOCKER_USER}}|${DOCKER_USER}|g" \
    "$WORKFLOW_TEMPLATE" > .github/workflows/docker-build.yml
echo "[OK] Workflow written to .github/workflows/docker-build.yml"

# 4. Create .gitignore
cat > .gitignore <<'EOF'
*.sif
*.img
*.log
__pycache__/
EOF

# 5. Initial commit
git add Dockerfile .github/workflows/docker-build.yml .gitignore
git commit -m "Add Dockerfile and GitHub Actions CI for ${TOOL_NAME} v${VERSION}" || true

# 6. Create GitHub repo
if gh repo view "$FULL_REPO" &>/dev/null 2>&1; then
    echo "[WARN] Repo $FULL_REPO already exists — skipping creation"
else
    gh repo create "$FULL_REPO" --"$VISIBILITY" --source=. \
        --description "${TOOL_NAME} Docker image for HPC (built via GitHub Actions)"
    echo "[OK] GitHub repo created: https://github.com/$FULL_REPO"
fi

# 7. Set DOCKERHUB_TOKEN secret
TOKEN_VALUE="${!TOKEN_VAR}"
gh secret set DOCKERHUB_TOKEN --repo "$FULL_REPO" --body "$TOKEN_VALUE"
echo "[OK] DOCKERHUB_TOKEN secret set on $FULL_REPO"

# 8. Push
git branch -M main
git push -u origin main
echo "[OK] Pushed to origin/main"

echo ""
echo "=== Repo ready. Tag to trigger build ==="
echo "  git tag v${VERSION} && git push origin v${VERSION}"
echo "  Image will be: ${DOCKER_USER}/${TOOL_NAME}:${VERSION}"
