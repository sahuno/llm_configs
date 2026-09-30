# Variant calling

Moved from CLAUDE.md §3B on 2026-09-30. Silent failures for Clair3/ClairS and Severus are in the `analysis-gotchas` skill.

### 3B. Variant Calling

| Type | Tool | Notes |
|------|------|-------|
| SNV/Indel (ONT) | Clair3 | Requires model matched to chemistry; use `--platform=ont` |
| SV (ONT) | Sniffles2 | Use `--tandem-repeats` BED when available |
| SNV/Indel (short-read) | GATK HaplotypeCaller | Follow GATK best practices; BQSR then HC then GenotypeGVCFs |

**QC checkpoints**: Check Ti/Tv ratio for SNVs (~2.0-2.1 for WGS, ~2.8 for exome). Check SV size distribution. Filter by QUAL and read support.

**Common pitfalls**: Clair3 model mismatch causes silent garbage. Always verify model version. GATK requires read groups; fail early if missing.
