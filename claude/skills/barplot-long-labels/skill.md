---
name: barplot-long-labels
description: |
  This skill creates publication-quality horizontal barplots with long categorical
  y-axis labels. Use when user asks to "create a GO enrichment barplot", "make a
  barplot with pathway names", "plot KEGG results as horizontal bars", "barplot
  with long y-axis labels", "enrichment figure with proper dimensions", "horizontal
  barplot that fits all labels", or needs help sizing figures with long text on
  the y-axis. Automatically calculates optimal width and height based on label
  length and number of categories. Supports GO, KEGG, Reactome pathway visualization.
version: 1.0.0
author: Samuel Ahuno
---

# Barplot with Long Y-Axis Labels

Create horizontal barplots with automatically calculated dimensions for long categorical labels (GO pathways, KEGG terms, etc.).

## Quick Start

```r
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/barplot-long-labels/calc_barplot_dimensions.R")

dims <- calc_barplot_dimensions(data, y_col = "Description", base_size = 20)
# ... create ggplot ...
ggsave(p, width = dims$width_mm, height = dims$height_mm, units = "mm")
```

## Required Information

Gather from user before creating the plot:

1. **Data frame** with:
   - Y-axis labels column (e.g., `Description`)
   - Bar values column (e.g., `p.adjust`, `count`)
   - (Optional) Grouping column (e.g., `Direction`)

2. **Parameters** (defaults in parentheses):
   - `base_size`: Font size (20)
   - `base_bar_width_mm`: Bar area width (180mm)
   - `wrap_width`: Text wrap limit (50 chars)
   - `top_n`: Number of items (10)

## Implementation

### 1. Source and Prepare

```r
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/barplot-long-labels/calc_barplot_dimensions.R")

plot_data <- data %>%
  slice_min(p.adjust, n = 10) %>%
  mutate(label = str_wrap(Description, width = 50),
         label = factor(label, levels = rev(unique(label))))
```

### 2. Calculate and Plot

```r
dims <- calc_barplot_dimensions(plot_data, y_col = "label", base_size = 20)

p <- ggplot(plot_data, aes(x = -log10(p.adjust), y = label, fill = Direction)) +
  geom_bar(stat = "identity", width = 0.7) +
  theme_bw(base_size = 20)

ggsave(p, width = dims$width_mm, height = dims$height_mm, units = "mm")
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `calc_barplot_dimensions(data, y_col)` | Calculate width & height from data |
| `calc_barplot_width(n_chars)` | Calculate width from character count |
| `calc_barplot_height(n_items)` | Calculate height from item count |
| `create_barplot_long_labels()` | Convenience function for complete plot |
| `save_barplot_multiformat()` | Save to pdf/png/svg |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Labels cut off | Use calculated dimensions, increase `base_bar_width_mm` |
| Bars too thin | Increase height or reduce `top_n` |
| Font issues (Linux) | Don't specify font family, use system default |

## Resources

- **Dimension tables:** See `references/dimension-tables.md`
- **Color palettes:** See `references/color-palettes.md`
- **Full example:** See `examples/go_enrichment_barplot.R`
- **Detailed docs:** `/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr/docs/barplot_width_calculation_guide.md`
