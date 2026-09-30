# Bulk RNA-seq differential expression

Moved from CLAUDE.md §3C on 2026-09-30.

### 3C. RNA-seq / DGE

**Standard chain**: fastp QC -> STAR align (or salmon quant) -> featureCounts -> DESeq2 (R) or pyDESeq2 (Python)

**QC checkpoints**: Verify >70% uniquely mapped (STAR), check PCA for batch effects before DGE, confirm replicate correlation >0.9.

**Defaults**: padj < 0.05, log2FC threshold = 1.0. Always generate MA plot, volcano plot, and PCA. Prompt user about which contrasts to test.

**Common pitfalls**: GTF and genome version mismatch. Salmon index must match the transcriptome version. Always declare the design formula explicitly.
