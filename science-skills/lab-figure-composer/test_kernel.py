#!/usr/bin/env python3
"""Self-test for the lab-figure-composer kernel.

Run it after `claude-science update`, and after any edit here. The point is not
coverage for its own sake -- it is that this skill is a FORK, and every check
below pins one place where it deliberately differs from the vendor
`figure-composer`. If a check starts failing after a vendor bump, the fork and
the upstream have diverged somewhere that matters.

    python3 science-skills/lab-figure-composer/test_kernel.py

Needs matplotlib, numpy, pillow and pypdf. Panel PNGs are synthesized with PIL
rather than matplotlib: some matplotlib/freetype pairings (3.11 + freetype 2.14,
seen on macOS) cannot rasterize a single glyph through Agg while the PDF and SVG
backends stay fine, and this suite is about the tiling, not about Agg.
"""

import os, re, sys, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lfc", os.path.join(HERE, "kernel.py"))
k = importlib.util.module_from_spec(spec); spec.loader.exec_module(k)

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image, ImageDraw
    from pypdf import PdfReader
except ImportError as e:
    print(f"SKIP: {e.name} not installed"); sys.exit(0)

WD = tempfile.mkdtemp(prefix="lfc-test-")
ROOT = os.path.join(WD, "docs", "manuscript", "figures")
STEM = "fig01_methylation_shift"
os.makedirs(k.figure_paths(STEM, ROOT)["panels"], exist_ok=True)
DPI, G = 300, 4
fails = []
def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond: fails.append(name)

outline = {
  "claim": "Treatment shifts methylation genome-wide, and the shift tracks expression.",
  "width_mm": k.house_width_mm("wide"), "ncol": 12,
  "row_heights_mm": [30, 55, 45],
  "panels": [
    {"letter":"a","role":"schematic","row":0,"col":0,"colspan":12,"chart_family":"schematic","message":"design","ask":"show design"},
    {"letter":"b","role":"primary","row":1,"col":0,"colspan":7,"chart_family":"scatter","message":"claim","ask":"scatter"},
    {"letter":"c","role":"supporting","row":1,"col":7,"colspan":5,"chart_family":"box","message":"support","ask":"box"},
    {"letter":"d","role":"supporting","row":2,"col":0,"colspan":12,"chart_family":"line","message":"support","ask":"line"},
  ]}

print("\n== 1. geometry ==")
W, ncol, col_x, col_w, rowh, row_y, g = k.grid_geom(outline, DPI, G)
check("rightmost column ends exactly at W", col_x[-1] + col_w[-1] == W, f"W={W}px")
check("width is 7.20 in exactly", W == 2160 and abs(W/DPI*25.4 - 182.88) < 1e-9, f"{W/DPI*25.4:.4f} mm")
wb,_ = k.panel_px(outline,"b",DPI,G); wc,_ = k.panel_px(outline,"c",DPI,G)
xb = k.panel_xy(outline,"b",DPI,G)[0]; xc = k.panel_xy(outline,"c",DPI,G)[0]
check("b+c span full width with exactly one gutter", xb==0 and xc+wc==W and xc==wb+g, f"b=[0,{wb}] c=[{xc},{xc+wc}]")
check("full-span panel equals W", k.panel_px(outline,"a",DPI,G)[0] == W)
# the vendor's floor-every-column version, for contrast
vend_colw = (W - g*(ncol-1)) // ncol
check("fork recovers the width the vendor floors away",
      vend_colw*ncol + g*(ncol-1) < W and col_x[-1]+col_w[-1] == W,
      f"vendor right edge {vend_colw*ncol+g*(ncol-1)}px vs W={W}px")

print("\n== 2. panels: real vector via matplotlib, PNG via PIL ==")
# NOTE: matplotlib 3.11 + freetype 2.14 on this machine cannot rasterize glyphs
# (Agg raster overflow on ANY text). The PDF/SVG backends are unaffected, so the
# vector path is exercised for real; PNGs are synthesized at exact slot size.
rng = np.random.default_rng(0)
# Same chain house_style() builds, so panels and the letters overlay resolve
# identically -- on a machine without the house font both fall back together.
with plt.rc_context({"font.family":"sans-serif",
                     "font.sans-serif":[k.HOUSE_FONT,"Helvetica","DejaVu Sans"],
                     "pdf.fonttype":42,"svg.fonttype":"none","font.size":8,
                     "xtick.labelsize":7,"ytick.labelsize":7,"axes.labelsize":8}):
    for L in "abcd":
        w, h = k.panel_px(outline, L, DPI, G)
        fig = plt.figure(figsize=(w/DPI, h/DPI), dpi=DPI)
        ax = fig.add_subplot(111)
        ax.plot(rng.normal(size=40), rng.normal(size=40), "o", ms=2)
        ax.set_xlabel(f"x label {L}"); ax.set_ylabel("y label")
        ax.set_title(f"Panel {L} takeaway", fontsize=9, loc="left")
        fig.subplots_adjust(left=0.12, right=0.98, top=0.86, bottom=0.18)
        k.save_panel(fig, L, outline, STEM, root=ROOT, dpi=DPI, gutter_mm=G,
                     formats=("pdf","svg"), verbose=False)
        plt.close(fig)
        im = Image.new("RGBA", (w, h), (255,255,255,0))
        ImageDraw.Draw(im).rectangle([10,10,w-10,h-10], outline=(40,40,40,255), width=2)
        im.save(k.panel_path(STEM, L, "png", ROOT))
paths = {f: {L: k.panel_path(STEM, L, f, ROOT) for L in "abcd"} for f in ("png","pdf","svg")}
check("save_panel wrote vector for every panel", all(os.path.exists(p) for f in ("pdf","svg") for p in paths[f].values()))
rep = k.verify_panels(outline, paths["png"], DPI, G, verbose=False)
check("verify_panels: all match their slot", rep["all_ok"])

print("\n== 3. strict assert fires on a mis-sized panel ==")
Image.open(paths["png"]["c"]).resize((100,100)).save(f"{WD}/bad_c.png")
bad = dict(paths["png"]); bad["c"] = f"{WD}/bad_c.png"
try:
    k.compose_figure(outline, bad, f"{WD}/nope.png", DPI, G, verbose=False)
    check("strict rejects a mis-sized panel", False, "(no exception)")
except AssertionError as e:
    check("strict rejects a mis-sized panel", "c: slot" in str(e), "-> " + str(e).splitlines()[1].strip())
check("strict=False still composes (vendor behaviour, opt-in)",
      bool(k.compose_figure(outline, bad, f"{WD}/lax.png", DPI, G, strict=False, verbose=False)))
try:
    k.save_panel(plt.figure(figsize=(1,1)), "z",
                 {**outline, "panels":[{"letter":"z","role":"primary","row":0,"col":0,
                                        "colspan":12,"chart_family":"x","message":"m","ask":"a"}]},
                 "fig99_scratch", root=ROOT, dpi=DPI, gutter_mm=G,
                 formats=("pdf",), verbose=False)
    check("save_panel tolerates vector-only formats", True)
except Exception as e:
    check("save_panel tolerates vector-only formats", False, repr(e))

print("\n== 4. compose_figure (raster review artifact) ==")
p, (CW, CH) = k.compose_figure(outline, paths["png"], f"{WD}/fig.png", DPI, G, verbose=False)
check("composite size matches grid", Image.open(p).size == (CW, CH), f"{Image.open(p).size}")
check("composite is 7.20 in wide", CW == 2160)
crops = k.compose_crops(outline, DPI, G)
check("crops in bounds", all(0 <= b[0] < b[2] <= CW and 0 <= b[1] < b[3] <= CH for b in crops.values()))
check("crops cover every panel", set(crops) == set("abcd"))

print("\n== 5. compose_vector (the submission file) ==")
p2, (PW, PH) = k.compose_vector(outline, paths["pdf"], f"{WD}/fig.pdf", DPI, G, verbose=False)
data = open(p2,"rb").read()
fonts = sorted({m.decode() for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", data)})
check("PDF page is 7.20 in wide", abs(PW/72 - 7.2) < 1e-6, f"{PW/72*25.4:.2f} mm")
check("PDF page height matches the grid", abs(PH/72*300 - CH) < 1e-6)
# Which face the house font resolves to is an environment fact (CI runners have
# no Arial). What must hold everywhere is that the face actually resolved is the
# one that reaches the PDF -- the vendor bug was stamping a face nobody asked for.
norm = lambda t: re.sub(r"[^a-z0-9]", "", os.path.splitext(os.path.basename(t))[0].lower())
from matplotlib.font_manager import findfont, FontProperties
# Panels resolve through the whole chain (that is what rcParams does), and so
# must the letters -- REG and BOLD agreeing is the property under test.
REG = norm(findfont(FontProperties(family=k.house_font_chain())))
_bold_path, HAVE_HOUSE = k._resolve_letter_font(verbose=False)
BOLD = norm(_bold_path)
print(f"  (house font {k.HOUSE_FONT!r} "
      f"{'installed' if HAVE_HOUSE else 'NOT installed — exercising the fallback chain'}; "
      f"panels {REG!r}, letters {BOLD!r})")
check("letters resolve to the same family as the panels", REG in BOLD,
      f"panels {REG!r} vs letters {BOLD!r}")
check("fonts embedded as TrueType subsets", data.count(b"/FontFile2") > 0 and
      any(REG in norm(f) for f in fonts), str(fonts))
check("no rasterized image XObject", b"/Subtype /Image" not in data)
txt = PdfReader(p2).pages[0].extract_text()
check("panel text is live in the PDF", "Panel a takeaway" in txt and "Panel d takeaway" in txt)
check("panel letters A-D stamped as live text", sorted(set(re.findall(r"\b[A-D]\b", txt))) == ["A","B","C","D"], str(re.findall(r"\b[A-D]\b", txt)))
check("panel letters are stamped in the resolved face, bold",
      any(BOLD in norm(f) for f in fonts), f"looking for {BOLD!r} in {fonts}")

print("\n== 6. compose_svg (editable) ==")
p3 = k.compose_svg(outline, paths["svg"], f"{WD}/fig.svg", DPI, G, verbose=False)
import xml.etree.ElementTree as ET  # noqa: E402
root = ET.parse(p3).getroot()
raw = open(p3, encoding="utf-8").read()
ids = [e.get("id") for e in root.iter() if e.get("id")]
check("SVG parses", root.tag.endswith("svg"))
check("all ids unique after namespacing", len(ids) == len(set(ids)), f"{len(ids)} ids")
check("root width in mm = 7.20 in", root.get("width").endswith("mm") and abs(float(root.get("width")[:-2]) - 182.88) < 0.01, root.get("width"))
groups = [e for e in root if e.tag.endswith("}g") and (e.get("id") or "").startswith("panel-")]
check("one transform group per panel", len(groups) == 4, str([e.get("id") for e in groups]))
texts = [e.text for e in root if e.tag.endswith("}text")]
check("panel letters present as live text", sorted(t for t in texts if t) == ["A","B","C","D"], str(texts))
check("no dangling url(#id) references", not (set(re.findall(r'url\(#([^)]+)\)', raw)) - set(ids)))
# matplotlib emits its own axes clipPaths inside each panel, so count only ours
clips = [e for e in root.iter() if e.tag.endswith("}clipPath")
         and (e.get("id") or "").startswith("clip-panel-")]
check("every panel is clipped to its slot", len(clips) == 4 and
      all((e.get("clip-path") or "").startswith("url(#clip-panel-") for e in groups),
      f"{len(clips)} slot clipPaths, {sum(1 for e in root.iter() if e.tag.endswith(chr(125)+chr(99)+chr(108)+chr(105)+chr(112)+chr(80)+chr(97)+chr(116)+chr(104)))} total")
check("panel text survived as <text>, not outlines", raw.count("<text") > 8 and "x label a" in raw)
# id collision is real without prefixing: same-size panels emit the same clip ids
b_raw = open(paths["svg"]["b"], encoding="utf-8").read()
c_raw = open(paths["svg"]["c"], encoding="utf-8").read()
shared = set(re.findall(r'\bid="([^"]+)"', b_raw)) & set(re.findall(r'\bid="([^"]+)"', c_raw))
check("prefixing was necessary (panels shared raw ids)", len(shared) > 0, f"{len(shared)} shared ids before prefixing")

print("\n== 7. compose_all ==")
allp = {L: {f: paths[f][L] for f in ("png","pdf","svg")} for L in "abcd"}
out = k.compose_all(outline, allp, STEM, root=ROOT, dpi=DPI, gutter_mm=G, verbose=False)
fp = k.figure_paths(STEM, ROOT)
check("deliverables land in {png,pdf,svg}/<stem>.<fmt>",
      out == fp["finals"] and all(os.path.exists(v) for v in out.values()), str(sorted(out)))
check("finals are NOT under _build", all(k.BUILD_DIRNAME not in v for v in out.values()))
check("outline.json written beside the panels", os.path.exists(fp["outline"]))
import json as _json
check("outline.json round-trips the producer",
      _json.load(open(fp["outline"]))["claim"] == outline["claim"])
partial = {L: {"png": paths["png"][L]} for L in "abcd"}
out2 = k.compose_all(outline, partial, "fig02_other", root=ROOT, dpi=DPI, gutter_mm=G, verbose=False)
check("skips formats no panel supplied", set(out2) == {"png"}, str(sorted(out2)))

print("\n== 7b. layout and the collision it prevents ==")
check("composer does not claim a bare figures/ dir",
      k.HOUSE_FIGURE_ROOT == os.path.join("docs", "manuscript", "figures"), k.HOUSE_FIGURE_ROOT)
a = k.figure_paths("fig01_x", ROOT); b = k.figure_paths("fig02_y", ROOT)
check("two figures get separate panel dirs", a["panels"] != b["panels"],
      f"{os.path.basename(os.path.dirname(a['panels']))} vs {os.path.basename(os.path.dirname(b['panels']))}")
check("panel_a.pdf cannot collide across figures",
      k.panel_path("fig01_x", "a", "pdf", ROOT) != k.panel_path("fig02_y", "a", "pdf", ROOT))
check("build tree sits under the figure root, not results/",
      a["build"].startswith(ROOT) and k.BUILD_DIRNAME in a["build"])
check("round composites are kept per round",
      k.round_path(STEM, 1, ROOT) != k.round_path(STEM, 2, ROOT))
# the stray-panel warning: same slot size, wrong figure -- size checks alone pass it
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    k.verify_panels(outline, {L: f"{WD}/panel_{L}.png" for L in "abcd"},
                    DPI, G, stem=STEM, root=ROOT, verbose=True)
check("panels from outside this figure's build dir are flagged", "WARNING" in buf.getvalue(),
      buf.getvalue().strip().splitlines()[0][:70] if buf.getvalue().strip() else "(silent)")
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    k.verify_panels(outline, paths["png"], DPI, G, stem=STEM, root=ROOT, verbose=True)
check("canonical panels raise no warning", "WARNING" not in buf2.getvalue())

print("\n== 8. house defaults ==")
fp, inst = k._resolve_letter_font(verbose=False)
check("house font resolution reports honestly",
      inst == (k.HOUSE_FONT.split()[0].lower() in os.path.basename(fp or "").lower()),
      f"{k.HOUSE_FONT!r} -> {os.path.basename(fp or '')} (installed={inst})")
check("an installed font resolves as installed", k._resolve_letter_font("DejaVu Sans", verbose=False)[1])
check("a missing font is reported, not silently substituted",
      not k._resolve_letter_font("NoSuchFace000", verbose=False)[1])
# The vendor hardcodes DejaVuSans-Bold.ttf. Proving the fork does not means
# showing resolution actually follows the family it is asked for -- which is
# checkable even on a runner where the house font is absent.
serif = os.path.basename(k._resolve_letter_font("DejaVu Serif", verbose=False)[0] or "")
check("the fallback chain is the house chain", k.house_font_chain()[0] == k.HOUSE_FONT and
      list(k.house_font_chain())[1:] == [f for f in k.HOUSE_FALLBACK if f != k.HOUSE_FONT])
check("resolution follows the requested family, not a hardcoded path",
      "serif" in serif.lower(), serif)
check("default letter case is upper (figure-editor convention)", k.HOUSE_LETTER_CASE == "upper")
check("house widths match lab-figure-format", (k.house_width_mm("single"), k.house_width_mm("wide")) == (88.9, 182.88))
check("ladder matches lab-figure-format", k.HOUSE_LADDER == {"title":9,"label":8,"tick":7,"dense":6})
t = k.panel_task(outline, "b", STEM)
check("panel_task pins the call order", "apply_figure_style()" in t and "house_style()" in t and t.index("apply_figure_style()") < t.index("house_style()"))
check("panel_task loads lab-figure-format", "lab-figure-format" in t)
check("panel_task warns off save_figure's bbox_inches='tight'", "Do NOT call `save_figure()`" in t)
check("panel_task asks for vector", "panel_b.pdf" in t and "panel_b.svg" in t)
check("panel_task names the build dir the composer files into", f"_build/{STEM}/panels/" in t)
check("panel_task states the exact slot", f"{wb}×" in t)
r = k.composite_review_task("VID", outline, "RULES")
check("reviewer checks the house typeface", "One typeface" in r and k.HOUSE_FONT in r)
check("reviewer judges at true print width", "182.9 mm wide" in r or "182.88 mm" in r or "mm wide -- its true print width" in r)

print("\n" + (f"ALL CHECKS PASSED ({WD})" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
