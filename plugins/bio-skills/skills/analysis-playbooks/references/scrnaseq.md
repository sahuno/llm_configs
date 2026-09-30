# Single-cell RNA-seq

Moved from CLAUDE.md §3D on 2026-09-30.

### 3D. scRNA-seq

**Seurat (R)** or **Scanpy (Python)** — ask user which framework unless context is clear.

**Standard chain**: CellRanger (or STARsolo) -> Load counts -> QC filtering (mito%, nFeature, nCount) -> Normalize -> HVG -> PCA -> Harmony/integration if multi-sample -> UMAP -> Clustering -> Marker genes -> Annotation

**QC checkpoints**: Report cells before/after filtering. Show violin plots of QC metrics. Check doublet rate with scrublet or DoubletFinder.

**Common pitfalls**: Over-filtering kills rare populations. Under-filtering adds noise. Always show QC distributions before applying thresholds and get user confirmation. Resolution parameter for clustering should be explored at multiple values.
