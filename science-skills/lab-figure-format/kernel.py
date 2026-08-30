"""Helpers for house figure typography and multi-format export."""
import os

DEFAULT_FONT = "Arial"
FALLBACK_CHAIN = ("Arial", "Helvetica", "DejaVu Sans")
SIZE_LADDER = (8, 7, 6)


def house_style(font=None, family="sans-serif", sizes=None, verbose=True):
    """Apply the house matplotlib style. Returns the resolved rcParams dict.

    font    : family name, e.g. "Arial" (default), "Helvetica", "Times New Roman".
              Pass family="serif" for a serif face.
    sizes   : (base, annotation, tick) point sizes; defaults to (8, 7, 6).

    Sets three things a bare rcParams['font.family'] assignment misses:
      * a fallback chain, so a machine without `font` gets a near neighbour
        rather than silently dropping to DejaVu;
      * matched mathtext, so $...$ is not rendered in DejaVu while the rest
        of the figure uses `font`;
      * pdf/ps.fonttype 42, so vector exports embed editable TrueType
        outlines instead of Type 3.
    """
    import matplotlib as mpl
    from matplotlib.font_manager import findfont, FontProperties

    if font is None:
        font = DEFAULT_FONT
    if sizes is None:
        sizes = SIZE_LADDER
    base, ann, tick = sizes
    chain = [font] + [f for f in FALLBACK_CHAIN if f != font]
    rc = {
        "font.family": family,
        f"font.{family}": chain + list(mpl.rcParams.get(f"font.{family}", [])),
        "font.size": base, "axes.titlesize": base, "axes.labelsize": base,
        "legend.fontsize": ann, "xtick.labelsize": tick, "ytick.labelsize": tick,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlelocation": "left", "axes.titleweight": "normal",
        # 200 matches figure-style's screen dpi, so composing the two skills
        # does not silently downgrade preview resolution
        "figure.dpi": 200, "savefig.dpi": 300,
        "mathtext.fontset": "custom", "mathtext.rm": font,
        "mathtext.it": font + ":italic", "mathtext.bf": font + ":bold",
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    }
    mpl.rcParams.update(rc)
    # resolve the concrete family, not the generic alias: FontProperties parses
    # "sans-serif" as a fontconfig pattern and raises.
    actual = findfont(FontProperties(family=[font])).split(os.sep)[-1]
    ok = font.split()[0].lower().replace(" ", "") in actual.lower().replace(" ", "")
    if verbose:
        print(f"font requested {font!r} -> file loaded {actual!r}")
        if not ok:
            print(f"  WARNING: {font!r} is not installed; matplotlib substituted a fallback.")
    return {"font": font, "resolved_file": actual, "installed": ok}


def available_fonts(filter_common=True):
    """List installed font families. filter_common keeps journal-relevant ones."""
    import matplotlib.font_manager as fm
    names = sorted({f.name for f in fm.fontManager.ttflist})
    if not filter_common:
        return names
    common = ["Arial", "Helvetica", "Helvetica Neue", "Times New Roman", "Times",
              "Calibri", "Cambria", "Georgia", "Verdana", "Myriad Pro", "Minion Pro",
              "Nimbus Sans", "Liberation Sans", "DejaVu Sans", "DejaVu Serif"]
    return [c for c in common if c in names]


def save_figure(fig, stem, outdir="figures", formats=("png", "pdf", "svg"),
                svg_text="none", dpi=300, verbose=True):
    """Write `fig` to <outdir>/<fmt>/<stem>.<fmt> for each format.

    png : raster, for slides and quick viewing
    pdf : vector, fonts embedded as a TrueType subset -- the submission format
    svg : vector, editable in Illustrator/Inkscape

    svg_text="none" keeps text as <text> elements (editable and searchable, but
    the opener needs the font installed). svg_text="path" converts glyphs to
    outlines: renders identically anywhere, no longer editable as text.

    For dense scatter plots pass rasterized=True to the plotting call first --
    see rasterize_dense() -- or vector files balloon (one XML element per point).
    """
    import matplotlib as mpl
    written = []
    for fmt in formats:
        sub = os.path.join(outdir, fmt)
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, f"{stem}.{fmt}")
        with mpl.rc_context({"svg.fonttype": svg_text}):
            fig.savefig(path, dpi=dpi, bbox_inches="tight")
        written.append(path)
        if verbose:
            print(f"  wrote {path}  ({os.path.getsize(path)/1000:.0f} kB)")
    return written


def rasterize_dense(ax, threshold=2000):
    """Mark scatter collections with > `threshold` points as rasterized.

    Text, axes and lines stay vector. Without this a genome-scale volcano SVG
    is tens of MB because every point becomes its own XML element.
    Returns the number of collections rasterized.
    """
    n = 0
    for coll in ax.collections:
        try:
            size = len(coll.get_offsets())
        except Exception:
            continue
        if size > threshold:
            coll.set_rasterized(True)
            n += 1
    return n


def verify_embedded_fonts(pdf_path):
    """Return the font names embedded in a PDF, to confirm the export worked."""
    import re
    data = open(pdf_path, "rb").read()
    names = sorted({m.decode() for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", data)})
    return {"fonts": names, "embedded_streams": data.count(b"/FontFile2"),
            "size_kb": round(len(data) / 1000)}


COLUMN_WIDTH_IN = 3.5
PAGE_WIDTH_IN = 7.2
SINGLE_PANEL_PT = 8


def figure_size(width="single", height=None, aspect=0.75):
    """Return (w, h) inches at a journal-standard width.

    width  : "single" -> 3.5 in (one column), "wide"/"double" -> 7.2 in
             (full page), or an explicit number of inches.
    height : explicit height in inches; if None, derived from `aspect` (h/w).

    Figures must be authored at final print size. A figure drawn 14 in wide and
    reduced to 7.2 in on the page has every font halved -- a 9 pt title prints
    at 4.7 pt.
    """
    if isinstance(width, str):
        key = width.lower()
        if key == "single":
            w = COLUMN_WIDTH_IN
        elif key in ("wide", "double", "page", "full"):
            w = PAGE_WIDTH_IN
        else:
            raise ValueError("width must be 'single', 'wide', or a number")
    else:
        w = float(width)
    return (w, float(height) if height is not None else w * aspect)


def check_print_size(fig, target=None, min_pt=5.0, verbose=True):
    """Check a figure against the print width and report effective font sizes.

    Returns {"width_in", "target_in", "scale", "smallest_pt", "effective_pt",
             "ok"}. `ok` is False when the figure must be reduced to fit, or
            when any text would print below `min_pt`.
    """
    import matplotlib as mpl
    if target is None:
        w = fig.get_size_inches()[0]
        target = COLUMN_WIDTH_IN if w <= COLUMN_WIDTH_IN * 1.15 else PAGE_WIDTH_IN
    width_in = float(fig.get_size_inches()[0])
    scale = target / width_in
    sizes = [t.get_fontsize() for t in fig.findobj(mpl.text.Text)
             if t.get_text().strip() and t.get_visible()]
    smallest = min(sizes) if sizes else float("nan")
    eff = smallest * scale if sizes else float("nan")
    ok = bool(scale >= 0.999 and (not sizes or eff >= min_pt))
    if verbose:
        print(f"width {width_in:.2f} in -> target {target:.2f} in (scale {scale:.2f}x)")
        print(f"  smallest text {smallest:.1f} pt -> prints at {eff:.1f} pt")
        if scale < 0.999:
            print(f"  WARNING: figure is {1/scale:.2f}x too wide; author it at "
                  f"{target} in instead of scaling down.")
        if sizes and eff < min_pt:
            print(f"  WARNING: {eff:.1f} pt is below the {min_pt} pt legibility floor.")
    return {"width_in": width_in, "target_in": target, "scale": scale,
            "smallest_pt": smallest, "effective_pt": eff, "ok": ok}

