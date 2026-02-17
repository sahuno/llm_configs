---
name: igv-screenshots
description: |
  This skill generates IGV screenshots using igver for genomic visualization.
  Use when user asks to "take IGV screenshot", "IGV snapshot", "visualize BAM
  in IGV", "igver screenshot", "show me the reads at", "screenshot genomic
  region", "visualize methylation in IGV", "IGV plot of BAM", "generate IGV
  images", "look at this region in IGV", "screenshot structural variant",
  "haplotype visualization in IGV", or any mention of IGV/igver with BAM files.
  Handles Singularity/Docker execution, chromosome naming mismatches,
  methylation coloring (ONT/PacBio), and batch generation for large region sets.
version: 1.0.0
author: Samuel Ahuno
---

# IGV Screenshots with igver

Generate publication-quality IGV screenshots programmatically from BAM files across genomic regions using [igver](https://github.com/sahuno/igver).

## Required Information

Gather from user before generating:

1. **Input files** (required):
   - BAM file path(s), or a `.txt` file with one path per line
   - Each BAM must have a `.bai` index

2. **Regions** (required):
   - BED file (`.bed` — BED3 or BED6), region text file (`.txt`), or inline `chr:start-end`

3. **Genome** (default: `hg19`):
   - Common: `hg38`, `hg19`, `mm10`, `mm39`
   - Aliases supported: `GRCh38` -> `hg38`, `GRCm38` -> `mm10`, etc.
   - See `references/genome-aliases.md`

4. **Visualization type** (ask user):
   - Standard alignment view (default)
   - DNA methylation coloring (ONT/PacBio — needs `colorBy BASE_MODIFICATION`)
   - Haplotype coloring (needs `colorBy TAG HP` + `group TAG HP`)
   - Custom IGV preferences

5. **Output directory**

## Pre-flight Checks

Before generating the script, ALWAYS verify:

### 1. Chromosome Naming Convention
```bash
# Check BAM chromosome names
samtools view -H sample.bam | grep @SQ | head -3
# Look for: SN:chr1 (UCSC) vs SN:1 (Ensembl/NCBI)
```

```bash
# Check BED chromosome names
head -3 regions.bed
```

**If they don't match**, add a preprocessing step:
```bash
# Add 'chr' prefix to BED
awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' regions.bed > regions_chrPrefix.bed

# Remove 'chr' prefix from BED
sed 's/^chr//' regions.bed > regions_noChr.bed
```

### 2. BAM Index Exists
```bash
ls sample.bam.bai  # or sample.bai
```

### 3. Region Count
```bash
wc -l regions.bed
# If >500 regions: warn user it will take a while, suggest screen/tmux/SLURM
```

## Script Template

### Standard Screenshot
```bash
#!/bin/bash
set -euo pipefail

BAM="<BAM_PATH>"
REGIONS="<REGIONS_PATH>"
OUTDIR="<OUTPUT_DIR>"
GENOME="<GENOME>"  # hg38, hg19, mm10, etc.
IGVER_IMAGE="docker://sahuno/igver:latest"

mkdir -p "${OUTDIR}"

singularity exec \
    --bind <BIND_PATHS> \
    "${IGVER_IMAGE}" \
    igver \
        --input "${BAM}" \
        --regions "${REGIONS}" \
        --output "${OUTDIR}" \
        --genome "${GENOME}" \
        --dpi 600 \
        --overlap-display squish \
        --max-panel-height 200 \
        --no-singularity \
        --format png
```

### Methylation Screenshot (ONT/PacBio)
```bash
#!/bin/bash
set -euo pipefail

BAM="<BAM_PATH>"  # Must contain MM/ML tags from dorado/guppy
REGIONS="<REGIONS_PATH>"
OUTDIR="<OUTPUT_DIR>"
GENOME="hg38"
IGVER_IMAGE="docker://sahuno/igver:latest"

# Create methylation config
IGV_CONFIG="${OUTDIR}/igv_methylation_prefs.txt"
mkdir -p "${OUTDIR}"
echo "colorBy BASE_MODIFICATION" > "${IGV_CONFIG}"

singularity exec \
    --bind <BIND_PATHS> \
    "${IGVER_IMAGE}" \
    igver \
        --input "${BAM}" \
        --regions "${REGIONS}" \
        --output "${OUTDIR}" \
        --genome "${GENOME}" \
        --dpi 600 \
        --overlap-display expand \
        --max-panel-height 1000 \
        --no-singularity \
        --format png \
        --igv-config "${IGV_CONFIG}"
```

**Methylation colors**: Red = methylated CpG (5mC), Blue = unmethylated CpG.

### Haplotype Screenshot
```bash
# Create haplotype config
cat > "${OUTDIR}/igv_haplotype_prefs.txt" << 'EOF'
group TAG HP
colorBy TAG HP
sort READNAME
EOF

# Then pass: --igv-config "${OUTDIR}/igv_haplotype_prefs.txt"
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `-i`, `--input` | BAM/BEDPE/VCF/bigWig file(s), or `.txt` with paths | *required* |
| `-r`, `--regions` | Regions: `chr1:100-200`, `.txt` file, or `.bed` file | *required* |
| `-o`, `--output` | Output directory | `/tmp` |
| `-g`, `--genome` | Reference genome (aliases supported) | `hg19` |
| `--dpi` | DPI resolution | `300` |
| `-p`, `--max-panel-height` | Max pixel height per track panel | `200` |
| `-d`, `--overlap-display` | `expand`, `collapse`, or `squish` | `squish` |
| `-c`, `--igv-config` | IGV batch commands file (injected before each snapshot) | *none* |
| `-f`, `--format` | `png`, `svg`, or `pdf` | `png` |
| `--no-singularity` | **Required** when running inside a container | `false` |
| `--singularity-image` | Container image path | `docker://sahuno/igver:latest` |
| `--singularity-args` | Extra Singularity args (bind mounts) | `-B /home` |

## Recommended Settings by Data Type

| Data Type | `-d` | `-p` | `--dpi` | `--igv-config` |
|-----------|------|------|---------|-----------------|
| Short-read WGS/WES | `squish` | `200` | `300` | *none* |
| Long-read ONT/PacBio | `expand` | `1000` | `600` | *none* |
| ONT methylation | `expand` | `1000` | `600` | `colorBy BASE_MODIFICATION` |
| Haplotagged reads | `squish` | `500` | `600` | `group TAG HP` + `colorBy TAG HP` |
| Structural variants | `squish` | `200` | `300` | *none* |

## Bind Mount Rules

All directories containing input files, output, and config must be bind-mounted:
```bash
--bind /data1/project,/data1/references,/home
```

igver auto-binds BAM directories and output, but additional paths (BED files, igv-config) may need explicit mounting.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Empty screenshots | Chromosome names don't match — check chr prefix |
| "Region not found" | Wrong genome build or chr naming convention |
| Nested container error | Add `--no-singularity` flag |
| OOM on large region sets | Use `load_figures=False` (CLI does this automatically since v1.1) |
| Missing BAM index | Create with `samtools index sample.bam` |
| Slow on many regions | Run via SLURM or `screen`/`tmux` |

## Resources

- **Genome aliases:** See `references/genome-aliases.md`
- **IGV batch commands:** See `references/igv-batch-commands.md`
- **Examples:** See `examples/`
- **igver source:** `/data1/greenbab/users/ahunos/apps/igver/`
- **igver GitHub:** https://github.com/sahuno/igver
