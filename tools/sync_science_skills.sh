#!/usr/bin/env bash
# Track hand-authored Claude Science skills in this repo.
# Author: Samuel Ahuno
#
# THE PROBLEM
#
# Skills you write land in ~/.claude-science/orgs/<uuid>/skills/, which is
# application state, not a workspace. That tree also holds a multi-hundred-MB
# SQLite database, OAuth tokens, an encryption key and a daemon socket — so it
# cannot be version controlled as-is, and committing it would leak secrets.
#
# It is also rewritten by releases. Every vendor skill in that directory carries
# the same mtime: the release drop. `claude-science update` self-updates and can
# roll back to an arbitrary build. Anything you authored there is one upgrade
# away from being replaced or removed, and it exists in no other location — the
# release bundle at runtime/<version>/skills does not contain it.
#
# THE APPROACH
#
# Source of truth lives here, in git, under science-skills/. This script moves
# copies between here and the app directory and, more importantly, tells you
# when they have diverged — which is what you want to know after an upgrade.
#
# Copies rather than symlinks: a release that rewrites the skills directory
# would replace a symlink with a real directory, silently detaching your source
# of truth at exactly the moment you needed it. A copy that drifts is visible;
# a detached symlink is not.
#
# Usage:
#   sync_science_skills.sh status   # what differs, and in which direction
#   sync_science_skills.sh pull     # app -> repo  (capture edits made in the UI)
#   sync_science_skills.sh push     # repo -> app  (restore after an upgrade)

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

REPO_DIR="science-skills"
DATA_DIR="${CLAUDE_SCIENCE_HOME:-$HOME/.claude-science}"
ACTIVE="$DATA_DIR/active-org.json"

# Resolve the active org rather than hardcoding a UUID — it changes per account
# and per machine.
if [ -n "${CLAUDE_SCIENCE_ORG:-}" ]; then
  ORG="$CLAUDE_SCIENCE_ORG"
elif [ -f "$ACTIVE" ]; then
  ORG=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('org_uuid',''))" "$ACTIVE" 2>/dev/null)
else
  ORG=""
fi
if [ -z "$ORG" ]; then
  echo "Cannot determine the active org. Set CLAUDE_SCIENCE_ORG, or check $ACTIVE" >&2
  exit 1
fi

APP_DIR="$DATA_DIR/orgs/$ORG/skills"
RELEASE_DIR=$(ls -d "$DATA_DIR"/runtime/*/skills 2>/dev/null | tail -1)

[ -d "$APP_DIR" ] || { echo "No skills directory at $APP_DIR" >&2; exit 1; }
mkdir -p "$REPO_DIR"

# Tracked = whatever is already in science-skills/. Adding one is deliberate:
# `pull <name>`. Absence from the release bundle is a useful hint that a skill
# was authored rather than shipped, but it is only a hint — org-synced product
# skills also fail that test, and vendoring those would be wrong.
tracked() { find "$REPO_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; 2>/dev/null | sort; }

# Candidates: in the app, not shipped by the release, not yet tracked.
candidates() {
  [ -n "$RELEASE_DIR" ] || return 0
  comm -23 <(comm -23 <(ls "$APP_DIR" | sort) <(ls "$RELEASE_DIR" | sort)) <(tracked)
}

cmd="${1:-status}"
CHANGED=0

case "$cmd" in
  status)
    printf '%-34s %s\n' "TRACKED SKILL" "STATE"
    printf '%-34s %s\n' "$(printf '─%.0s' $(seq 1 13))" "$(printf '─%.0s' $(seq 1 5))"
    for s in $(tracked); do
      in_repo=0; in_app=0
      [ -d "$REPO_DIR/$s" ] && in_repo=1
      [ -d "$APP_DIR/$s" ] && in_app=1
      if   [ $in_repo -eq 1 ] && [ $in_app -eq 0 ]; then
        printf '%-34s \033[31mMISSING FROM APP\033[0m — an upgrade may have removed it; run push\n' "$s"; CHANGED=1
      # .sync-org and .catalog_stamp are stripped on pull, so a raw diff always
      # reports them as differences. Exclude them or every skill reads as drifted
      # and the signal this tool exists to give becomes noise.
      elif diff -rq -x '.sync-org' -x '.catalog_stamp' "$REPO_DIR/$s" "$APP_DIR/$s" >/dev/null 2>&1; then
        printf '%-34s in sync\n' "$s"
      else
        newer=$([ "$APP_DIR/$s" -nt "$REPO_DIR/$s" ] && echo "app is newer — pull" || echo "repo is newer — push")
        printf '%-34s \033[33mDIFFERS\033[0m — %s\n' "$s" "$newer"; CHANGED=1
      fi
    done
    [ -z "$(tracked)" ] && echo "  (nothing tracked yet)"
    echo
    cand=$(candidates)
    if [ -n "$cand" ]; then
      echo "Not shipped by the release, and not tracked here — candidates for 'pull <name>':"
      for c in $cand; do printf '  %s\n' "$c"; done
      echo "  (some of these may be org-synced product skills; track only what you wrote)"
      echo
    fi
    [ -n "$RELEASE_DIR" ] && echo "Release bundle: $(ls "$RELEASE_DIR" | wc -l | tr -d ' ') vendor skills at $RELEASE_DIR (never tracked)"
    [ $CHANGED -eq 0 ] && [ -n "$(tracked)" ] && echo "Everything tracked is in sync."
    exit $CHANGED
    ;;
  pull)
    # With arguments: adopt those skills. Without: refresh what is already tracked.
    list="${*:2}"; [ -z "$list" ] && list=$(tracked)
    for s in $list; do
      [ -d "$APP_DIR/$s" ] || { echo "  skip $s — not in $APP_DIR" >&2; continue; }
      rm -rf "${REPO_DIR:?}/$s"; cp -R "$APP_DIR/$s" "$REPO_DIR/$s"
      # App-managed metadata: .sync-org carries the org UUID (an account
      # identifier), .catalog_stamp is a timestamp rewritten on every sync and
      # would produce a diff on every pull. Neither is content; the app
      # regenerates both.
      find "$REPO_DIR/$s" -name '.sync-org' -o -name '.catalog_stamp' | xargs rm -f 2>/dev/null
      echo "  pulled $s"
    done
    echo "Review with 'git diff' before committing."
    ;;
  push)
    for s in $(tracked); do
      rm -rf "${APP_DIR:?}/$s"; cp -R "$REPO_DIR/$s" "$APP_DIR/$s"
      echo "  pushed $s"
    done
    echo "Restart the daemon if it caches the skill list: claude-science stop && claude-science serve"
    ;;
  *)
    echo "usage: $0 status | pull [skill...] | push" >&2; exit 2 ;;
esac
