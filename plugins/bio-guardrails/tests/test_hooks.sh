#!/usr/bin/env bash
# Behavioural test suite for the bio-guardrails hooks.
# Author: Samuel Ahuno
#
# Usage:
#   ./tests/test_hooks.sh              # run with the default JSON backend
#   JSON_BACKEND=python3 ./tests/...   # force the python3 fallback path
#
# Exit codes under test: 0 = allow (warnings still print to stderr), 2 = block.

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../hooks" && pwd)"
PASS=0; FAIL=0; FAILED_NAMES=()

# check <hook> <expected-exit> <name> <json>
check() {
  local hook="$1" want="$2" name="$3" json="$4"
  local got out
  out=$(printf '%s' "$json" | "$HOOKS/$hook" 2>&1); got=$?
  if [ "$got" -eq "$want" ]; then
    PASS=$((PASS+1)); printf '  \033[32mok\033[0m   %-58s (exit %d)\n' "$name" "$got"
  else
    FAIL=$((FAIL+1)); FAILED_NAMES+=("$name")
    printf '  \033[31mFAIL\033[0m %-58s want %d got %d\n' "$name" "$want" "$got"
    [ -n "$out" ] && printf '       └─ %s\n' "$(echo "$out" | head -1 | cut -c1-100)"
  fi
}

bash_cmd() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
write_file() { printf '{"tool_name":"Write","tool_input":{"file_path":"%s","content":"%s"}}' "$1" "${2:-x}"; }

echo "=== block-dangerous-commands ==="
check block-dangerous-commands.sh 0 "benign command"            "$(bash_cmd 'echo hello')"
check block-dangerous-commands.sh 2 "rm -rf on data root"        "$(bash_cmd 'rm -rf /data1/greenbab/db')"
check block-dangerous-commands.sh 2 "rm -rf ."                   "$(bash_cmd 'rm -rf .')"
check block-dangerous-commands.sh 2 "snakemake --reason"         "$(bash_cmd 'snakemake --reason -n')"

echo "=== block-raw-data-writes ==="
check block-raw-data-writes.sh 0 "write to processed"            "$(write_file 'data/processed/hg38/a.hg38.bed')"
check block-raw-data-writes.sh 2 "write into data/raw"           "$(write_file 'data/raw/sample.fastq')"

echo "=== enforce-genome-tag ==="
check enforce-genome-tag.sh 0 "tagged bam (dot convention)"       "$(write_file 'data/processed/hg38/p01.hg38.sorted.bam')"
check enforce-genome-tag.sh 0 "non-genomic file exempt"           "$(write_file 'src/01_align.py')"
check enforce-genome-tag.sh 0 "raw fastq exempt"                  "$(write_file 'data/raw/s.fastq')"
check enforce-genome-tag.sh 2 "untagged bam"                      "$(write_file 'results/aligned.bam')"

echo "=== validate-reference-genome: single build (allow) ==="
check validate-reference-genome.sh 0 "one build, dot form"        "$(bash_cmd 'samtools sort a.hg38.bam')"
check validate-reference-genome.sh 0 "one build, dir form"        "$(bash_cmd 'samtools sort data/processed/hg38/a.bam')"

echo "=== validate-reference-genome: CROSS-SPECIES (must block, all delimiters) ==="
check validate-reference-genome.sh 2 "cross-species, slash form"  "$(bash_cmd 'samtools merge o.bam data/processed/hg38/a.bam data/processed/mm10/b.bam')"
check validate-reference-genome.sh 2 "cross-species, underscore"  "$(bash_cmd 'samtools merge o.bam s_hg38_a.bam s_mm10_b.bam')"
check validate-reference-genome.sh 2 "cross-species, DOT form"    "$(bash_cmd 'samtools merge o.bam s.hg38.bam s.mm10.bam')"

echo "=== validate-reference-genome: same-species build mix (must block) ==="
check validate-reference-genome.sh 2 "mm10+mm39, dot form"        "$(bash_cmd 'bedtools intersect -a x.mm10.bed -b y.mm39.bed')"
check validate-reference-genome.sh 2 "mm10+mm39, underscore"      "$(bash_cmd 'bedtools intersect -a x_mm10_a.bed -b y_mm39_b.bed')"

echo "=== validate-reference-genome: liftOver must be ALLOWED (CLAUDE.md mandates it) ==="
check validate-reference-genome.sh 0 "liftOver invocation"        "$(bash_cmd 'liftOver in.mm39.bed mm39ToMm10.chain out.mm10.bed unmapped.bed')"
check validate-reference-genome.sh 0 "CrossMap invocation"        "$(bash_cmd 'CrossMap.py bed mm39ToMm10.chain in.mm39.bed out.mm10.bed')"
check validate-reference-genome.sh 0 "mandated _to_ filename"     "$(bash_cmd 'wc -l s.mm39_to_mm10.lifted.bed')"
check validate-reference-genome.sh 0 "explicit ALLOW_BUILD_MIX"   "$(bash_cmd 'ALLOW_BUILD_MIX=1 bedtools intersect -a x.mm10.bed -b y.mm39.bed')"
check validate-reference-genome.sh 2 "cross-species NOT exempt by liftOver" "$(bash_cmd 'liftOver in.hg38.bed hg38ToMm10.chain out.mm10.bed')"

echo "=== warn-only hooks (must never block) ==="
check warn-absolute-paths.sh    0 "absolute path warns only"      "$(write_file 'src/a.py' 'p = \"/data1/x\"')"
check block-hardcoded-contigs.sh 0 "hardcoded contigs warn only"  "$(write_file 'src/a.py' 'chroms = [\"chr1\",\"chr2\"]')"
check validate-yaml.sh          0 "bad yaml warns only"           "$(write_file 'config.yaml' 'a: [1')"

echo
echo "──────────────────────────────────────────────────────────────"
printf 'passed %d   failed %d\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf 'failing: %s\n' "${FAILED_NAMES[*]}"
  exit 1
fi
