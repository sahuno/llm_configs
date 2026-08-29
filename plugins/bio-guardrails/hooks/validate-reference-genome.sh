#!/bin/bash
# Reference genome validator — catches silent systematic errors
# Detects: build mixing, cross-species contamination, chr naming mismatches, config inconsistency
# BLOCKS on any inconsistency (exit 2)
# Author: Samuel Ahuno
# Date: 2026-02-17

# Portable JSON parsing (prefers jq, falls back to python3, warns loudly
# if neither exists rather than silently passing everything through).
. "${BASH_SOURCE[0]%/*}/lib/json.sh"
json_backend_check || exit 0

INPUT=$(cat)
TOOL_NAME=$(json_get "$INPUT" tool_name)

# --- Helper: extract genome build indicators from a string ---
extract_builds() {
  local text="$1"
  local builds=""
  # Delimiters: the leading class MUST include '.' — the mandated filename
  # convention is {sample}.{build}.{description}.{ext} (CLAUDE.md §2), so a
  # leading class of (/|_|^) made every correctly-named file invisible to this
  # check. `samtools merge o.bam s.hg38.bam s.mm10.bam` passed silently.
  # Mouse builds
  echo "$text" | grep -qiE '(/|_|\.|^)mm10(/|_|\.|$)' && builds="$builds mm10"
  echo "$text" | grep -qiE '(/|_|\.|^)mm39(/|_|\.|$)' && builds="$builds mm39"
  echo "$text" | grep -qiE '(/|_|\.|^)GRCm39(/|_|\.|$)' && builds="$builds mm39"
  # Human builds
  echo "$text" | grep -qiE '(/|_|\.|^)hg38(/|_|\.|$)' && builds="$builds hg38"
  echo "$text" | grep -qiE '(/|_|\.|^)GRCh38(/|_|\.|$)' && builds="$builds hg38"
  echo "$text" | grep -qiE '(/|_|\.|^)hg19(/|_|\.|$)' && builds="$builds hg19"
  echo "$text" | grep -qiE '(/|_|\.|^)GRCh37(/|_|\.|$)' && builds="$builds hg19"
  echo "$text" | grep -qiE '(/|_|\.|^)t2t(/|_|\.|$)|chm13' && builds="$builds t2t"
  echo "$text" | grep -qiE 'Homo_sapiens_assembly38' && builds="$builds hg38"
  echo "$builds" | xargs -n1 | sort -u | xargs
}

# --- Helper: is this a deliberate coordinate conversion? ---
# CLAUDE.md §2 mandates liftOver for multi-build work and mandates naming the
# output with BOTH builds ({sample}.mm39_to_mm10.lifted.bed). Without this
# exemption, fixing the delimiter class above would block the exact workflow
# the instructions require — and would keep blocking every later command that
# touches the resulting file. Applies to SAME-SPECIES mixing only; mixing mouse
# with human is never a legitimate liftOver.
is_intentional_conversion() {
  local text="$1"
  echo "$text" | grep -qiE 'liftover|crossmap|\.chain\b|_to_|ALLOW_BUILD_MIX=1' && return 0
  [ "${ALLOW_BUILD_MIX:-}" = "1" ] && return 0
  return 1
}

# --- Helper: classify species from builds ---
get_species() {
  local builds="$1"
  local species=""
  echo "$builds" | grep -qE 'mm10|mm39' && species="$species mouse"
  echo "$builds" | grep -qE 'hg38|hg19|t2t' && species="$species human"
  echo "$species" | xargs -n1 | sort -u | xargs
}

# ============================================================
# CHECK 1 & 2: Build mixing + Cross-species (Bash commands)
# ============================================================
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(json_get "$INPUT" tool_input.command)
  [ -z "$COMMAND" ] && exit 0

  BUILDS=$(extract_builds "$COMMAND")
  BUILD_COUNT=$(echo "$BUILDS" | wc -w | xargs)

  if [ "$BUILD_COUNT" -gt 1 ]; then
    SPECIES=$(get_species "$BUILDS")
    SPECIES_COUNT=$(echo "$SPECIES" | wc -w | xargs)

    if [ "$SPECIES_COUNT" -gt 1 ]; then
      # Never exempt: no legitimate liftOver crosses species.
      echo "BLOCKED: Cross-species genome mixing detected. Found references to both MOUSE ($( echo "$BUILDS" | grep -oE 'mm10|mm39' | xargs )) and HUMAN ($( echo "$BUILDS" | grep -oE 'hg38|hg19|t2t' | xargs )) in the same command. This is almost certainly an error." >&2
      exit 2
    elif is_intentional_conversion "$COMMAND"; then
      echo "NOTE: multiple builds ($BUILDS) in one command, allowed as a coordinate conversion. Store both original and lifted coordinates, and verify unmapped regions before proceeding (CLAUDE.md §2)." >&2
      exit 0
    else
      echo "BLOCKED: Mixed genome builds detected in the same command: $BUILDS. All files in a single operation must use the same genome build. If this is a deliberate coordinate conversion, use liftOver/CrossMap, or re-run with ALLOW_BUILD_MIX=1 prefixed to the command." >&2
      exit 2
    fi
  fi
fi

# ============================================================
# CHECK 3: Config consistency (YAML edits)
# ============================================================
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  FILE_PATH=$(json_get "$INPUT" tool_input.file_path)
  [ -z "$FILE_PATH" ] && exit 0

  # Only check YAML config files
  if echo "$FILE_PATH" | grep -qE '\.(yaml|yml)$'; then
    # Validate the content being WRITTEN, not what is already on disk. Reading
    # $FILE_PATH here meant a fresh Write checked nothing (the file does not
    # exist yet) and an Edit checked the pre-edit state — so an edit that
    # introduced a second build passed, and the hook only ever fired on damage
    # that had already landed.
    if [ "$TOOL_NAME" = "Write" ]; then
      FILE_CONTENT=$(json_get "$INPUT" tool_input.content)
    else
      # Edit: reconstruct the post-edit text so the resulting file is judged.
      # Falls back to the replacement fragment alone, which under-detects but
      # never false-positives — this hook blocks, so a wrong block is costly.
      NEW_STRING=$(json_get "$INPUT" tool_input.new_string)
      OLD_STRING=$(json_get "$INPUT" tool_input.old_string)
      FILE_CONTENT=""
      if [ -f "$FILE_PATH" ] && command -v python3 >/dev/null 2>&1; then
        FILE_CONTENT=$(python3 -c '
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    text = open(path).read()
except Exception:
    text = ""
print(text.replace(old, new) if old else text + "\n" + new)
' "$FILE_PATH" "$OLD_STRING" "$NEW_STRING" 2>/dev/null)
      fi
      [ -z "$FILE_CONTENT" ] && FILE_CONTENT="$NEW_STRING"
    fi

    if [ -n "$FILE_CONTENT" ]; then
      BUILDS=$(extract_builds "$FILE_CONTENT")
      BUILD_COUNT=$(echo "$BUILDS" | wc -w | xargs)

      if [ "$BUILD_COUNT" -gt 1 ]; then
        SPECIES=$(get_species "$BUILDS")
        SPECIES_COUNT=$(echo "$SPECIES" | wc -w | xargs)

        # Config files listing multiple builds for reference (like databases_config.yaml) are OK
        # Only flag if it looks like a single-sample/single-pipeline config
        if echo "$FILE_PATH" | grep -qiE 'database|reference|genomes'; then
          exit 0
        fi

        if [ "$SPECIES_COUNT" -gt 1 ]; then
          echo "BLOCKED: Config file $FILE_PATH references both mouse and human genome builds: $BUILDS. A single pipeline config should reference one genome build." >&2
          exit 2
        else
          echo "BLOCKED: Config file $FILE_PATH references multiple builds of the same species: $BUILDS. Verify this is intentional (e.g., not mixing hg38 FASTA with hg19 GTF)." >&2
          exit 2
        fi
      fi
    fi
  fi
fi

# ============================================================
# CHECK 4: Chr naming convention (BED/GTF referenced in commands)
# ============================================================
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(json_get "$INPUT" tool_input.command)
  [ -z "$COMMAND" ] && exit 0

  # Extract .bed, .gtf, .gff, .vcf file paths from the command
  GENOMIC_FILES=$(echo "$COMMAND" | grep -oE '[^ "'"'"']+\.(bed|gtf|gff|gff3|vcf)(\.gz)?' | head -5)
  [ -z "$GENOMIC_FILES" ] && exit 0

  HAS_CHR_PREFIX=""
  HAS_NO_PREFIX=""

  for gfile in $GENOMIC_FILES; do
    [ ! -f "$gfile" ] && continue

    # Read first non-comment, non-header line
    if echo "$gfile" | grep -qE '\.gz$'; then
      FIRST_LINE=$(zcat "$gfile" 2>/dev/null | grep -v '^#' | grep -v '^track' | head -1)
    else
      FIRST_LINE=$(grep -v '^#' "$gfile" | grep -v '^track' | head -1)
    fi
    [ -z "$FIRST_LINE" ] && continue

    FIRST_COL=$(echo "$FIRST_LINE" | cut -f1)
    if echo "$FIRST_COL" | grep -qE '^chr'; then
      HAS_CHR_PREFIX="yes"
    elif echo "$FIRST_COL" | grep -qE '^[0-9XYM]'; then
      HAS_NO_PREFIX="yes"
    fi
  done

  if [ -n "$HAS_CHR_PREFIX" ] && [ -n "$HAS_NO_PREFIX" ]; then
    echo "BLOCKED: Chromosome naming convention mismatch detected. Some files use 'chr' prefix (UCSC-style) and others do not (Ensembl-style). This will cause silent data loss in bedtools, intersections, and most genomic tools. Standardize naming before proceeding." >&2
    exit 2
  fi
fi

exit 0
