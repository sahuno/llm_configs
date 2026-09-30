# R colour palettes for cohort and expression heatmaps

Rescued from `heatmap-dimensions` and `barplot-long-labels` when those
skills were retired (2026-09-06) for asserting their own font sizes and
figure widths against the house style. The palettes were never part of that
conflict — colour is not typography — and nothing else in this repo carries
them, so they are kept here with the surviving R figure skill.

Sizing and typography are **not** defined here. They come from
`lab-figure-format`, and `print-plate-assembly` is what applies them.

---

# Color Palettes for Heatmaps

## Continuous Palettes (Heatmap Body)

### Recommended: Viridis Family (Colorblind-Safe)

```r
library(viridis)

viridis(100)   # Default: purple → green → yellow
inferno(100)   # Black → red → yellow
plasma(100)    # Purple → pink → yellow
magma(100)     # Black → purple → yellow
cividis(100)   # Blue → yellow (optimized for colorblindness)
```

### Diverging (Centered at Zero)

```r
library(RColorBrewer)

# Blue-White-Red (most common for expression)
colorRampPalette(rev(brewer.pal(11, "RdBu")))(100)

# Purple-White-Green
colorRampPalette(rev(brewer.pal(11, "PRGn")))(100)

# Brown-White-Blue-Green
colorRampPalette(rev(brewer.pal(11, "BrBG")))(100)
```

### Custom Blue-White-Red

```r
colorRampPalette(c("navy", "white", "firebrick3"))(100)
```

## Discrete Palettes (Annotations)

### Okabe-Ito (Recommended - Colorblind-Safe)

```r
okabe_ito <- c(
  "#E69F00",  # orange
  "#56B4E9",  # sky blue
  "#009E73",  # bluish green
  "#F0E442",  # yellow
  "#0072B2",  # blue
  "#D55E00",  # vermillion
  "#CC79A7",  # reddish purple
  "#999999"   # grey
)
```

### Treatment/Control (2 groups)

```r
c("Control" = "#0072B2",    # blue
  "Treatment" = "#D55E00")  # vermillion
```

### Up/Down/NotSig (3 groups)

```r
c("Up" = "#D55E00",        # vermillion
  "Down" = "#0072B2",      # blue
  "Not Sig" = "#999999")   # grey
```

### Sample Groups (5 groups)

```r
c("Group_A" = "#0072B2",   # blue
  "Group_B" = "#E69F00",   # orange
  "Group_C" = "#009E73",   # green
  "Group_D" = "#CC79A7",   # purple
  "Group_E" = "#56B4E9")   # sky blue
```

## Using with ComplexHeatmap

### Heatmap Body

```r
library(ComplexHeatmap)
library(viridis)

Heatmap(matrix, col = viridis(100), ...)
```

### Annotations

```r
# Define colors for each annotation column
anno_colors <- list(
  Group = c("Control" = "#0072B2", "Treatment" = "#D55E00"),
  Batch = c("Batch1" = "#E69F00", "Batch2" = "#56B4E9", "Batch3" = "#009E73")
)

HeatmapAnnotation(
  df = sample_metadata,
  col = anno_colors
)
```

## Color Accessibility

### Colorblind Simulation

Test your palette with:
- [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/)
- [Sim Daltonism](https://michelf.ca/projects/sim-daltonism/) (macOS)
- R package `colorBlindness`

### Safe Combinations

| Good Pairs | Avoid |
|------------|-------|
| Blue + Orange | Red + Green |
| Blue + Yellow | Red + Brown |
| Purple + Green | Green + Brown |

---

# Color Palettes for Enrichment Barplots

## Two-Group (Up/Down Regulation)

```r
scale_fill_manual(
  values = c("Upregulated" = "#D62728", "Downregulated" = "#1F77B4"),
  name = "Gene Regulation"
)
```

Alternative warm/cool:
```r
c("Upregulated" = "#E74C3C", "Downregulated" = "#3498DB")
```

## Multi-Group (GO Ontology)

```r
scale_fill_manual(
  values = c("BP" = "#E41A1C", "MF" = "#377EB8", "CC" = "#4DAF4A"),
  name = "Ontology"
)
```

## Gradient (Continuous Values)

For p-values or enrichment scores:
```r
scale_fill_gradient(low = "#FEE0D2", high = "#DE2D26", name = "-log10(p.adj)")
```

For NES scores (diverging):
```r
scale_fill_gradient2(
  low = "#2166AC", mid = "white", high = "#B2182B",
  midpoint = 0, name = "NES"
)
```

## Colorblind-Friendly Options

```r
# Two groups
c("Up" = "#E69F00", "Down" = "#56B4E9")

# Three groups (Okabe-Ito)
c("#E69F00", "#56B4E9", "#009E73")
```

## Publication-Ready (Grayscale Compatible)

```r
c("Upregulated" = "#404040", "Downregulated" = "#BABABA")
```
