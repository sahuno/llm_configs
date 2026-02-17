#!/bin/bash
# Reference genome validator — catches silent systematic errors
# Detects: build mixing, cross-species contamination, chr naming mismatches, config inconsistency
# BLOCKS on any inconsistency (exit 2)
# Author: Samuel Ahuno
# Date: 2026-02-17

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# --- Helper: extract genome build indicators from a string ---
extract_builds() {
  local text="$1"
  local builds=""
  # Mouse builds
  echo "$text" | grep -qiE '(/|_|^)mm10(/|_|\.|$)' && builds="$builds mm10"
  echo "$text" | grep -qiE '(/|_|^)mm39(/|_|\.|$)' && builds="$builds mm39"
  echo "$text" | grep -qiE '(/|_|^)GRCm39(/|_|\.|$)' && builds="$builds mm39"
  # Human builds
  echo "$text" | grep -qiE '(/|_|^)hg38(/|_|\.|$)' && builds="$builds hg38"
  echo "$text" | grep -qiE '(/|_|^)GRCh38(/|_|\.|$)' && builds="$builds hg38"
  echo "$text" | grep -qiE '(/|_|^)hg19(/|_|\.|$)' && builds="$builds hg19"
  echo "$text" | grep -qiE '(/|_|^)GRCh37(/|_|\.|$)' && builds="$builds hg19"
  echo "$text" | grep -qiE '(/|_|^)t2t(/|_|\.|$)|chm13' && builds="$builds t2t"
  echo "$text" | grep -qiE 'Homo_sapiens_assembly38' && builds="$builds hg38"
  echo "$builds" | xargs -n1 | sort -u | xargs
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
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
  [ -z "$COMMAND" ] && exit 0

  BUILDS=$(extract_builds "$COMMAND")
  BUILD_COUNT=$(echo "$BUILDS" | wc -w | xargs)

  if [ "$BUILD_COUNT" -gt 1 ]; then
    SPECIES=$(get_species "$BUILDS")
    SPECIES_COUNT=$(echo "$SPECIES" | wc -w | xargs)

    if [ "$SPECIES_COUNT" -gt 1 ]; then
      echo "BLOCKED: Cross-species genome mixing detected. Found references to both MOUSE ($( echo "$BUILDS" | grep -oE 'mm10|mm39' | xargs )) and HUMAN ($( echo "$BUILDS" | grep -oE 'hg38|hg19|t2t' | xargs )) in the same command. This is almost certainly an error." >&2
      exit 2
    else
      echo "BLOCKED: Mixed genome builds detected in the same command: $BUILDS. All files in a single operation must use the same genome build. If this is intentional (e.g., liftover), re-run with explicit confirmation." >&2
      exit 2
    fi
  fi
fi

# ============================================================
# CHECK 3: Config consistency (YAML edits)
# ============================================================
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
  [ -z "$FILE_PATH" ] && exit 0

  # Only check YAML config files
  if echo "$FILE_PATH" | grep -qE '\.(yaml|yml)$'; then
    if [ -f "$FILE_PATH" ]; then
      FILE_CONTENT=$(cat "$FILE_PATH" 2>/dev/null)
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
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
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
