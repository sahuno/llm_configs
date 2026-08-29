#!/bin/bash
# Portable JSON field extraction for hook scripts.
# Author: Samuel Ahuno
#
# Why this exists: every guardrail used to start with `jq -r ...`. On a machine
# without jq the hooks produced empty fields, took the `[ -z "$X" ] && exit 0`
# early-out, and passed everything through — silently. A guardrail that
# silently stops guarding is worse than no guardrail, because it buys false
# confidence. This prefers jq, falls back to python3, and if neither exists
# says so loudly instead of pretending to work.

if command -v jq >/dev/null 2>&1; then
  _JSON_BACKEND="jq"
elif command -v python3 >/dev/null 2>&1; then
  _JSON_BACKEND="python3"
else
  _JSON_BACKEND=""
fi

# Emit a loud warning when no JSON backend is available. Call once per hook,
# before any json_get. Returns 1 so callers can exit 0 without pretending the
# check succeeded.
json_backend_check() {
  if [ -z "$_JSON_BACKEND" ]; then
    echo "bio-guardrails: neither jq nor python3 found on PATH. Safety hooks CANNOT parse tool input and are passing everything through unchecked. Install jq or python3 to restore protection." >&2
    return 1
  fi
  return 0
}

# json_get <json-text> <dotted.path> [<fallback.path> ...]
# Prints the first path that resolves to a non-empty value; prints nothing
# otherwise. Paths use dots, without a leading dot: "tool_input.command".
json_get() {
  local json="$1"; shift
  [ -z "$_JSON_BACKEND" ] && return 0
  [ $# -eq 0 ] && return 0

  if [ "$_JSON_BACKEND" = "jq" ]; then
    local expr="" p
    for p in "$@"; do expr="${expr}.${p} // "; done
    expr="${expr}empty"
    printf '%s' "$json" | jq -r "$expr" 2>/dev/null
  else
    printf '%s' "$json" | python3 -c '
import json, sys
try:
    doc = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for path in sys.argv[1:]:
    cur = doc
    for key in path.split("."):
        cur = cur.get(key) if isinstance(cur, dict) else None
        if cur is None:
            break
    if cur is None or cur == "":
        continue
    print(cur if isinstance(cur, str) else json.dumps(cur))
    break
' "$@" 2>/dev/null
  fi
}
