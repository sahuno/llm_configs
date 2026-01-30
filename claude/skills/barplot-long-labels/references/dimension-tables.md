# Dimension Reference Tables

Quick lookup tables for barplot dimensions at `base_size=20`.

## Width Reference (bar_width=180mm)

| Max Label Chars | Label Area | Total Width |
|-----------------|------------|-------------|
| 20 | 61mm | 260mm |
| 30 | 86mm | 285mm |
| 40 | 112mm | 310mm |
| 50 | 137mm | 335mm |
| 60 | 162mm | 360mm |
| 70 | 188mm | 385mm |
| 80 | 213mm | 410mm |
| 90 | 238mm | 435mm |
| 100 | 264mm | 460mm |

## Height Reference

| # Categories | Height |
|--------------|--------|
| 5 | 110mm |
| 10 | 170mm |
| 15 | 230mm |
| 20 | 290mm |
| 25 | 350mm |
| 30 | 410mm |

## Dimension Formulas

### Width Calculation

```
axis_font_pt = base_size × 0.8
char_height_mm = axis_font_pt × 0.3528
char_width_mm = char_height_mm × 0.45  (proportional fonts)
label_text_mm = max_chars × char_width_mm
total_width = label_text_mm + 10 + bar_width + 15
```

### Height Calculation

```
space_per_item = base_size × 0.6  (12mm at base_size=20)
fixed_overhead = 50mm
total_height = fixed_overhead + (n_items × space_per_item)
```

## Adjustments

### For Different base_size

| base_size | Axis Font | Char Width | Space/Item |
|-----------|-----------|------------|------------|
| 12 | 9.6pt | 1.53mm | 7.2mm |
| 16 | 12.8pt | 2.03mm | 9.6mm |
| 20 | 16pt | 2.54mm | 12mm |
| 24 | 19.2pt | 3.05mm | 14.4mm |

### For Different bar_width

Adjust the formula: `total_width = label_area + bar_width + 25`

| bar_width | For 50-char labels |
|-----------|-------------------|
| 90mm | 245mm |
| 180mm | 335mm |
| 250mm | 405mm |

## Nature Journal Guidelines

- Single column: 90mm
- Double column: 180mm
- Full page depth: 170mm

For GO enrichment barplots with long labels, typically need **double column width or larger** (180-350mm).
