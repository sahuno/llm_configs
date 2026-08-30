---
name: lab-figure-format
description: Apply a consistent house typography, journal-standard figure widths (3.5 in single column, 7.2 in full page) and a strict point-size ladder, then export every figure to PNG, PDF and SVG. Use when producing figures for a paper, poster, thesis or grant where all panels must share one typeface and size scale, when sizing a figure for a journal's column width, when checking whether text will still be legible at print size, when a journal requires vector files with embedded fonts, when figures across scripts or notebooks look typographically inconsistent, when text renders in the wrong font after setting font.family, when math/LaTeX labels appear in a different typeface from the surrounding axis labels, when a vector export is unexpectedly huge, or when checking whether a font is actually installed rather than silently substituted. Default typeface is Arial, overridable per journal. This is a house style, not design guidance -- load `figure-style` alongside it for chart choice, labelling and layout rules.
---

# Lab figure format

House typography and export mechanics for matplotlib figures. **Personal
convention of this user** — Arial by default, overridable per journal.

This skill sets *how figures look typographically and what files ship*. It
deliberately says nothing about chart choice, label economy, colour or layout —
load **`figure-style`** alongside it for those, and call `apply_figure_style()`
before `house_style()` so the house font wins.

## Composing with `figure-style`

`figure-style` is the design checklist (chart choice, labelling, layout); this
skill is typography and export. They compose — call in this order:

```python
apply_figure_style()   # figure-style: ticks, spines, legend, size ladder
house_style()          # this skill: font, matched mathtext, embed-safe vectors
```

`house_style()` deliberately overwrites three things `apply_figure_style()` sets,
and leaves everything else (tick length/direction, spine width, frameless
legends, size ladder) untouched:

| rcParam | figure-style | house_style | why |
|---|---|---|---|
| `font.sans-serif` | `[font, DejaVu Sans]` | `[font, Helvetica, DejaVu Sans]` | an intermediate fallback, so a machine without the font gets a near neighbour |
| `mathtext.fontset` / `.rm` | `dejavusans` / `sans` | `custom` / the chosen font | otherwise `$...$` renders in DejaVu while the rest of the figure does not |
| `svg.fonttype` | `path` (glyphs outlined) | `none` (live `<text>`) | keeps SVG text editable and searchable; pass `svg_text="path"` to `save_figure` when sending outside the lab |

`pdf.fonttype: 42` is set by both — no conflict.

**On order.** `apply_figure_style()` only writes `font.sans-serif` when you pass
its own `font=` argument. So:

* `house_style()` then `apply_figure_style()` (no `font=`) — nothing is lost; the
  house font and matched mathtext survive.
* `house_style()` then `apply_figure_style(font="Helvetica")` — the house font IS
  overwritten (`['Arial','Helvetica','DejaVu Sans']` becomes
  `['Helvetica','DejaVu Sans']`), though matched mathtext still survives.

Calling `house_style()` last is the reliable order: it works whether or not
`apply_figure_style` was given a font.

## Quick start

```python
house_style()                       # Arial, matched mathtext, embed-safe vectors
# ... build fig ...
rasterize_dense(ax)                 # only for scatter plots with many points
save_figure(fig, "volcano_all_contrasts")
```

Writes `figures/png/`, `figures/pdf/`, `figures/svg/`.

## Figure size and the point-size ladder

**House convention — author figures at final print size.**

| | width | use |
|---|---|---|
| single column | **3.50 in** | one panel |
| full page | **7.20 in** | multi-panel / wide |

```python
fig, ax = plt.subplots(figsize=figure_size("single"))        # 3.5 x 2.625
fig = plt.figure(figsize=figure_size("wide", height=7.8))    # 7.2 x 7.8
```

**A single-panel figure uses 8 pt.** For multi-panel figures keep a strict
ladder and map by role, never per-figure taste:

| role | pt |
|---|---|
| panel/figure title | 9 |
| axis label, body text | 8 |
| tick label, legend, annotation | 7 |
| dense in-plot label (gene names, cell values) | 6 |

Nothing below 6 pt in the source, and nothing that *prints* below ~5 pt.

**Why authoring size matters more than it looks.** Fonts do not rescale with
the figure. A figure drawn 14 in wide and reduced to 7.2 in on the page has
every point size halved — a 9 pt title prints at 4.7 pt, an illegible 6 pt
gene label prints at 3.1 pt. Drawing at final width and choosing sizes from the
ladder is the only way the numbers in your code mean what they say on paper.

```python
check_print_size(fig)
# width 15.40 in -> target 7.20 in (scale 0.47x)
#   smallest text 5.6 pt -> prints at 2.6 pt
#   WARNING: figure is 2.14x too wide; author it at 7.2 in instead of scaling down.
```

Call it before `save_figure()`; `ok` is False if the figure must be reduced to
fit or if any text would print below the legibility floor.

**One thing neither the size check nor a bbox collision check can see: bleed.**
The standard geometric check in `figure-style` §9.1 tests text boxes against
each other and against `fig.bbox` — the *figure* box. A label that leaves its
own *axes* box and lands in the neighbouring panel is inside `fig.bbox`, so it
passes, and at print size it reads as a label on the wrong panel. Two cheap
guards, once, on the first render: compare each non-tick text box against
`ax.bbox` for the axes it belongs to, and read the saved image. Axis labels,
panel titles, panel letters and colorbar labels sit outside the axes box by
design, rotated text reports an unrotated box, and tick labels outside the view
limits are never drawn — so this list is meant to be skimmed for the one real
crossing, not driven to empty.

## Changing the typeface per journal

```python
house_style("Helvetica")                        # another sans
house_style("Times New Roman", family="serif")  # serif journal
available_fonts()                               # what is installed here
```

`house_style()` returns `{"font", "resolved_file", "installed"}` — check
`installed` in a script, because **matplotlib substitutes a missing font
silently** and the figure ships in the wrong face with no error.

## Why not just set `rcParams["font.family"]`

Three things that assignment misses, all of which `house_style()` handles:

1. **Mathtext ignores it.** A label like `$-\log_{10} p$` renders in DejaVu
   regardless of `font.family` unless `mathtext.fontset` is `"custom"` and the
   `mathtext.rm/it/bf` roles are set. Symptom: tick labels in Arial, axis label
   in DejaVu, in the same figure.
2. **No fallback.** A collaborator without the font drops to DejaVu rather than
   a near neighbour. `house_style()` sets Arial → Helvetica → DejaVu Sans.
3. **Type 3 vector text.** Matplotlib's default `pdf.fonttype` is 3, which is
   not editable in Illustrator and is rejected by some journals.
   `house_style()` sets 42 (TrueType).

## Export

`save_figure(fig, stem)` writes all three formats. Submit the **PDF** — it is
vector with the font embedded as a subset. Confirm with:

```python
verify_embedded_fonts("figures/pdf/my_figure.pdf")
# {"fonts": ["BQXPMH+ArialMT", ...], "embedded_streams": 3, "size_kb": 82}
```

Subset-name prefixes (`BQXPMH+`) are the evidence the font is genuinely
embedded rather than merely referenced.

**Sending an SVG outside the lab?** Default `svg_text="none"` references the
font by name, so the opener needs it installed. Use
`save_figure(fig, stem, svg_text="path")` to convert glyphs to outlines —
identical rendering anywhere, but text is no longer editable or searchable.

## Dense scatter plots

Call `rasterize_dense(ax)` before saving any plot with thousands of points
(volcano, MA, per-cell embedding). It rasterizes only the point collections;
text, axes and ticks stay vector.

Measured on a 7-panel volcano with ~92,000 points: **SVG 10.2 MB → 0.58 MB,
PDF 1.4 MB → 344 kB**, with all 93 text elements still vector.

## Bundled style file

`operon_arial.mplstyle` ships with this skill for scripts that prefer a style
file over a function call. Copy it beside the script and use:

```python
plt.style.use("operon_arial.mplstyle")
```

`house_style()` is preferred — it takes the font as an argument and verifies
the resolution; the style file hardcodes Arial.

## Caveats worth carrying into a methods section

- `bbox_inches="tight"` (used by `save_figure`) resizes the canvas to fit
  content, so the page is not exactly the `figsize` set. If a journal specifies
  exact column widths, size the figure explicitly and drop it.
- A `findfont: Failed to find font weight normal` warning appears with custom
  mathtext and some fonts. It is cosmetic — verify with
  `verify_embedded_fonts()` that the intended font is present in the output.
- PNG bakes the font into pixels; "consistent typography" only holds for the
  vector formats.
