# Heatmap Dimension Reference Tables

## Fixed Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Width | 180mm | Double column (Nature) |
| Max Height | 170mm | Nature constraint |
| base_size | 20 | For readable fonts |

## Height by Number of Genes

### With Row Labels (n_genes ≤ 31)

Cell height: 4mm per gene

| n_genes | Body | Overhead | Total Height |
|---------|------|----------|--------------|
| 10 | 40mm | 45mm | **85mm** |
| 15 | 60mm | 45mm | **105mm** |
| 20 | 80mm | 45mm | **125mm** |
| 25 | 100mm | 45mm | **145mm** |
| 30 | 120mm | 45mm | **165mm** |
| 31 | 124mm | 45mm | **169mm** |

### Without Row Labels (n_genes > 31)

Cell height: 2mm per gene

| n_genes | Body | Overhead | Total Height |
|---------|------|----------|--------------|
| 35 | 70mm | 45mm | **115mm** |
| 40 | 80mm | 45mm | **125mm** |
| 50 | 100mm | 45mm | **145mm** |
| 60 | 120mm | 45mm | **165mm** |
| 62 | 124mm | 45mm | **169mm** |
| 75 | 150mm | 45mm | 195mm → **170mm** (capped) |
| 100 | 200mm | 45mm | 245mm → **170mm** (capped) |
| 150 | 300mm | 45mm | 345mm → **170mm** (capped) |
| 200 | 400mm | 45mm | 445mm → **170mm** (capped) |

## Overhead Components

| Component | Size (mm) |
|-----------|-----------|
| Column dendrogram | 15 |
| Annotation (per track) | 8 |
| Title | 10 |
| Column labels | 5 |
| Margins | 7 |
| **Total (1 track)** | **45mm** |

## Label Visibility Rules

| n_genes | Row Labels | Column Labels |
|---------|------------|---------------|
| ≤31 | SHOWN | If n_samples ≤ 50 |
| 32-62 | HIDDEN | If n_samples ≤ 50 |
| >62 | HIDDEN | If n_samples ≤ 50 |

## Quick Formula

```r
# With row labels (n_genes ≤ 31)
height_mm = n_genes × 4 + 45

# Without row labels (n_genes > 31)
height_mm = min(n_genes × 2 + 45, 170)
```
