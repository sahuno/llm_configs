#!/usr/bin/env bash
# Resolve a site or user profile path by name.
# Author: Samuel Ahuno
#
# Profiles have two independent axes, because two different things were
# previously mixed in one directory:
#
#   sites/  cluster facts — genome paths, container images, SLURM partitions,
#           bind mounts. These change when you change institution.
#   users/  person facts — plot defaults, sample-sheet conventions, DO_NOT
#           rules. These follow you across institutions. (.Rprofile already
#           did macOS/Linux/Windows font detection: it was written to travel.)
#
# Composing them independently means moving institution keeps your plot
# defaults, and a labmate can adopt your site profile without inheriting your
# personal conventions.
#
# Selection, in order:
#   1. $SITE_PROFILE / $USER_PROFILE
#   2. $USER, if profiles/users/$USER exists
#   3. the only profile present, when there is exactly one
#   4. fail loudly — never guess
#
# Usage:
#   site_profile_dir            -> .../profiles/sites/<name>
#   user_profile_dir            -> .../profiles/users/<name>
#   site_file databases.yaml    -> absolute path, or exit 1 naming what is missing
#   user_file matplotlib_defaults

_PROFILES_ROOT="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"

_pick_profile() {          # _pick_profile <axis> <explicit-name>
  local axis="$1" explicit="$2"
  # NB: dir must be its own statement — a `local a=$1 b=$a` self-reference
  # inside one declaration does not resolve reliably across bash versions.
  local dir="$_PROFILES_ROOT/$axis"
  local label="${axis%s}"
  if [ -n "$explicit" ]; then
    if [ -d "$dir/$explicit" ]; then printf '%s' "$dir/$explicit"; return 0; fi
    echo "profiles: $label profile '$explicit' not found in $dir. Available: $(ls "$dir" 2>/dev/null | tr '\n' ' ')" >&2
    return 1
  fi
  # For users only: fall back to the login name when it names a real profile.
  if [ "$axis" = "users" ] && [ -n "${USER:-}" ] && [ -d "$dir/$USER" ]; then
    printf '%s' "$dir/$USER"; return 0
  fi
  # Exactly one candidate (ignoring the example template) is unambiguous.
  local only count
  only=$(ls "$dir" 2>/dev/null | grep -v '^example$' | head -2)
  count=$(printf '%s\n' "$only" | grep -c .)
  if [ "$count" -eq 1 ]; then printf '%s' "$dir/$only"; return 0; fi
  echo "profiles: cannot choose a $label profile — set $(printf %s "$label" | tr a-z A-Z)_PROFILE. Available in $dir: $(ls "$dir" 2>/dev/null | tr '\n' ' ')" >&2
  return 1
}

site_profile_dir() { _pick_profile sites "${SITE_PROFILE:-}"; }
user_profile_dir() { _pick_profile users "${USER_PROFILE:-}"; }

_profile_file() {          # _profile_file <axis-dir> <relative-file>
  local dir="$1" rel="$2"
  [ -z "$dir" ] && return 1
  if [ -e "$dir/$rel" ]; then printf '%s' "$dir/$rel"; return 0; fi
  # Fail loudly and name the key. A silent fallback to a literal path is the
  # failure mode this whole registry exists to remove.
  echo "profiles: '$rel' not found in $(basename "$dir") profile at $dir. Add it there rather than hardcoding a path." >&2
  return 1
}

site_file() { _profile_file "$(site_profile_dir)" "$1"; }
user_file() { _profile_file "$(user_profile_dir)" "$1"; }

# Read one dotted key out of a profile YAML, e.g.
#   site_path containers.cache_dir
# Uses python3; returns non-zero and explains if the key is absent.
site_path() {
  local key="$1" f
  f="$(site_file paths.yaml)" || return 1
  python3 -c '
import sys
try:
    import yaml
except ImportError:
    sys.stderr.write("profiles: python3 yaml module required to read paths.yaml\n"); sys.exit(2)
doc = yaml.safe_load(open(sys.argv[1])) or {}
cur = doc
for part in sys.argv[2].split("."):
    cur = cur.get(part) if isinstance(cur, dict) else None
    if cur is None:
        sys.stderr.write("profiles: key %r not set in %s\n" % (sys.argv[2], sys.argv[1])); sys.exit(1)
print(cur)
' "$f" "$key"
}

# Convenience exports for callers that just want the two directories.
# Naming: *_PROFILE selects by NAME, *_CONFIG is the RESOLVED DIRECTORY.
#   SITE_PROFILE=mskcc-greenbaum  ->  SITE_CONFIG=/.../profiles/sites/mskcc-greenbaum
profiles_export() {
  local s u
  s="$(site_profile_dir)" || return 1
  u="$(user_profile_dir)" || return 1
  export SITE_CONFIG="$s" USER_CONFIG="$u"
}
