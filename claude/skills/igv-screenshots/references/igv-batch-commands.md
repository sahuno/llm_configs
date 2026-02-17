# IGV Batch Commands Reference

These commands can be placed in an igv-config file and passed via `--igv-config` / `-c`.
They are injected into the IGV batch script **after each `goto`** and **before each `snapshot`**.

Full reference: https://igv.org/doc/desktop/#UserGuide/tools/batch/

## Display Commands

| Command | Description | Example |
|---------|-------------|---------|
| `colorBy` | Color reads by attribute | `colorBy BASE_MODIFICATION` |
| `group` | Group reads by attribute | `group TAG HP` |
| `sort` | Sort reads | `sort READNAME` |
| `squish` | Compress read display | `squish` |
| `expand` | Expand read display | `expand` |
| `collapse` | Collapse read display | `collapse` |
| `maxPanelHeight` | Set max panel pixel height | `maxPanelHeight 1000` |

## colorBy Options

| Value | Use Case |
|-------|----------|
| `BASE_MODIFICATION` | DNA methylation from ONT/PacBio (MM/ML tags) |
| `TAG HP` | Haplotype (HP tag from whatshap/longphase) |
| `TAG RG` | Read group |
| `UNEXPECTED_PAIR` | Structural variant evidence |
| `INSERT_SIZE` | Insert size anomalies |
| `PAIR_ORIENTATION` | Read pair orientation |
| `READ_STRAND` | Forward/reverse strand |
| `FIRST_OF_PAIR_STRAND` | Strand of first mate |
| `BISULFITE` | Bisulfite-seq methylation |
| `NOMESEQ` | NOMe-seq (GpC/CpG) |
| `NONE` | Reset to default (gray) |

## group Options

| Value | Use Case |
|-------|----------|
| `TAG HP` | Group by haplotype |
| `TAG RG` | Group by read group |
| `STRAND` | Group by strand |
| `SAMPLE` | Group by sample |
| `SUPPLEMENTARY` | Group by supplementary alignment |
| `BASE_AT_POS` | Group by base at a specific position |
| `NONE` | Remove grouping |

## Common Configurations

### Methylation (ONT/PacBio)
```
colorBy BASE_MODIFICATION
```

### Haplotype Visualization
```
group TAG HP
colorBy TAG HP
sort READNAME
```

### Structural Variant View
```
colorBy UNEXPECTED_PAIR
sort INSERT_SIZE
```

### Bisulfite-seq
```
colorBy BISULFITE
```

### Clean Alignment View
```
squish
colorBy NONE
sort POSITION
```

## Preferences (set via IGV prefs.properties)

These are NOT batch commands but can be set in the IGV properties file:

| Preference | Description | Default |
|-----------|-------------|---------|
| `IGV.Bounds` | Window size | `0,0,1920,1080` |
| `SAM.SHOW_SOFT_CLIPPED` | Show soft-clipped bases | `false` |
| `SAM.SHOW_MISMATCHES` | Highlight mismatches | `true` |
| `SAM.SHADE_BASE_QUALITY` | Shade by base quality | `true` |
