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
