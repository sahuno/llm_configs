"""Multi-panel figure composition, bound to this lab's house style.

Fork of the vendor `figure-composer` kernel. The vendor skill is shipped in
`~/.claude-science/runtime/<version>/skills/` and is overwritten by every
`claude-science update`, so it cannot be edited in place. Every deliberate
divergence below is marked `FORK:`; everything else is the vendor logic.

Four changes, and the reasons:

1. `panel_task` names BOTH design skills and fixes the call order
   (`apply_figure_style()` then `house_style()` last). The vendor prompt loads
   `figure-style` only, so panels come out on its font chain and size ladder
   rather than the house Arial 8/7/6.
2. `compose_figure` asserts panel dimensions instead of silently resizing.
   A resize rescales the type: an 8 pt label in a panel resized 0.8x prints at
   6.4 pt, off the ladder, with no error anywhere.
3. Panel letters are stamped in the house face, resolved through matplotlib's
   font manager, and the resolution is reported rather than assumed.
4. `compose_vector` / `compose_svg` are new. The vendor composite is PIL raster
   only, which is right for the review loop and wrong for submission -- the
   house export contract is a vector PDF with the font embedded as a subset.

`grid_geom` additionally distributes its rounding remainder; the vendor floors
every column, leaving up to `ncol-1` px of unbalanced white at the right edge.
"""

import os
import re


def fc_sdk():
    """Rebind-proof SDK handle -- see pdf-explore/kernel.py:pdf_sdk."""
    import host
    return host


# ---------------------------------------------------------------- house facts

HOUSE_FONT = "Arial"
# The chain house_style() installs. Every path that picks a face must walk it,
# or the outputs disagree: with Arial absent but Helvetica present, panels come
# out in Helvetica while a single-family lookup drops to matplotlib's DejaVu
# default, stamping letters in a face that appears nowhere else in the figure.
HOUSE_FALLBACK = ("Arial", "Helvetica", "DejaVu Sans")
HOUSE_LETTER_PT = 9
# FORK: `figure-editor` is the named authority for manuscript figures in
# CLAUDE.md section 7, and it labels panels A, B, C. The vendor default is
# lowercase, which is Nature's own convention -- pass letter_case="lower" for
# venues that use it.
HOUSE_LETTER_CASE = "upper"
# CLAUDE.md distinguishes two figure homes, and a composed figure belongs to the
# second: `results/{run}/figures/{png,pdf,svg}` is per-run ANALYSIS output, which
# is save_figure()'s territory, while `docs/manuscript/figures/` holds the final
# multi-panel publication figures. Defaulting to a bare `figures/` would squat in
# the analysis namespace and collide with whatever a run script already wrote
# there. It also keeps the build tree outside `figure_manifest.py --check`, which
# scans a results/<run> directory.
HOUSE_FIGURE_ROOT = os.path.join("docs", "manuscript", "figures")
BUILD_DIRNAME = "_build"

# 3.50 in and 7.20 in exactly, the widths in lab-figure-format.figure_size().
# Kept in mm to the full conversion (7.2 * 25.4 = 182.88): rounding to 182.9
# lands the 300 dpi canvas a pixel off 2160 px, which is 7.20 in on the nose.
HOUSE_WIDTH_MM = {"single": 88.9, "wide": 182.88}
HOUSE_LADDER = {"title": 9, "label": 8, "tick": 7, "dense": 6}
HOUSE_MIN_PT = 6


def figure_paths(stem, root=None, formats=("png", "pdf", "svg")):
    """Canonical locations for one composed figure -- the only definition of the
    layout, so the panel writer, the fan-out prompt and the exporter cannot drift.

        docs/manuscript/figures/
          {png,pdf,svg}/<stem>.<fmt>        the deliverables
          _build/<stem>/                    everything else, namespaced by figure
            outline.json                    the producer
            panels/panel_<L>.<fmt>
            rounds/composite_r<n>.png

    The `<stem>` segment is what makes a second figure safe: `panel_a.pdf` is a
    fixed name, so without it Figure 2's panels overwrite Figure 1's and
    `compose_all` rebuilds Figure 1 from them without complaint -- the slot sizes
    match, because both figures share a grid.
    """
    root = HOUSE_FIGURE_ROOT if root is None else root
    build = os.path.join(root, BUILD_DIRNAME, stem)
    return {"root": root, "build": build,
            "panels": os.path.join(build, "panels"),
            "rounds": os.path.join(build, "rounds"),
            "outline": os.path.join(build, "outline.json"),
            "finals": {f: os.path.join(root, f, f"{stem}.{f}") for f in formats}}


def panel_path(stem, letter, fmt, root=None):
    """Canonical path of one panel file."""
    return os.path.join(figure_paths(stem, root)["panels"], f"panel_{letter}.{fmt}")


def round_path(stem, round_no, root=None):
    """Canonical path of the composite for one review round.

    Keeping each round is what gives the reviewer's `regression_vs_prev` field
    something real to compare against; regenerating a panel otherwise overwrites
    the only copy of what it replaced.
    """
    return os.path.join(figure_paths(stem, root)["rounds"], f"composite_r{round_no}.png")


def house_font_chain(font=None):
    """The house face followed by its fallbacks, as `house_style()` orders them."""
    name = font or HOUSE_FONT
    return [name] + [f for f in HOUSE_FALLBACK if f != name]


def house_width_mm(kind="single"):
    """Target width in mm for `figure_outline["width_mm"]`.

    "single" -> 88.9 (3.50 in), "wide"/"double"/"page" -> 182.88 (7.20 in), or
    pass a number through unchanged for a venue with its own column width.
    """
    if not isinstance(kind, str):
        return float(kind)
    k = kind.lower()
    if k == "single":
        return HOUSE_WIDTH_MM["single"]
    if k in ("wide", "double", "page", "full"):
        return HOUSE_WIDTH_MM["wide"]
    raise ValueError("kind must be 'single', 'wide', or a width in mm")


# ------------------------------------------------------------------- outline

def figure_outline_schema():
    return {"type":"object","properties":{
        "claim":{"type":"string"}, "width_mm":{"type":"number"},
        "ncol":{"type":"integer"},
        "row_heights_mm":{"type":"array","items":{"type":"number"}},
        "panels":{"type":"array","items":{"type":"object","properties":{
            "letter":{"type":"string"},
            "role":{"type":"string","enum":["schematic","hero","primary","supporting"]},
            "message":{"type":"string"}, "chart_family":{"type":"string"},
            "data_vid":{"type":["string","null"]}, "data_desc":{"type":"string"},
            "row":{"type":"integer"}, "col":{"type":"integer"},
            "colspan":{"type":"integer"}, "rowspan":{"type":"integer"},
            "label_budget":{"type":"integer"}, "ask":{"type":"string"}},
            "required":["letter","role","message","chart_family","row","col","colspan","ask"]}}},
        "required":["claim","width_mm","ncol","row_heights_mm","panels"]}


# ------------------------------------------------------------------ geometry

def grid_geom(outline, dpi=300, gutter_mm=4):
    """Pixel geometry of the grid: (W, ncol, col_x, col_w, rowh, row_y, gutter).

    FORK: `col_x`/`col_w` are per-column lists computed from exact fractional
    edges. The vendor floors a single `colw` for every column, so the rightmost
    panel can stop up to `ncol-1` px short of `W` and the figure carries a wider
    right margin than left -- visible at print size on a narrow column.
    """
    mm = dpi / 25.4
    W = int(round(outline["width_mm"] * mm))
    ncol = int(outline["ncol"])
    g = int(round(gutter_mm * mm))
    span = W - g * (ncol - 1)
    if span <= 0:
        raise ValueError(f"gutter_mm={gutter_mm} leaves no room for {ncol} columns "
                         f"in {outline['width_mm']} mm")
    edges = [int(round(span * i / ncol)) for i in range(ncol + 1)]
    col_x = [edges[i] + g * i for i in range(ncol)]
    col_w = [edges[i + 1] - edges[i] for i in range(ncol)]
    rowh = [int(round(h * mm)) for h in outline["row_heights_mm"]]
    row_y = [sum(rowh[:i]) + g * i for i in range(len(rowh))]
    return W, ncol, col_x, col_w, rowh, row_y, g


def _panel(outline, letter):
    return next(q for q in outline["panels"] if q["letter"] == letter)


def panel_px(outline, letter, dpi=300, gutter_mm=4):
    """(width, height) in px of one panel's grid slot."""
    W, ncol, col_x, col_w, rowh, row_y, g = grid_geom(outline, dpi, gutter_mm)
    p = _panel(outline, letter)
    c, cs, rs, r = p["col"], p["colspan"], p.get("rowspan", 1), p["row"]
    w = col_x[c + cs - 1] + col_w[c + cs - 1] - col_x[c]
    return w, sum(rowh[r:r + rs]) + g * (rs - 1)


def panel_xy(outline, letter, dpi=300, gutter_mm=4):
    """(x, y) in px of one panel's top-left corner, origin top-left."""
    W, ncol, col_x, col_w, rowh, row_y, g = grid_geom(outline, dpi, gutter_mm)
    p = _panel(outline, letter)
    return col_x[p["col"]], row_y[p["row"]]


def figure_px(outline, dpi=300, gutter_mm=4):
    """(W, H) in px of the composed figure."""
    W, ncol, col_x, col_w, rowh, row_y, g = grid_geom(outline, dpi, gutter_mm)
    return W, row_y[-1] + rowh[-1]


# ----------------------------------------------------------------- fan-out

def panel_task(outline, letter, stem="figure", fig_label="Figure", dpi=300,
               gutter_mm=4, vector_formats=("pdf", "svg"),
               rules_ref="(load `figure-style`)"):
    """Task string for one panel sub-agent.

    FORK vs the vendor prompt, in three places:
      * loads `lab-figure-format` alongside `figure-style` and pins the call
        order, so the house face and the house ladder survive;
      * saves vector alongside the PNG, so `compose_vector` has something to
        tile -- the vendor saves PNG only, which strands the submission format;
      * warns off `save_figure()`, which is the house export helper but saves
        with bbox_inches="tight" and would resize the canvas off the grid.
    """
    p = _panel(outline, letter)
    w, h = panel_px(outline, letter, dpi, gutter_mm)
    neighbours = ", ".join(f"{q['letter']}={q['role']}:{q['chart_family']}"
                           for q in outline["panels"] if q["letter"] != letter)
    data_line = (f"**Data:** `{{{{artifact:{p['data_vid']}}}}}` -- {p.get('data_desc','')}"
                 if p.get("data_vid") else "**Data:** none (schematic).")
    rowmates = [q["letter"] for q in outline["panels"]
                if q["row"] == p["row"] and q["letter"] != letter
                and q.get("rowspan", 1) == p.get("rowspan", 1)]
    share_line = (f"- **Row-mates: {','.join(rowmates)}** -- match y-limits if same metric; series identity "
                  f"labeled ONCE on the row (rightmost panel).") if rowmates else ""
    bud = p.get("label_budget", 4)
    vec = "\n".join(
        f"- `fig.savefig('panel_{letter}.{f}', transparent=True, bbox_inches=None)`"
        f"{'  # vector, tiled by compose_vector' if f == 'pdf' else '  # vector, tiled by compose_svg'}"
        for f in vector_formats)
    saved = ", ".join([f"panel_{letter}.png"] + [f"panel_{letter}.{f}" for f in vector_formats])
    return f"""Produce panel **{letter}** of {fig_label}. You are one of {len(outline['panels'])} parallel panel-makers; the composer tiles results on a {outline['ncol']}-column grid.

## Figure narrative (the one sentence this whole figure makes true)
> {outline['claim']}

Neighbors: {neighbours}

## Your panel
- **role:** {p['role']} · **chart family:** {p['chart_family']}
- **message:** {p['message']}
- **what to show:** {p['ask']}
{data_line}
{share_line}

## House style -- load BOTH skills, and mind the call order
```python
apply_figure_style()   # figure-style: design -- ticks, spines, legend, layout
house_style()          # lab-figure-format: Arial + fallback chain, matched mathtext, fonttype 42
import matplotlib as mpl; mpl.rcParams['savefig.bbox'] = None   # the style helper sets 'tight'
```
`house_style()` goes **last**: `apply_figure_style(font=...)` overwrites
`font.sans-serif` and the mathtext roles, and the house face has to win. Check its
return value -- `installed` False means matplotlib silently substituted another face
and the panel will not match its neighbours.

**Point sizes come from the house ladder, never from per-figure taste:**
{HOUSE_LADDER['title']} pt panel title · {HOUSE_LADDER['label']} pt axis label and body ·
{HOUSE_LADDER['tick']} pt tick label, legend, annotation · {HOUSE_LADDER['dense']} pt dense
in-plot label (gene names, cell values). Nothing below {HOUSE_MIN_PT} pt in the source.
Your box is a final-print-size box -- do not author large and rely on reduction.

## §2 Label discipline -- ceiling AND floor
- **Floor (§2.1, non-negotiable):** every distinct mark, series, glyph, comparator
  is IDENTIFIABLE from this panel alone. Identity labels (what it is) do NOT count
  against the budget and are never removed. Comparator labels must be self-
  explanatory ("prior method", "ablation" -- never "previous"/"old"/"v1").
- **Ceiling:** ≤{bud} *narrative* annotations (callouts, value labels, brackets,
  arrows) beyond title/axis/tick labels and identity labels.
- n=, held-fixed, footnotes, code expansions, exclusion rationale → CAPTION.
- Title is a standalone-parseable takeaway (read-aloud-cold test). Small-multiple
  rows: ONE row-header; per-subplot identity = x-axis label.
- One direction arrow per ROW (leftmost margin).

## §3.5 Fill the box
- Box is **{w}×{h} px (aspect {w/h:.2f})** at {dpi} dpi = {w/dpi*25.4:.1f}×{h/dpi*25.4:.1f} mm on
  the page. Data envelope must occupy ≥75% of it. Set `fig.subplots_adjust(...)` so the
  axes fill the box minus labels; do not center a small plot in a large canvas.

## Hard rendering constraints
- Environment `figures`, Python/matplotlib.
- `fig = plt.figure(figsize=({w/dpi:.4f},{h/dpi:.4f}), dpi={dpi})`
- **Do NOT call `save_figure()` from `lab-figure-format` for a panel.** It is the
  house export helper, but it saves with `bbox_inches="tight"`, which resizes the
  canvas to fit content -- the panel then no longer matches its slot and the
  composer rejects it. Save explicitly instead:
- `fig.savefig('panel_{letter}.png', dpi={dpi}, transparent=True, bbox_inches=None)`
{vec}
- **No `bbox_inches='tight'`, no `plt.tight_layout()`, no `constrained_layout`** --
  each of them changes the pixel dimensions. Use `fig.subplots_adjust(...)` only.
- Dense scatter (>2000 points)? Call `rasterize_dense(ax)` from `lab-figure-format`
  before saving, or the vector files balloon to tens of MB.
- Save with these exact flat names in your own working directory. The composer
  files them under `_build/{stem}/panels/` on receipt via `collect_panels()`;
  do not create directories yourself.
- Reserve top-left ~10×6 mm clear for the composer's panel letter. Do NOT draw your own.
- **§9 Render-then-verify:** after savefig, (a) `from PIL import Image; assert
  Image.open('panel_{letter}.png').size==({w},{h})` -- if not, you used tight_layout/
  constrained_layout/bbox-tight somewhere, undo it; (b) collect every visible `Text`
  window_extent and assert none overlaps another, crosses a spine, or exceeds the canvas.
  Fix and re-save until both pass -- do not ship a panel that fails either check.
- Design rules {rules_ref} apply in full.

`save_artifacts([{', '.join(repr(s) for s in saved.split(', '))}], language='python')`; return `figure_filename` and `labels_used`."""


def save_panel(fig, letter, outline, stem, root=None, dpi=300, gutter_mm=4,
               formats=("png", "pdf", "svg"), outdir=None, verbose=True):
    """Exact-size panel export, for panels drawn locally rather than by a sub-agent.

    Writes into `_build/<stem>/panels/` unless `outdir` overrides it. The house
    `save_figure()` cannot be used here: it saves with bbox_inches="tight", which
    resizes the canvas to its content and takes the panel off the grid.
    """
    import matplotlib as mpl
    w, h = panel_px(outline, letter, dpi, gutter_mm)
    dest = outdir if outdir is not None else figure_paths(stem, root)["panels"]
    os.makedirs(dest, exist_ok=True)
    written = []
    for fmt in formats:
        path = os.path.join(dest, f"panel_{letter}.{fmt}")
        with mpl.rc_context({"savefig.bbox": None}):
            fig.savefig(path, dpi=dpi, transparent=True, bbox_inches=None)
        written.append(path)
    if "png" in formats:
        from PIL import Image
        got = Image.open(os.path.join(dest, f"panel_{letter}.png")).size
        if got != (w, h):
            raise AssertionError(
                f"panel {letter}: saved {got[0]}x{got[1]} px, slot is {w}x{h} px. "
                f"Set figsize=({w/dpi:.4f},{h/dpi:.4f}) at dpi={dpi} and remove any "
                f"tight_layout/constrained_layout/bbox_inches='tight'.")
    if verbose:
        print(f"  panel {letter}: {w}x{h} px -> {dest}/panel_{letter}.{{{','.join(formats)}}}")
    return {fmt: p for fmt, p in zip(formats, written)}


def collect_panels(stem, returned, root=None, formats=("png", "pdf", "svg"),
                   verbose=True):
    """Move what the panel sub-agents returned into this figure's build directory.

    Sub-agents render in their own sandbox and hand back flat `panel_<L>.<fmt>`
    names; this is where those become `_build/<stem>/panels/...` and stop being
    able to collide with another figure's panels. `returned` is
    {letter: path} or {letter: {fmt: path}}.
    """
    import shutil
    dest = figure_paths(stem, root)["panels"]
    os.makedirs(dest, exist_ok=True)
    out = {}
    for L, got in returned.items():
        got = got if isinstance(got, dict) else {os.path.splitext(got)[1].lstrip("."): got}
        out[L] = {}
        for fmt, src in got.items():
            if fmt not in formats or not src:
                continue
            tgt = os.path.join(dest, f"panel_{L}.{fmt}")
            if os.path.abspath(src) != os.path.abspath(tgt):
                shutil.copyfile(src, tgt)
            out[L][fmt] = tgt
    if verbose:
        print(f"  collected {len(out)} panels into {dest}")
    return out


def verify_panels(outline, panel_paths, dpi=300, gutter_mm=4, stem=None,
                  root=None, verbose=True):
    """Check every panel image against its slot BEFORE composing.

    FORK. Returns {letter: {"expected", "actual", "ok"}} plus "all_ok". The
    vendor composer resizes a mismatched panel into place, which rescales its
    type off the house ladder and reports nothing.
    """
    from PIL import Image
    report, all_ok = {}, True
    # A panel sourced from outside this figure's build dir is the collision case:
    # same grid means same slot size, so the size check alone would pass it.
    if stem is not None:
        own = os.path.abspath(figure_paths(stem, root)["panels"])
        stray = sorted(L for L, pth in panel_paths.items()
                       if pth and os.path.abspath(os.path.dirname(pth)) != own)
        if stray and verbose:
            print(f"  WARNING: panel(s) {', '.join(stray)} are not from "
                  f"{own} — check they belong to {stem!r} and not another figure.")
    for p in outline["panels"]:
        L = p["letter"]
        w, h = panel_px(outline, L, dpi, gutter_mm)
        path = panel_paths.get(L)
        if not path or not os.path.exists(path):
            report[L] = {"expected": (w, h), "actual": None, "ok": False}
            all_ok = False
            continue
        got = Image.open(path).size
        ok = got == (w, h)
        report[L] = {"expected": (w, h), "actual": got, "ok": ok}
        all_ok &= ok
    if verbose:
        for L, r in sorted(report.items()):
            a = f"{r['actual'][0]}x{r['actual'][1]}" if r["actual"] else "MISSING"
            mark = "ok" if r["ok"] else "MISMATCH"
            print(f"  {L}: slot {r['expected'][0]}x{r['expected'][1]} px, got {a}  [{mark}]")
    report["all_ok"] = all_ok
    return report


# ------------------------------------------------------------ panel letters

def _face_matches(family, path):
    tok = re.sub(r"[^a-z0-9]", "", family.lower())
    return bool(path) and tok in re.sub(r"[^a-z0-9]", "", os.path.basename(path).lower())


def _resolve_letter_font(font=None, verbose=True):
    """(path, installed) for a bold face, walking the house fallback chain.

    `installed` is True only when the house font itself was found; a fallback
    still returns its path, because a letter in Helvetica beside panels in
    Helvetica is right, while a letter in DejaVu beside them is not.

    FORK, twice over. The vendor hardcodes "DejaVuSans-Bold.ttf", so panel
    letters ship in a face that appears nowhere else in the figure. And the
    lookup has to walk `house_font_chain()` rather than the house name alone --
    matplotlib resolves rcParams through the whole chain, so a single-family
    lookup silently disagrees with the panels on any machine that has a
    fallback installed but not the house font.
    """
    try:
        from matplotlib.font_manager import findfont, FontProperties
    except Exception:
        return None, False
    chain = house_font_chain(font)
    fallback = None
    for i, fam in enumerate(chain):
        try:
            path = findfont(FontProperties(family=[fam], weight="bold"))
        except Exception:
            continue
        if _face_matches(fam, path):
            if verbose and i:
                print(f"  NOTE: {chain[0]!r} is not installed; panel letters use "
                      f"{fam!r}, the next face in the house chain — matching what "
                      f"house_style() gives the panels.")
            return path, i == 0
        fallback = fallback or path
    if verbose:
        print(f"  WARNING: none of {chain} is installed; panel letters fall back to "
              f"{os.path.basename(fallback) if fallback else 'the PIL default'}, "
              f"which will not match the panels.")
    return fallback, False


def _letter_case(letter, case):
    return letter.lower() if case == "lower" else letter.upper()


# ------------------------------------------------------------------ compose

def compose_crops(outline, dpi=300, gutter_mm=4, pad_px=4):
    """Pixel crop boxes ``{letter: (x0, y0, x1, y1)}`` for each panel in the
    composed PNG (origin top-left, matching ``host.view_image(path, crop=...)``
    and ``PIL.Image.crop``). Mirror of ``figure-style.panel_crops`` for the
    PIL-composed case where no live ``matplotlib.Figure`` exists. Use after
    :func:`compose_figure` for the §3.5 perceptual self-QA pass."""
    W, H = figure_px(outline, dpi, gutter_mm)
    out = {}
    for p in outline["panels"]:
        L = p["letter"]
        w, h = panel_px(outline, L, dpi, gutter_mm)
        x, y = panel_xy(outline, L, dpi, gutter_mm)
        out[L] = (max(x - pad_px, 0), max(y - pad_px, 0),
                  min(x + w + pad_px, W), min(y + h + pad_px, H))
    return out


def compose_figure(outline, panel_paths, out_path, dpi=300, gutter_mm=4,
                   letter_font=None, letter_pt=HOUSE_LETTER_PT,
                   letter_case=HOUSE_LETTER_CASE, strict=True, verbose=True):
    """Tile panel PNGs onto the grid and stamp panel letters. Raster.

    This is the REVIEW artifact: fast, croppable, and what the vision reviewer
    reads. It is not the submission file -- use :func:`compose_vector` for that.

    FORK: `strict=True` refuses a panel whose PNG does not match its slot. The
    vendor resizes it, which rescales the type -- a panel 20% too wide has its
    8 pt labels print at 6.4 pt, below the house floor, with nothing raised.
    Pass strict=False only for a throwaway look.
    """
    from PIL import Image, ImageDraw, ImageFont
    W, H = figure_px(outline, dpi, gutter_mm)
    if strict:
        rep = verify_panels(outline, panel_paths, dpi, gutter_mm, verbose=False)
        if not rep["all_ok"]:
            bad = "\n  ".join(
                f"{L}: slot {r['expected'][0]}x{r['expected'][1]} px, got "
                + ("MISSING" if not r["actual"] else f"{r['actual'][0]}x{r['actual'][1]} px")
                for L, r in sorted(rep.items()) if L != "all_ok" and not r["ok"])
            raise AssertionError(
                "panel(s) do not match their grid slot, and resizing them would "
                "rescale the type off the house ladder:\n  " + bad +
                "\nRe-render at panel_px() size, or pass strict=False for a throwaway look.")
    if isinstance(letter_font, str) and letter_font.lower().endswith((".ttf", ".otf")):
        path = letter_font
    else:
        path, _ = _resolve_letter_font(letter_font, verbose=verbose)
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        ft = ImageFont.truetype(path, int(round(letter_pt / 72 * dpi)))
    except Exception:
        ft = ImageFont.load_default()
    dx, dy = int(round(1.5 / 25.4 * dpi)), int(round(1.0 / 25.4 * dpi))
    for p in outline["panels"]:
        L = p["letter"]
        w, h = panel_px(outline, L, dpi, gutter_mm)
        x, y = panel_xy(outline, L, dpi, gutter_mm)
        im = Image.open(panel_paths[L]).convert("RGBA")
        if im.size != (w, h):
            im = im.resize((w, h))
        canvas.paste(im, (x, y), im)
        draw.text((x + dx, y + dy), _letter_case(L, letter_case), fill="black", font=ft)
    canvas.save(out_path)
    if verbose:
        print(f"  composed {out_path}  {W}x{H} px = "
              f"{W/dpi*25.4:.1f}x{H/dpi*25.4:.1f} mm at {dpi} dpi")
    return out_path, (W, H)


def _letters_overlay_pdf(outline, out_path, dpi=300, gutter_mm=4,
                         letter_pt=HOUSE_LETTER_PT, letter_case=HOUSE_LETTER_CASE,
                         font=None):
    """One transparent PDF page carrying only the panel letters, for merging.

    The four rcParams below are the subset of `house_style()` that matters for a
    text-only page. This kernel cannot import lab-figure-format's kernel -- they
    are separate skills -- so that much is duplicated deliberately.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    name = font or HOUSE_FONT
    W, H = figure_px(outline, dpi, gutter_mm)
    with plt.rc_context({"font.family": "sans-serif",
                         "font.sans-serif": house_font_chain(name),
                         "pdf.fonttype": 42, "ps.fonttype": 42}):
        fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi)
        fig.patch.set_alpha(0.0)
        dx, dy = 1.5 / 25.4 * dpi, 1.0 / 25.4 * dpi
        for p in outline["panels"]:
            x, y = panel_xy(outline, p["letter"], dpi, gutter_mm)
            fig.text((x + dx) / W, 1.0 - (y + dy) / H,
                     _letter_case(p["letter"], letter_case),
                     fontsize=letter_pt, fontweight="bold",
                     ha="left", va="top", color="black")
        fig.savefig(out_path, transparent=True, bbox_inches=None, format="pdf")
        plt.close(fig)
    return out_path


def compose_vector(outline, panel_pdf_paths, out_path, dpi=300, gutter_mm=4,
                   letter_pt=HOUSE_LETTER_PT, letter_case=HOUSE_LETTER_CASE,
                   font=None, aspect_tol=0.02, verbose=True):
    """Tile per-panel vector PDFs into ONE vector PDF -- the submission file.

    NEW IN THIS FORK. `compose_figure` produces a raster composite; the house
    export contract (lab-figure-format: "Submit the PDF -- it is vector with the
    font embedded as a subset") cannot be met from a PNG. This places each
    panel's PDF page on the same grid, so text stays live and fonts stay
    embedded, then merges a letters overlay drawn in the house face.

    Verify the result with `verify_embedded_fonts()` from `lab-figure-format`:
    subset prefixes (BQXPMH+ArialMT) are the evidence the font really embedded.
    """
    try:
        from pypdf import PdfReader, PdfWriter, Transformation, PageObject
    except ImportError as e:
        raise ImportError(
            "compose_vector needs pypdf (`pip install pypdf`). Without it the "
            "composite is raster only -- compose_figure still works, but the "
            "result is not submittable to a venue that requires vector.") from e
    W, H = figure_px(outline, dpi, gutter_mm)
    k = 72.0 / dpi                      # px at `dpi` -> PDF points
    page = PageObject.create_blank_page(width=W * k, height=H * k)
    for p in outline["panels"]:
        L = p["letter"]
        w, h = panel_px(outline, L, dpi, gutter_mm)
        x, y = panel_xy(outline, L, dpi, gutter_mm)
        src = PdfReader(panel_pdf_paths[L]).pages[0]
        sw, sh = float(src.mediabox.width), float(src.mediabox.height)
        sx, sy = (w * k) / sw, (h * k) / sh
        if max(sx, sy) > 0 and abs(sx - sy) / max(sx, sy) > aspect_tol:
            print(f"  WARNING: panel {L} PDF is {sw:.1f}x{sh:.1f} pt but its slot is "
                  f"{w*k:.1f}x{h*k:.1f} pt -- non-uniform scale {sx:.3f}x{sy:.3f} will "
                  f"distort the type. Re-render it at the slot aspect.")
        # PDF origin is bottom-left; the grid is measured from the top.
        page.merge_transformed_page(
            src, Transformation().scale(sx, sy).translate(x * k, (H - y - h) * k))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ov = _letters_overlay_pdf(outline, os.path.join(td, "letters.pdf"),
                                  dpi, gutter_mm, letter_pt, letter_case, font)
        page.merge_page(PdfReader(ov).pages[0])
    writer = PdfWriter()
    writer.add_page(page)
    with open(out_path, "wb") as fh:
        writer.write(fh)
    if verbose:
        print(f"  composed {out_path}  {W*k:.1f}x{H*k:.1f} pt = "
              f"{W/dpi*25.4:.1f}x{H/dpi*25.4:.1f} mm (vector)")
    return out_path, (W * k, H * k)


def _prefix_svg_ids(svg_text, pfx):
    """Namespace every id in one panel's SVG so panels cannot collide.

    Matplotlib emits clip-path and glyph ids derived from content hashes, so two
    panels of the same size emit the same ids. Concatenated without this, the
    second panel's clip paths resolve to the first panel's definitions and its
    content is clipped to the wrong box.
    """
    for i in sorted(set(re.findall(r'\bid="([^"]+)"', svg_text)), key=len, reverse=True):
        svg_text = (svg_text.replace(f'id="{i}"', f'id="{pfx}{i}"')
                            .replace(f'url(#{i})', f'url(#{pfx}{i})')
                            .replace(f'href="#{i}"', f'href="#{pfx}{i}"'))
    return svg_text


def _svg_viewbox(root):
    vb = root.get("viewBox")
    if vb:
        parts = [float(v) for v in vb.replace(",", " ").split()]
        return parts[2], parts[3]
    def num(s):
        return float(re.match(r"[-\d.eE+]+", s or "0").group())
    return num(root.get("width")), num(root.get("height"))


def compose_svg(outline, panel_svg_paths, out_path, dpi=300, gutter_mm=4,
                letter_pt=HOUSE_LETTER_PT, letter_case=HOUSE_LETTER_CASE,
                font=None, verbose=True):
    """Tile per-panel SVGs into ONE editable SVG, for Illustrator/Inkscape.

    NEW IN THIS FORK. Stdlib only. Panel text stays live provided the panels
    were saved under the house `svg.fonttype: "none"` -- which `house_style()`
    sets -- so the opener needs the house font installed. Send `svg_text="path"`
    exports outside the lab instead.

    Each panel is clipped to its slot, matching what the PDF page and the PIL
    paste already do. Content a panel drew outside its own canvas is therefore
    lost in every output -- which is what the render-then-verify assertion in
    `panel_task` exists to catch before it gets this far.
    """
    import xml.etree.ElementTree as ET
    SVG = "http://www.w3.org/2000/svg"
    XLINK = "http://www.w3.org/1999/xlink"
    ET.register_namespace("", SVG)
    ET.register_namespace("xlink", XLINK)
    W, H = figure_px(outline, dpi, gutter_mm)
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": f"{W/dpi*25.4:.4f}mm", "height": f"{H/dpi*25.4:.4f}mm",
        "viewBox": f"0 0 {W} {H}", "version": "1.1"})
    defs = ET.SubElement(root, f"{{{SVG}}}defs")
    for p in outline["panels"]:
        L = p["letter"]
        w, h = panel_px(outline, L, dpi, gutter_mm)
        x, y = panel_xy(outline, L, dpi, gutter_mm)
        text = _prefix_svg_ids(open(panel_svg_paths[L], encoding="utf-8").read(), f"{L}-")
        src = ET.fromstring(text)
        vw, vh = _svg_viewbox(src)
        sx, sy = w / vw, h / vh
        # Clip each panel to its slot, so the three outputs agree. A PDF page
        # and a pasted PIL image both clip at the panel edge; an unclipped SVG
        # group would let a label that overruns its canvas bleed into the
        # neighbour -- present in the SVG, absent from the PDF, found at
        # submission. The clip lives on an outer group with no transform so the
        # rect is unambiguously in root coordinates.
        clip_id = f"clip-panel-{L}"
        cp = ET.SubElement(defs, f"{{{SVG}}}clipPath",
                           {"id": clip_id, "clipPathUnits": "userSpaceOnUse"})
        ET.SubElement(cp, f"{{{SVG}}}rect", {"x": f"{x}", "y": f"{y}",
                                             "width": f"{w}", "height": f"{h}"})
        outer = ET.SubElement(root, f"{{{SVG}}}g",
                              {"id": f"panel-{L}", "clip-path": f"url(#{clip_id})"})
        g = ET.SubElement(outer, f"{{{SVG}}}g", {
            "transform": f"translate({x:.4f},{y:.4f}) scale({sx:.6f},{sy:.6f})"})
        for child in list(src):
            if child.tag == f"{{{SVG}}}metadata":
                continue
            g.append(child)
    size_px = letter_pt / 72 * dpi
    dx, dy = 1.5 / 25.4 * dpi, 1.0 / 25.4 * dpi
    for p in outline["panels"]:
        x, y = panel_xy(outline, p["letter"], dpi, gutter_mm)
        t = ET.SubElement(root, f"{{{SVG}}}text", {
            "x": f"{x+dx:.2f}", "y": f"{y+dy+size_px*0.8:.2f}",
            "font-family": ", ".join(house_font_chain(font)) + ", sans-serif",
            "font-weight": "bold",
            "font-size": f"{size_px:.2f}px", "fill": "black"})
        t.text = _letter_case(p["letter"], letter_case)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    if verbose:
        print(f"  composed {out_path}  {W/dpi*25.4:.1f}x{H/dpi*25.4:.1f} mm (vector, editable)")
    return out_path


def compose_all(outline, panels, stem, root=None, dpi=300, gutter_mm=4,
                letter_pt=HOUSE_LETTER_PT, letter_case=HOUSE_LETTER_CASE,
                font=None, write_outline=True, verbose=True):
    """Compose PNG + PDF + SVG into the house manuscript layout, mirroring
    `save_figure`'s contract but for a multi-panel figure.

    Deliverables land in `<root>/{png,pdf,svg}/<stem>.<fmt>`; `outline.json` --
    the thing that actually determines the figure -- is written beside the panels
    in `<root>/_build/<stem>/`, so the composite has a producer on disk rather
    than only in a session transcript.

    `panels` is {letter: {"png": path, "pdf": path, "svg": path}} -- whatever
    formats the panel agents returned. Formats missing from any panel are
    skipped rather than faked.
    """
    import json
    paths = figure_paths(stem, root)
    written = {}

    def have(fmt):
        return bool(panels) and all(v.get(fmt) for v in panels.values())

    if write_outline:
        os.makedirs(paths["build"], exist_ok=True)
        with open(paths["outline"], "w", encoding="utf-8") as fh:
            json.dump(outline, fh, indent=2, sort_keys=True)
        if verbose:
            print(f"  wrote {paths['outline']}")

    common = dict(dpi=dpi, gutter_mm=gutter_mm, letter_pt=letter_pt,
                  letter_case=letter_case, verbose=verbose)
    for fmt in ("png", "pdf", "svg"):
        if not have(fmt):
            if verbose:
                print(f"  skipping {fmt}: not every panel supplied one")
            continue
        path = paths["finals"][fmt]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        p = {L: v[fmt] for L, v in panels.items()}
        if fmt == "png":
            compose_figure(outline, p, path, letter_font=font, strict=True, **common)
        elif fmt == "pdf":
            compose_vector(outline, p, path, font=font, **common)
        else:
            compose_svg(outline, p, path, font=font, **common)
        written[fmt] = path
    return written


# ------------------------------------------------------------------- review

def group_fixes_by_panel(review):
    out = {}
    for v in review.get("violations", []):
        if v.get("severity") not in ("BLOCKER", "MAJOR"):
            continue
        L = v.get("panel_letter") or (v.get("location", " ") + " ")[0]
        out.setdefault(L, []).append(
            f"- **[{v['severity']}]** ({v.get('rule_ref','')}, {v.get('location','')}) "
            f"{v.get('finding','')} **Fix:** {v.get('fix','')}")
    return {k: "\n".join(v) for k, v in out.items()}


def review_schema(per_panel=True):
    """Adversarial composite-review schema. Two feedback tiers:
       - outline_revisions: layout/grid/title-strategy changes (regen affected panels)
       - violations: per-panel issues (regen that panel only)."""
    v_props = {"severity":{"type":"string","enum":["BLOCKER","MAJOR","MINOR"]},
               "rule_ref":{"type":"string"},"location":{"type":"string"},
               "finding":{"type":"string"},"fix":{"type":"string"}}
    if per_panel: v_props["panel_letter"]={"type":"string"}
    return {"type":"object","properties":{
        "editor_verdict":{"type":"string",
            "enum":["accept","minor_revision","major_revision","reject"]},
        "outline_revisions":{"type":"array","description":
            "Figure-level changes that no single panel can fix in isolation: grid geometry "
            "(rowspan/colspan/row_heights), panel add/remove/merge, row-header vs per-panel "
            "titles, label_budget reallocation, whitespace fill (§3.5).",
            "items":{"type":"object","properties":{
                "kind":{"type":"string","enum":["geometry","titles","panel_set","label_budget","other"]},
                "affected_panels":{"type":"array","items":{"type":"string"}},
                "finding":{"type":"string"},"revision":{"type":"string"}},
                "required":["kind","affected_panels","finding","revision"]}},
        "violations":{"type":"array","items":{"type":"object","properties":v_props,
            "required":list(v_props)}},
        "regression_vs_prev":{"type":"array","items":{"type":"string"}},
        "strongest_aspect":{"type":"string"}},
        "required":["editor_verdict","outline_revisions","violations","strongest_aspect"]}


def composite_review_task(composite_vid, outline, rules_vid, prev_vid=None,
                          round_no=1, min_floor=5):
    """Adversarial reviewer's task for the WHOLE composed figure.

    FORK: adds a house-style pass. The vendor reviewer checks the design rules
    only, so a figure can pass review in the wrong typeface at the wrong point
    sizes -- exactly the drift this fork exists to stop.
    """
    panel_tbl = "\n".join(
        f"  {p['letter']}: {p['role']:<10} row{p['row']}+{p.get('rowspan',1)} col{p['col']}+{p['colspan']} "
        f"— {p['chart_family']} — \"{p['message']}\""
        for p in outline["panels"])
    prev_line = (f"\n**Previous version** (for `regression_vs_prev`): `{{{{artifact:{prev_vid}}}}}`"
                 if prev_vid else "")
    return f"""You are an adversarial journal production editor reviewing a COMPOSED multi-panel figure.
Review at THREE levels:

1. **Outline level** (`outline_revisions`): the layout, grid, panel set, title strategy.
   - §3.5 Fill the box: any panel with >25% dead whitespace, or whose natural aspect doesn't
     fit its slot → propose rowspan/colspan/row_heights change.
   - §2.4 Titles: any title that fails the "read it aloud cold" test (cryptic noun fragments),
     or a small-multiple row that should have ONE row-header instead of per-panel titles.
   - Panel set: anything that doesn't earn its space, or a missing panel the claim needs.
2. **Panel level** (`violations`): everything the design rules cover, scoped to one panel.
3. **House style** (`violations`, rule_ref "house"): this figure ships from a lab with a fixed
   style, and consistency across panels is the point.
   - **One typeface.** Every glyph in every panel is {HOUSE_FONT} (or its stated per-journal
     substitute). A panel in a different face is a BLOCKER -- it usually means
     `house_style()` was not called, or was called before `apply_figure_style(font=...)`
     overwrote it. Panel letters must match the panels.
   - **The ladder, not taste.** {HOUSE_LADDER['title']} pt panel title ·
     {HOUSE_LADDER['label']} pt axis label and body · {HOUSE_LADDER['tick']} pt tick, legend,
     annotation · {HOUSE_LADDER['dense']} pt dense in-plot label. Text that reads visibly
     smaller than a {HOUSE_MIN_PT} pt neighbour at this print width is a BLOCKER.
   - **Same metric, same scale.** Row-mates plotting the same quantity share y-limits, and
     the same series is the same colour in every panel it appears in.
   - This figure is {outline['width_mm']:.1f} mm wide -- its true print width. Judge legibility
     at that size, not zoomed in.

## Figure
**Composite:** `{{{{artifact:{composite_vid}}}}}`
**Design rules:** `{{{{artifact:{rules_vid}}}}}`{prev_line}

**Claim:** {outline['claim']}

**Outline** ({outline['ncol']}-col grid, row heights {outline['row_heights_mm']} mm):
{panel_tbl}

## Method
Environment `figures`. Render the composite at full size, then `host.view_image(path, crop=...)`
on each panel (use the outline's row/col to find pixel boxes). For panels with data, spot-check
2–3 plotted values against the CSV. Be calibrated: minimum {min_floor} violations total
(decreasing 5→4→3 by round); do not manufacture. Return ONLY structured output."""


def apply_outline_revisions(outline, revisions):
    """Return the set of panel letters that must regenerate after outline-level revisions.
       (The composer applies the revisions to the outline dict by hand; this just computes scope.)"""
    affected = set()
    for r in revisions:
        affected |= set(r.get("affected_panels", []))
    return affected


def derive_outline(figure_png_path, claim=None, data_hints=None, model=None):
    """Reverse-engineer a figure_outline from an existing composite, so the entry
    point is just '@figure + improve it'. Uses vision; returns an outline dict
    (figure_outline_schema) you MUST review/edit before fan-out -- the image is
    untrusted input and every string field is vision-model-derived. `data_vid`
    is forced to None on every panel (pixels cannot encode a workspace artifact
    id); fill those in yourself from the session's data refs."""
    sch = figure_outline_schema()
    prompt = ("Reverse-engineer this multi-panel figure into a figure_outline. "
              "For each panel: letter, role (hero/primary/supporting/schematic), "
              "chart_family, a one-sentence 'message' (the panel's takeaway -- what "
              "a reader learns from it alone), a one-sentence 'ask' (what the panel "
              "should show), and a label_budget (how many non-axis annotations it "
              "currently uses). Estimate the 12-column grid placement (row, col, "
              "colspan, rowspan) and row_heights_mm from relative panel heights. "
              + (f"Claim (use as outline.claim): {claim}\n" if claim else
                 "Infer the figure's one-sentence claim from its title and panel a.\n")
              + (f"Data hints: {data_hints}\n" if data_hints else ""))
    r = fc_sdk().llm(prompt, images=[figure_png_path],
                     tools=[{"name": "outline", "input_schema": sch}],
                     tool_choice={"type": "tool", "name": "outline"},
                     model=model or fc_sdk().reasoning_model(), max_tokens=4000)
    out = (r.get("tool_use") or [{}])[0].get("input") or {}
    for p in out.get("panels") or []:
        p["data_vid"] = None
    return out
