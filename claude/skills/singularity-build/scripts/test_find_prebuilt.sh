#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-05-20
# Purpose: Offline tests for find_prebuilt.sh (no network; uses --no-probe).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${HERE}/find_prebuilt.sh"
fail=0

check() { # desc expected_exit actual_exit output needle
  local desc="$1" exp="$2" act="$3" out="$4" needle="$5"
  if [[ "$act" != "$exp" ]]; then echo "FAIL [$desc]: exit $act != $exp"; fail=1; return; fi
  if [[ -n "$needle" ]] && ! grep -qF "$needle" <<<"$out"; then
    echo "FAIL [$desc]: output missing '$needle'"; fail=1; return; fi
  echo "PASS [$desc]"
}

# Case 1: missing --version -> usage, exit 2
out="$("$SCRIPT" --name samtools 2>&1)"; check "missing-version" 2 "$?" "$out" ""

# Case 2: --no-probe prints the Galaxy depot template, exit 0
out="$("$SCRIPT" --name samtools --version 1.21 --no-probe --catalog /dev/null 2>&1)"
check "no-probe-template" 0 "$?" "$out" "depot.galaxyproject.org/singularity/samtools:<TAG>"

# Case 3: catalog hit -> exit 3
tmp="$(mktemp)"; printf 'samtools:\n  sif: /path/samtools_1.21.sif\n' >"$tmp"
out="$("$SCRIPT" --name samtools --version 1.21 --no-probe --catalog "$tmp" 2>&1)"
check "catalog-hit" 3 "$?" "$out" "ALREADY REGISTERED"
rm -f "$tmp"

[[ "$fail" -eq 0 ]] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
