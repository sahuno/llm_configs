---
name: heatmap-dimensions
description: |
  This skill creates publication-quality heatmaps with automatically calculated dimensions
  for Nature journal specifications. Use when user asks to "create a heatmap", "make a
  DE gene heatmap", "plot expression heatmap", "heatmap with proper dimensions",
  "clustered heatmap", "gene expression heatmap", "correlation heatmap", "heatmap for
  DESeq2 results", "ComplexHeatmap", "pheatmap with correct size", or any mention of
  heatmap visualization. Automatically calculates optimal height based on number of
  genes (rows) and determines whether to show row labels. Fixed width of 180mm for
  publication quality. Supports DESeq2, correlation matrices, and clustering analysis.
version: 1.0.0
author: Samuel Ahuno
---

# Heatmap with Automatic Dimension Calculation

Create publication-quality heatmaps with automatically calculated dimensions based on the number of genes and samples. Uses ComplexHeatmap for advanced features.

## Fixed Parameters (Nature Journal Specs)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Width | **180mm** | Double column, space for dendrograms/labels/legend |
| base_size | **20** | Readable fonts at print size |
| Max Height | **170mm** | Nature journal constraint |

**Note**: 90mm width is NOT supported for heatmaps - insufficient space.

## Quick Start

```r
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/heatmap-dimensions/calc_heatmap_dimensions.R")

dims <- calc_heatmap_dimensions(n_genes = 30, n_samples = 8)
# Returns: height_mm = 165, show_row_labels = TRUE

# Create heatmap with ComplexHeatmap
ht <- create_publication_heatmap(expression_matrix,
                                  column_annotation = sample_info)
save_heatmap(ht, "my_heatmap", dims)
```

## Required Information

Gather from user before creating the heatmap:

1. **Data**:
   - Expression matrix (genes × samples)
   - Sample metadata (for column annotations)
   - Gene metadata (optional, for row annotations)

2. **Dimensions** (auto-calculated):
   - Number of genes (rows)
   - Number of samples (columns)

3. **Optional parameters**:
   - `n_annotation_tracks`: Number of column annotation bars (default: 1)
   - `cluster_rows`: Cluster genes? (default: TRUE)
   - `cluster_cols`: Cluster samples? (default: TRUE)
   - `scale`: Scale by row? (default: "row" for z-score)

## Dimension Rules

### Height Calculation

| n_genes | Show Labels | Cell Height | Formula | Result |
|---------|-------------|-------------|---------|--------|
| ≤31 | Yes | 4mm | n×4 + 45 | Variable |
| 32-62 | No | 2mm | n×2 + 45 | Variable |
| >62 | No | 2mm | Capped | **170mm** |

### Decision Tree

```
n_genes ≤ 31?  → Show labels, height = n_genes × 4 + 45
n_genes 32-62? → Hide labels, height = n_genes × 2 + 45
n_genes > 62?  → Hide labels, height = 170mm (capped)
```

## Implementation

### 1. Source and Calculate Dimensions

```r
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/heatmap-dimensions/calc_heatmap_dimensions.R")

# From data
dims <- calc_heatmap_dimensions(
  n_genes = nrow(expr_matrix),
  n_samples = ncol(expr_matrix),
  n_annotation_tracks = 1
)
```

### 2. Prepare Data

```r
# Scale by row (z-score)
expr_scaled <- t(scale(t(expr_matrix)))

# Create column annotation
col_anno <- HeatmapAnnotation(
  Group = sample_metadata$group,
  col = list(Group = c("Control" = "#0072B2", "Treatment" = "#D55E00"))
)
```

### 3. Create Heatmap

```r
library(ComplexHeatmap)
library(viridis)

ht <- Heatmap(
  expr_scaled,
  name = "Z-score",
  col = viridis(100),

  # Dimensions
  show_row_names = dims$show_row_labels,
  show_column_names = dims$show_col_labels,

  # Clustering
  cluster_rows = TRUE,
  cluster_columns = TRUE,

  # Fonts (base_size = 20)
  row_names_gp = gpar(fontsize = 8),
  column_names_gp = gpar(fontsize = 10),

  # Annotations
  top_annotation = col_anno,

  # Dendrograms
  row_dend_width = unit(15, "mm"),
  column_dend_height = unit(15, "mm")
)
```

### 4. Save

```r
save_heatmap(ht, "expression_heatmap", dims)
# Creates: pdf/expression_heatmap.pdf, png/..., svg/...
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `calc_heatmap_dimensions(n_genes, n_samples)` | Calculate height and label visibility |
| `calc_heatmap_height(n_genes)` | Calculate height from gene count |
| `create_publication_heatmap(matrix, ...)` | Convenience function for complete heatmap |
| `save_heatmap(ht, filename, dims)` | Save to pdf/png/svg |
| `get_colorblind_palette(type)` | Get colorblind-safe colors |

## Color Palettes

### Continuous (Heatmap Body)
```r
viridis(100)           # Default, colorblind-safe
inferno(100)           # Yellow-red-black
plasma(100)            # Yellow-purple
RColorBrewer::brewer.pal(11, "RdBu")  # Diverging
```

### Discrete (Annotations)
```r
# Okabe-Ito palette (colorblind-safe)
c("#E69F00", "#56B4E9", "#009E73", "#F0E442",
  "#0072B2", "#D55E00", "#CC79A7", "#999999")
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Labels cut off | Use `dims$show_row_labels` to auto-hide |
| Height exceeds 170mm | Reduce n_genes or accept capped height |
| Too many genes (>100) | Consider showing top N or clustering summary |
| PDF won't open | Use `cairo_pdf` device (handled by `save_heatmap`) |
| Fonts missing | Use default sans-serif, don't specify family |

## Resources

- **Dimension tables:** See `references/dimension-tables.md`
- **Color palettes:** See `references/color-palettes.md`
- **Full example:** See `examples/deseq2_heatmap.R`
- **Correlation example:** See `examples/correlation_heatmap.R`
