#!/usr/bin/env bash
# detect_context.sh — Detect standalone vs monorepo mode
# Author: Samuel Ahuno
# Purpose: Check if user has a containers/self_made/ monorepo via gh repo list
#
# Output (stdout):
#   MODE=standalone
#   MODE=monorepo REPO=<owner/repo>
#
# Bug fix: use gh api exit code (0=found, non-zero=404) instead of parsing
# HTTP headers — header parsing breaks under set -euo pipefail because head -1
# sends SIGPIPE to gh api, making the pipeline fail, causing || echo 404 to
# append a second line to the status variable.

set -euo pipefail

# Get authenticated GitHub username
GH_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
if [[ -z "$GH_USER" ]]; then
    echo "MODE=standalone"
    exit 0
fi

# List repos (up to 100) and check each for the fingerprint path via API.
# Redirect gh api stdin from /dev/null so it doesn't compete with the while
# loop's herestring for stdin.
REPOS=$(gh repo list "$GH_USER" --limit 100 --json nameWithOwner \
    --jq '.[].nameWithOwner' 2>/dev/null || echo "")

if [[ -z "$REPOS" ]]; then
    echo "MODE=standalone"
    exit 0
fi

while IFS= read -r repo; do
    if gh api "repos/${repo}/contents/containers/self_made" \
            --silent </dev/null 2>/dev/null; then
        echo "MODE=monorepo REPO=$repo"
        exit 0
    fi
done <<< "$REPOS"

echo "MODE=standalone"
