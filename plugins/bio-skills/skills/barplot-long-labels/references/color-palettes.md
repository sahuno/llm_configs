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
