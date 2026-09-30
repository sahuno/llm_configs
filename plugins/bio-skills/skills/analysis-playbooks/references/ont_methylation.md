# ONT methylation: pod5 to DMRs

Moved from CLAUDE.md §3A on 2026-09-30.

### 3A. ONT Methylation Pipeline (pod5 to DMRs)

**Standard chain**: pod5 -> dorado basecall -> dorado align (or minimap2) -> samtools sort/index -> modkit pileup -> modkit dmr

**Tool references**: Load containers from `$SITE_CONFIG/containers.yaml`.

**QC checkpoints** (stop and report if any fail):
1. After basecalling: Check read N50, total bases, pass/fail ratio from dorado summary.
2. After alignment: Confirm mapping rate >80%, check flagstat for unexpected supplementary/secondary rates.
3. After modkit pileup: Verify bedMethyl has expected chromosomes, spot-check coverage distribution.
4. After DMR calling: Sanity-check DMR count; fewer than 10 or more than 100k warrants review.

**Common pitfalls**:
- Dorado models must match the chemistry/flowcell. Always confirm with the user.
- modkit pileup `--ref` must match the alignment reference exactly.
- For mouse samples, CpG islands from `$SITE_CONFIG/databases.yaml` are essential context for DMR interpretation.

**"Done" looks like**: bedMethyl files per sample, DMR bed file with statistics, summary plots of methylation distributions, and a manifest CSV linking sample metadata to output paths.

**ONT Processing Infrastructure**:
- **Chemistry detection**: ONT runs may have mixed chemistries (4kHz and 5kHz). Always check and process separately. Dorado model must match chemistry exactly — mismatches produce silent garbage.
- **Apptainer cache**: Set `APPTAINER_CACHEDIR=$(site_path containers.cache_dir)` (the site's cache from `$SITE_CONFIG/paths.yaml`) to avoid home directory quota issues on compute nodes.
- **Primary containers**: `onttools_v2.0.sif` (dorado + samtools), `sahuno/onttools:v3.0` (adds bedtools). Always load from `$SITE_CONFIG/containers.yaml`.
- **Methylation context**: Standard ONT methylation call string is `5mCG_5hmCG@latest,6mA@latest`.
- **Multi-run samples**: Some patients have multiple sequencing runs. These must be basecalled independently, then merged after alignment — never concatenate raw pod5 files across runs.
