# Genome Aliases

igver resolves genome aliases automatically via `igver/data/genome_map.yaml`.

## Supported Genomes

| Organism | Input Aliases | Resolved To | Chr Prefix |
|----------|--------------|-------------|------------|
| Human | hg19, hg37, b37, GRCh37 | hg19 | Yes (chr1) |
| Human | hg38, GRCh38 | hg38 | Yes (chr1) |
| Human | hs1 | hs1 | Yes (chr1) |
| Mouse | mm10, GRCm38 | mm10 | Yes (chr1) |
| Mouse | mm39, GRCm39 | mm39 | Yes (chr1) |
| Rat | rn6, Rnor_6.0 | rn6 | Yes (chr1) |
| Dog | canFam3, CanFam3.1 | canFam3 | Yes (chr1) |
| Zebrafish | danRer10, GRCz10 | danRer10 | Yes (chr1) |
| Zebrafish | danRer11, GRCz11 | danRer11 | Yes (chr1) |
| Fly | dm6, BDGP6 | dm6 | Yes (chr2L) |
| Worm | ce11, WBcel235 | ce11 | Yes (chrI) |
| Yeast | sacCer3, R64 | sacCer3 | Yes (chrI) |
| Arabidopsis | tair10, TAIR10 | tair10 | Yes (chr1) |

## Common Reference FASTA Files and Their Naming

| Reference | Chr Naming | Notes |
|-----------|-----------|-------|
| Broad `Homo_sapiens_assembly38.fasta` | chr1, chr2, ... | GRCh38, GATK bundle |
| UCSC hg38 | chr1, chr2, ... | Same as above |
| Ensembl GRCh38 | 1, 2, ... | **No chr prefix** |
| 1000 Genomes GRCh37 | 1, 2, ... | **No chr prefix**, use hg38_1kg in IGV |
| UCSC hg19 | chr1, chr2, ... | |
| Ensembl GRCh37 | 1, 2, ... | **No chr prefix** |

## Important

IGV genome builds (hg38, hg19, mm10) always use **chr-prefixed** names. If your BAM was aligned to a non-chr reference (Ensembl), your region files must also use the same convention. Since IGV expects chr-prefix, you may need to add chr to regions:

```bash
awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' regions.bed > regions_chrPrefix.bed
```
