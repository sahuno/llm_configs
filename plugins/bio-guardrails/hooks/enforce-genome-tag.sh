#!/bin/bash
# Enforce genome build tags in genomic output filenames
# Checks that .bam, .bed, .vcf, .bigwig etc. include a recognized genome build
# BLOCKS if a genomic file is created without a build tag (exit 2)
# Author: Samuel Ahuno
# Date: 2026-02-17

# Portable JSON parsing (prefers jq, falls back to python3, warns loudly
# if neither exists rather than silently passing everything through).
. "${BASH_SOURCE[0]%/*}/lib/json.sh"
json_backend_check || exit 0

INPUT=$(cat)
TOOL_NAME=$(json_get "$INPUT" tool_name)

# Recognized genome build tags (case-insensitive matching)
VALID_TAGS="mm10|mm39|GRCm39|hg38|GRCh38|hg19|GRCh37|t2t|chm13"

# Genomic file extensions that require a build tag
GENOMIC_EXTS='\.(bam|cram|bai|bed|bedgraph|bedMethyl|narrowPeak|broadPeak|vcf|vcf\.gz|bcf|bigwig|bw|bigbed|gtf|gff)(\.gz)?$'

# --- Helper: check if a filepath contains a valid genome tag ---
has_genome_tag() {
  local filepath="$1"
  # Check filename itself
  local basename=$(basename "$filepath")
  if echo "$basename" | grep -qiE "($VALID_TAGS)"; then
    return 0
  fi
  # Check parent directory path
  if echo "$filepath" | grep -qiE "/($VALID_TAGS)/"; then
    return 0
  fi
  return 1
}

# ============================================================
# CHECK: Write/Edit tool — file being created/modified
# ============================================================
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  FILE_PATH=$(json_get "$INPUT" tool_input.file_path)
  [ -z "$FILE_PATH" ] && exit 0

  # Only check genomic file types
  if echo "$FILE_PATH" | grep -qiE "$GENOMIC_EXTS"; then
    if ! has_genome_tag "$FILE_PATH"; then
      echo "BLOCKED: Genomic file '$FILE_PATH' is missing a genome build tag. All genomic output files must include the genome build in both the filename and parent directory. Expected pattern: {sample}.{genome_build}.{description}.{ext} under data/processed/{genome_build}/. Valid tags: mm10, mm39, GRCm39, hg38, GRCh38, hg19, GRCh37, t2t, chm13." >&2
      exit 2
    fi
  fi
fi

# ============================================================
# CHECK: Bash tool — output files in commands
# ============================================================
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(json_get "$INPUT" tool_input.command)
  [ -z "$COMMAND" ] && exit 0

  # Extract output file paths: look for -o, --output, >, >> patterns
  OUTPUT_FILES=$(echo "$COMMAND" | grep -oE '(-o|--output|>+)\s*[^ |;&]+' | sed 's/^[^ ]* *//' | tr -d '"'"'" )

  # Also check samtools sort/index output patterns
  SAMTOOLS_OUT=$(echo "$COMMAND" | grep -oE 'samtools\s+(sort|view|merge)\s+.*-o\s+[^ |;&]+' | grep -oE '\-o\s+[^ |;&]+' | sed 's/-o //')

  # Also check modkit/bedtools output
  TOOL_OUT=$(echo "$COMMAND" | grep -oE '(modkit|bedtools)\s+\S+.*-o\s+[^ |;&]+' | grep -oE '\-o\s+[^ |;&]+' | sed 's/-o //')

  ALL_OUTPUTS="$OUTPUT_FILES $SAMTOOLS_OUT $TOOL_OUT"
  [ -z "$(echo "$ALL_OUTPUTS" | xargs)" ] && exit 0

  for outfile in $ALL_OUTPUTS; do
    # Only check genomic file types
    if echo "$outfile" | grep -qiE "$GENOMIC_EXTS"; then
      if ! has_genome_tag "$outfile"; then
        echo "BLOCKED: Command produces genomic file '$outfile' without a genome build tag. All genomic output files must include the genome build in the filename. Expected pattern: {sample}.{genome_build}.{description}.{ext}. Valid tags: mm10, mm39, GRCm39, hg38, GRCh38, hg19, GRCh37, t2t, chm13." >&2
        exit 2
      fi
    fi
  done
fi

exit 0
