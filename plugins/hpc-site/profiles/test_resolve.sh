#!/usr/bin/env bash
# Tests for profile resolution. Author: Samuel Ahuno
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0; FAIL=0
t() { # t <name> <expected-exit> <command...>
  local name="$1" want="$2"; shift 2
  ( "$@" ) >/dev/null 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then PASS=$((PASS+1)); printf '  ok   %-52s (exit %d)\n' "$name" "$got"
  else FAIL=$((FAIL+1)); printf '  FAIL %-52s want %d got %d\n' "$name" "$want" "$got"; fi
}
eq() { # eq <name> <expected> <actual>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  FAIL %s\n       want %s\n       got  %s\n' "$1" "$2" "$3"; fi
}
. "$HERE/resolve.sh"

eq "site auto-selects the one real profile" "$HERE/sites/mskcc-greenbaum" "$(site_profile_dir)"
eq "user falls back to \$USER"               "$HERE/users/$USER"          "$(USER_PROFILE= user_profile_dir)"
eq "explicit SITE_PROFILE wins"              "$HERE/sites/example"        "$(SITE_PROFILE=example site_profile_dir)"
eq "site_file resolves"                      "$HERE/sites/mskcc-greenbaum/databases.yaml" "$(site_file databases.yaml)"
eq "dotted key lookup"                       "/data1/greenbab/users/ahunos/apptainer_cache" "$(site_path containers.cache_dir)"
t  "unknown profile fails loudly"      1 env SITE_PROFILE=nope bash -c ". $HERE/resolve.sh; site_profile_dir"
t  "missing file fails loudly"         1 bash -c ". $HERE/resolve.sh; site_file nope.yaml"
t  "missing key fails loudly"          1 bash -c ". $HERE/resolve.sh; site_path containers.nope"
t  "profiles_export succeeds"          0 bash -c ". $HERE/resolve.sh; profiles_export"

# ambiguity must not be guessed
mkdir -p "$HERE/sites/_tmp_second"
t  "two real sites -> ambiguous, no guess" 1 bash -c ". $HERE/resolve.sh; site_profile_dir"
rmdir "$HERE/sites/_tmp_second"

echo "──────────────────────────────────────────"
printf 'passed %d   failed %d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
