#!/usr/bin/env bash
# preflight.sh — Verify all prerequisites for the docker-hpc skill
# Author: Samuel Ahuno
# Purpose: Check git, gh CLI, Docker Hub token, and username before any git ops

set -euo pipefail

PASS="[OK]"
FAIL="[FAIL]"
WARN="[WARN]"
errors=0

echo "=== docker-hpc preflight checks ==="
echo ""

# 1. git
if command -v git &>/dev/null; then
    echo "$PASS git: $(git --version)"
else
    echo "$FAIL git: not found. Install git and re-run."
    errors=$((errors + 1))
fi

# 2. gh CLI — installed
if command -v gh &>/dev/null; then
    echo "$PASS gh CLI: $(gh --version | head -1)"
else
    echo "$FAIL gh CLI: not found."
    echo "       Install: https://cli.github.com/"
    errors=$((errors + 1))
fi

# 3. gh CLI — authenticated
if gh auth status &>/dev/null 2>&1; then
    GH_USER=$(gh api user --jq '.login' 2>/dev/null || echo "unknown")
    echo "$PASS gh auth: logged in as $GH_USER"
else
    echo "$FAIL gh auth: not authenticated. Run: gh auth login"
    errors=$((errors + 1))
fi

# 4. gh CLI — required scopes
SCOPES=$(gh auth status 2>&1 | grep "Token scopes" || true)
for scope in repo workflow "write:packages"; do
    if echo "$SCOPES" | grep -q "$scope"; then
        echo "$PASS gh scope '$scope': present"
    else
        echo "$WARN gh scope '$scope': not detected (may cause push failures)"
        echo "       Re-auth with: gh auth refresh -s repo,workflow,write:packages"
    fi
done

# 5. Docker Hub token
TOKEN_VAR=""
DOCKER_TOKEN_VALUE=""

if [[ -n "${DOCKERHUB_TOKEN:-}" ]]; then
    echo "$PASS DOCKERHUB_TOKEN: set"
    TOKEN_VAR="DOCKERHUB_TOKEN"
    DOCKER_TOKEN_VALUE="$DOCKERHUB_TOKEN"
elif [[ -n "${APPTAINER_DOCKER_PASSWORD:-}" ]]; then
    echo "$WARN DOCKERHUB_TOKEN: not set"
    echo "      Falling back to APPTAINER_DOCKER_PASSWORD."
    echo "      Verify this token has Docker Hub READ+WRITE scope before pushing."
    TOKEN_VAR="APPTAINER_DOCKER_PASSWORD"
    DOCKER_TOKEN_VALUE="$APPTAINER_DOCKER_PASSWORD"
else
    echo "$FAIL No Docker Hub token found."
    echo "      Set DOCKERHUB_TOKEN in your environment or ~/.bashrc"
    echo "      Generate one at: hub.docker.com → Account Settings → Security"
    echo "      Required scope: Read, Write, Delete"
    errors=$((errors + 1))
fi

# 6. Docker Hub username
DOCKER_USER=""
if [[ -n "${APPTAINER_DOCKER_USERNAME:-}" ]]; then
    DOCKER_USER="$APPTAINER_DOCKER_USERNAME"
    echo "$PASS Docker Hub username: $DOCKER_USER (from APPTAINER_DOCKER_USERNAME)"
elif [[ -n "${DOCKERHUB_USERNAME:-}" ]]; then
    DOCKER_USER="$DOCKERHUB_USERNAME"
    echo "$PASS Docker Hub username: $DOCKER_USER (from DOCKERHUB_USERNAME)"
else
    # Fall back to gh auth username — usually matches Docker Hub for solo developers
    DOCKER_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
    if [[ -n "$DOCKER_USER" ]]; then
        echo "$WARN Docker Hub username: using GitHub login '$DOCKER_USER' as fallback"
        echo "      Set DOCKERHUB_USERNAME in ~/.bashrc if your Docker Hub username differs."
    else
        echo "$FAIL Cannot determine Docker Hub username."
        echo "      Set DOCKERHUB_USERNAME=<your-dockerhub-username> in ~/.bashrc"
        errors=$((errors + 1))
    fi
fi

echo ""

if [[ $errors -gt 0 ]]; then
    echo "=== PREFLIGHT FAILED ($errors error(s)) — fix above before continuing ==="
    exit 1
fi

echo "=== PREFLIGHT PASSED ==="
echo ""
# Emit variables for capture by caller
echo "DOCKER_USER=$DOCKER_USER"
echo "DOCKER_TOKEN_VAR=$TOKEN_VAR"
