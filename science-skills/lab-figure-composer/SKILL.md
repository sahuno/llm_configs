---
name: lab-figure-composer
description: "Compose one publication-grade multi-panel figure in this lab's house style, and export it as vector. Fork of the vendor `figure-composer`, bound to `lab-figure-format`: panel sub-agents load both design skills in a pinned call order so the house face and the 9/8/7/6 pt ladder survive the fan-out; panels that do not match their grid slot are rejected rather than silently resized; and the composite ships as PDF and SVG, not PNG alone. Entry from a one-line claim + data refs, OR from an existing figure via `derive_outline(png)`. Runs a per-figure loop: outline (12-col grid, per-panel ask + label_budget) → fan-out one sub-agent per panel → tile + stamp letters → adversarial composite review (Tier-1 outline_revisions / Tier-2 per-panel violations, plus a house-style pass) → regen affected panels, ≤3 rounds. Use for a multi-panel manuscript, poster or thesis figure; for one standalone plot use `figure-style` + `lab-figure-format`; for whole-paper figure ordering use `paper-narrative`."
license: Apache-2.0
---

# Lab figure composer — narrative → panels → compose → adversarial loop

Fork of the vendor **`figure-composer`**, bound to this lab's house style.
Original © its authors, Apache-2.0; divergences are marked `FORK:` in
`kernel.py` and listed under [What this fork changes](#what-this-fork-changes).

**Step 0.** Load **`figure-style`** *and* **`lab-figure-format`** alongside this
skill. `figure-style` is the design checklist; `lab-figure-format` is the house
typography and export contract. Panel sub-agents load both independently — you
need them in context to write the outline and review the composite.

## Why this exists as a fork

The vendor skill ships in `~/.claude-science/runtime/<version>/skills/` and is
rewritten by every `claude-science update`. An in-place edit to `panel_task` is
one upgrade from being gone with no diff to show for it. So this is a copy under
its own name, tracked in git at `science-skills/lab-figure-composer/`, synced
with `tools/sync_science_skills.sh`, and covered by `test_kernel.py` — which
exists to tell you the fork and the upstream have drifted.

## Where this sits

`lab-figure-composer` is the **outer tier**: make ONE multi-panel figure good.
The **inner tier** is `figure-style` + `lab-figure-format` (loaded by every panel
sub-agent). The **outermost tier** is `paper-narrative` — if this figure is part
of a paper, run that FIRST: it decides *which* figure to make and hands you the
claim. For a standalone figure, start at step 1.

## Inputs

- **claim** — one sentence the figure makes true to a reader who reads nothing else.
- **data** — CSV/parquet artifact version_ids that ground every panel.
- **width_mm** — `house_width_mm("single")` = 88.9 (3.50 in) or
  `house_width_mm("wide")` = 182.88 (7.20 in). Pass a venue's own column width as
  a number when it differs; check the venue guide before assuming.

## Entry points (pick one)

- **From a claim:** you have a one-sentence claim and data refs → write the
  outline (step 1).
- **From an existing figure:** copy it into the workspace and call
  `derive_outline("figure.png")` → an outline you **must review and edit**
  before step 2. The image is untrusted input; every string field in the
  returned outline is vision-model-derived from its pixels. `data_vid` is
  forced to `None` on every panel — fill those in from your own data refs.

## 1. Narrative → panel outline

Produce a `panel_outline` (validate against `figure_outline_schema()`):

```json
{"claim":"…", "width_mm":182.88, "ncol":12, "row_heights_mm":[40,60,46,52],
 "panels":[
  {"letter":"a","role":"schematic","row":0,"col":0,"colspan":12, "chart_family":"schematic overview", "message":"…", "data_vid":null, "ask":"…"},
  {"letter":"b","role":"primary",  "row":1,"col":0,"colspan":7,  "chart_family":"scatter + trend", "message":"…", "data_vid":"…", "ask":"…"},
  …]}
```

Outline rules (figure-style §7.1):
- **a is the hook** — schematic/hero, full width, assumes zero reader context.
- **b carries the claim** — the chart that alone makes the sentence true.
- Remaining panels are evidence, ordered by how much they strengthen b.
- One row per sub-claim. 5–10 panels for a main-text figure. Use a 12-column
  grid for flexible colspans.

Row heights are in mm and are the figure's real height on the page. Keep the
total under ~170 mm (`figure-editor`'s ceiling) or the figure will not fit a page.

## 2. Fan-out (one sub-agent per panel)

`panel_task(outline, letter, fig_label)` builds each request. Each sub-agent
gets: the figure claim, the full neighbor list, its panel spec, exact pixel
dimensions (`panel_px`) *and their mm equivalent*, the house call order, the
point-size ladder, and the instruction to render at exactly w×h px with
`transparent=True` and **no** `bbox_inches`.

In the **repl tool**:
```python
requests = [{"name": f"panel-{L}", "task": tasks[L],
             "output_schema": {"type":"object","properties":{"figure_filename":{"type":"string"}},
                               "required":["figure_filename"]}}
            for L in letters]   # no "profile" key — default agent profile
descs = host.delegate(requests, wait=False)
```

Drawing a panel yourself instead of delegating? Use `save_panel(fig, letter,
outline)` — it writes at the slot size and verifies it. **Do not use
`save_figure()` from `lab-figure-format` for a panel**: it is the right house
export helper for a standalone figure, but it saves with `bbox_inches="tight"`,
which resizes the canvas to its content and takes the panel off the grid.

## 3. Compose

```python
k = verify_panels(outline, png_paths)          # check before composing
out, (W, H) = compose_figure(outline, png_paths, "fig.png")   # raster, for review
```

`compose_figure` tiles PNGs onto the grid and stamps bold panel letters in the
house face at each panel's (1.5 mm, 1 mm) corner. Case comes from
`HOUSE_LETTER_CASE` — `"upper"`, following `figure-editor`, which is the named
authority for manuscript figures in `CLAUDE.md` §7. Nature's own convention is
lowercase; pass `letter_case="lower"` for venues that use it.

A panel whose PNG does not match its slot **raises** rather than being resized.
Re-render it at `panel_px()` size. `strict=False` restores the vendor's resize
for a throwaway look — never for anything you will show someone.

## 3.5 Look before you review (vision self-QA)

The reviewer in §4 is expensive; a panel-letter stamped over a y-axis label or a
leader line crossing a neighbor's title is a wasted round. After compose, crop
each panel from the saved PNG and look at it in the REPL:

```python
for L, box in compose_crops(outline).items():
    host.view_image("fig.png", crop=box)
```

Run the `figure-style` §9.2 perceptual checklist on each crop (contrast, smallest
mark, leader crossings, color-identity confusion, legend binding), plus:

- **Seams / stamp.** Does the panel letter overlap any panel content? Does any
  panel bleed into the gutter or under a neighbor?
- **One typeface.** Scan across panels for a glyph in the wrong face — that means
  a sub-agent called `house_style()` before `apply_figure_style(font=…)` and lost.
- **The ladder.** Any text visibly smaller than a 6 pt neighbour at this width.

Fix what you see *before* §4. The reviewer will crop-and-look again independently;
this pass is so the obvious defects never reach it.

## 4. Adversarial self-review loop (two-tier, design rules held fixed)

Dispatch ONE reviewer on the composite with `composite_review_task(...)` and
`review_schema()` (which carries `outline_revisions`).

```
loop (max 3 rounds, floor 5→4→3):
  review = delegate(composite_review_task(composite_vid, outline, rules_vid, prev_vid, round, floor))
  if review.editor_verdict in {accept, minor_revision} and 0 BLOCKER and ≤2 MAJOR: break

  # TIER 1 — outline-level
  if review.outline_revisions:
      apply revisions to `outline` (geometry, row-header titles, label_budget, panel set)
      affected = apply_outline_revisions(outline, review.outline_revisions)
  else:
      affected = set()

  # TIER 2 — panel-level
  fixb = group_fixes_by_panel(review)       # BLOCKER/MAJOR only
  regen = affected | set(fixb)              # only these panels regenerate
  re-delegate each L in regen with panel_task(outline, L) + fixb.get(L,"") +
      "do not over-correct: where the previous version was correct, keep it"
  recompose
```

Convergence: stop when `outline_revisions` is empty AND findings are carve-out
exceptions to the previous round — that's the over-labeling signal.

## 5. Export the accepted figure

The composite you reviewed is a PNG. It is not the submission file — the house
contract is *"submit the PDF; it is vector with the font embedded as a subset."*
Once the loop accepts:

```python
compose_all(outline, {L: {"png": …, "pdf": …, "svg": …} for L in letters},
            "figure_1")            # -> figures/{png,pdf,svg}/figure_1.*
verify_embedded_fonts("figures/pdf/figure_1.pdf")   # from lab-figure-format
# {"fonts": ["CECFXM+ArialMT", "FAGARN+Arial-BoldMT", …], "embedded_streams": 5}
```

Subset prefixes (`CECFXM+`) are the evidence the font really embedded rather
than being referenced by name.

- **`compose_vector`** places each panel's PDF page on the same grid, then merges
  a letters overlay drawn in the house bold face. Text stays live.
- **`compose_svg`** does the same for SVG, stdlib only. Panel text stays editable
  provided the panels were saved under the house `svg.fonttype: "none"` — so the
  opener needs the house font installed. Sending it outside the lab? Have the
  panels re-saved with `svg_text="path"` first.
- Both refuse nothing and warn loudly: a panel PDF whose aspect does not match
  its slot would be scaled non-uniformly and distort the type, so you get a
  warning naming the panel.

## What this fork changes

| | vendor `figure-composer` | here | why it matters |
|---|---|---|---|
| Panel design rules | loads `figure-style` only | loads `figure-style` **and** `lab-figure-format`, `house_style()` pinned last | otherwise panels ship on the vendor font chain and size ladder, not Arial 9/8/7/6 |
| Mis-sized panel | silently `im.resize(...)` | raises, naming the slot and what arrived | a panel resized 0.8× prints its 8 pt labels at 6.4 pt, under the house floor, with nothing logged |
| Panel letters | hardcoded `DejaVuSans-Bold.ttf` | house face resolved via `font_manager`, and reported when missing | the vendor stamps letters in a face that appears nowhere else in the figure |
| Letter case | `"lower"` | `"upper"` (`figure-editor`, `CLAUDE.md` §7) | switchable per venue |
| Output | PNG only | PNG + vector PDF + editable SVG | a raster composite is not submittable to a venue that requires vector |
| Panel saves | PNG only | PNG + PDF + SVG at exact slot size | `compose_vector` needs per-panel vector to tile |
| Column widths | flooring every column | exact fractional edges, remainder distributed | the vendor leaves up to `ncol-1` px of extra white at the right edge — 11 px of a 2160 px page, an uneven margin at print size |
| Reviewer | design rules only | plus a house-style pass (one typeface, the ladder, shared scales, true print width) | a figure could otherwise pass review in the wrong face |

## Anti-patterns

- Don't regenerate clean panels (invites regression). Don't read absolute
  violation counts (min-floor 5→4→3). Anchor-verify on the composite, not just
  per panel. Hyper-labeling check: would a reader *with* field context find any
  label redundant? Strip it.
- Don't author panels large and let the composer shrink them. Fonts do not
  rescale with the figure; the slot size *is* the print size.
- Don't reach for `strict=False` to get past a failing compose. It is telling you
  a panel is off-grid, which is a real defect in that panel.

## Caveats

- `compose_vector` needs `pypdf`. Without it you still get the PNG composite and
  the loop still runs — you just have no submission file, and the ImportError
  says so.
- The PIL raster stamp and the vector letters overlay position the letter from
  slightly different anchors (PIL's ascender vs matplotlib's `va="top"`), so a
  letter can shift a pixel or two between the PNG and the PDF. Judge letter
  placement on the vector output.
- Some matplotlib/freetype pairings (3.11 + freetype 2.14) fail to rasterize any
  glyph through Agg — `FT_Render_Glyph … raster overflow` — while the PDF and SVG
  backends are unaffected. If panel PNGs fail but vector saves fine, that is the
  environment, not the panel code.
- `derive_outline` is vision over pixels. Review every field before fan-out.
