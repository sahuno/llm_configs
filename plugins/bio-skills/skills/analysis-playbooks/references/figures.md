# Manuscript figures: sizes, scaling and assembly

Moved from CLAUDE.md §7 and §9 on 2026-09-30. The everyday rules (three formats, fonts, fixed y-axes) stay in CLAUDE.md §7.

### Two Figure Locations
- **`results/{run}/figures/{png,pdf,svg}/`** — individual analysis figures generated per run. This is where scripts save figures during analysis.
- **`docs/manuscript/figures/`** — final multi-panel publication figures assembled from individual figures (created when preparing a manuscript, not during analysis). Draft the composite with the `figure-composer` Claude Science skill, then run it through `print-plate-assembly` — that pass re-renders each panel in the house style, lays it out on the sheet, and emits the manifest and legend. Point it here with `plate_paths(slug, letters, root="docs/manuscript/figures")`; its default root is a bare `plates/`. Illustrator remains the manual fallback. Nothing else writes here — analysis figures go to the per-run location above.

### ggplot2 Font Size Scaling Reference
The `theme()` element sizes are multiplied from `base_size`:

| Element | Multiplier | Draft (20pt target) | Nature final (6pt target) |
|---------|-----------|---------------------|---------------------------|
| `axis.text` | base_size × 0.8 | base_size = 25 | base_size = 7.5 |
| `axis.title` | base_size × 1.0 | base_size = 20 | base_size = 6 |
| `plot.title` | base_size × 1.2 | base_size = 17 | base_size = 5 |
| `legend.text` | base_size × 0.8 | base_size = 25 | base_size = 7.5 |

- **Key insight**: the multiplier, not the target, is the thing to remember — `axis.text` is `base_size × 0.8`, so solve for the size you actually want. Pick the target from where the figure will be *viewed*: a slide or a screen review wants 20pt; a 90 mm journal column wants ~6pt.
- **Default colorblind-safe palette**: Okabe-Ito — `#0072B2` (blue), `#E69F00` (orange), `#D55E00` (vermillion), `#999999` (grey).

### Nature Magazine Specifications (Final Manuscript Figures Only)
- Single column: 90 mm wide. Double column: 180 mm wide. Full page depth: 170 mm.
- Font: Arial or Helvetica, **5–8pt at final size** (lettering ≈ 2 mm tall, per Nature's guidance). This is the authoritative range for manuscript submission; the 20pt default above applies to draft figures only.
- **The lab's choice within that range is 8pt** — single-panel body 8pt, legend 7pt, ticks 6pt, single column 3.50 in (= 88.9 mm). That ladder and its matplotlib style live in the `lab-figure-format` Claude Science skill, mirrored at `science-skills/lab-figure-format/`. Use it rather than picking a size per figure; consistency across panels matters more than the exact point within the range.
- **`print-plate-assembly` is the authority for final figures**, and the only place the house style is actually applied — its Step 2 re-renders every panel through `apply_figure_style()` then `house_style()` before placing it, and `predict_print_size()` reports what each panel's smallest text measures once scaled into its slot. A composer's output is a draft until it has been through that pass.
- Apply these only when the user explicitly requests publication-quality or Nature-format figures.

### Philosophy of research publication with figures (stream of thought)
- Generate 3 figure formats (.png, .pdf, .svg) per figure. rasterize the .pdf  with `RASTERISE_DPI` of 50dpi and  png_dpi=70 (local machine)
- keep a figure index per script. Helps track down where each figure came from per script (Host and local machine)
- download figures onto OneDrive research/institutional folder (local machine)
- place figures (.pdf) on illustrator artboard and save accordingly as Figure 1, 2, .... # or Supplementary Figure 1, 2,...,n (local machine)
- write script to autodownload figures with higher dpi when ready (local machine)
- adobe illustrator should can be resaved with high dpi figures and exported as .pdf (local machine)
