"""Helpers for print-plate-assembly. See SKILL.md."""
import os
import re
import json
import hashlib
import pandas as pd

SHEETS = {"letter": (8.5, 11.0), "a4": (8.2677, 11.6929), "legal": (8.5, 14.0)}
REGEN_ROUTES = ("lineage", "replot", "authored", "flagged")
FLAG_STATUSES = ("open", "retracted", "fixed_upstream")
FLAG_COLS = ("letter", "flag_id", "status", "claim", "evidence", "resolution")
MANIFEST_COLS = ("letter", "what", "source_artifact", "source_version_id",
                 "source_panel_index", "producer", "regen_route", "stripped_title",
                 "stripped_annotations", "legend", "panel_pdf", "panel_svg",
                 "panel_sha256", "panel_version_id", "slot", "placed_scale", "flags")


def sheet_geometry(sheet=None, orientation="portrait", margin_in=0.5, gutter_in=0.18):
    """Usable drawing area of a paper sheet, in inches.

    sheet is a name from SHEETS or an explicit (width_in, height_in) pair — use
    the pair when the plate is destined for a manuscript, passing the document's
    TEXT area rather than its paper size. A plate built to the paper size is
    rescaled a second time when the typesetter fits it to the text column, and
    that second scaling is invisible to predict_print_size.
    """
    if isinstance(sheet, (tuple, list)):
        w, h = float(sheet[0]), float(sheet[1])
        sheet = "custom_%gx%g" % (w, h)
    else:
        if sheet is None:
            sheet = "letter"
        w, h = SHEETS[str(sheet).lower()]
    if orientation == "landscape":
        w, h = h, w
    return {"sheet": sheet, "orientation": orientation, "margin_in": margin_in,
            "gutter_in": gutter_in, "page_w_in": w, "page_h_in": h,
            "usable_w_in": w - 2 * margin_in, "usable_h_in": h - 2 * margin_in}


def panel_geometry(paths):
    """Authored size and aspect of each panel file (PDF preferred, PNG tolerated).

    Accepts a list of paths OR the dict returned by plate_paths() — the latter is
    the only thing a caller holds at this point, so passing it directly is the
    intended call. Returns a DataFrame, one row per panel.
    """
    if isinstance(paths, dict) and "panels" in paths:
        paths = [paths["panels"][letter]["pdf"] for letter in paths["panels"]]
    rows = []
    for p in paths:
        rec = {"path": p, "kind": os.path.splitext(p)[1].lstrip(".").lower(),
               "width_in": None, "height_in": None, "aspect": None, "error": ""}
        try:
            if rec["kind"] == "pdf":
                import pypdf
                box = pypdf.PdfReader(p).pages[0].mediabox
                rec["width_in"] = float(box.width) / 72.0
                rec["height_in"] = float(box.height) / 72.0
            else:
                from PIL import Image
                im = Image.open(p)
                dpi = (im.info.get("dpi") or (300.0, 300.0))[0] or 300.0
                rec["width_in"] = im.size[0] / float(dpi)
                rec["height_in"] = im.size[1] / float(dpi)
            rec["aspect"] = rec["width_in"] / rec["height_in"]
        except Exception as exc:
            rec["error"] = str(exc)
        rows.append(rec)
    return pd.DataFrame(rows)


def propose_layout(geom, sheet=None, orientation="portrait", ncols=None,
                   margin_in=0.5, gutter_in=0.18, out_path=None, letters=None,
                   spans=None):
    """Propose a grid spec for a plate. Reading order is the row order of geom.

    spans maps a panel letter to (rowspan, colspan) for panels that must occupy
    more than one cell — a wide time-course above two square panels, say.
    Placement is row-major into the first block of free cells that fits.
    """
    if letters is None:
        letters = "abcdefghijklmnopqrstuvwxyz"
    if spans is None:
        spans = {}
    page = sheet_geometry(sheet, orientation, margin_in, gutter_in)
    n = len(geom)
    if ncols is None:
        mean_aspect = float(pd.to_numeric(geom["aspect"], errors="coerce").mean() or 1.0)
        ncols = 1 if n == 1 else (2 if mean_aspect >= 0.9 or n <= 4 else 1)
        ncols = min(ncols, n)
    records = geom.to_dict("records")
    taken = set()
    slots = []
    row, col = 0, 0
    for i, rec in enumerate(records):
        rspan, cspan = spans.get(letters[i], (1, 1))
        cspan = min(int(cspan), ncols)
        rspan = int(rspan)
        while True:
            if col + cspan > ncols:
                row, col = row + 1, 0
                continue
            block = [(row + dr, col + dc) for dr in range(rspan) for dc in range(cspan)]
            if not any(cell in taken for cell in block):
                break
            col += 1
        taken.update(block)
        slots.append({"row": row, "col": col, "rowspan": rspan, "colspan": cspan})
        col += cspan
    nrows = max(s["row"] + s["rowspan"] for s in slots) if slots else 1
    cell_w = (page["usable_w_in"] - gutter_in * (ncols - 1)) / ncols
    cell_h = (page["usable_h_in"] - gutter_in * (nrows - 1)) / nrows
    panels = []
    for i, (rec, slot) in enumerate(zip(records, slots)):
        box_w = cell_w * slot["colspan"] + gutter_in * (slot["colspan"] - 1)
        box_h = cell_h * slot["rowspan"] + gutter_in * (slot["rowspan"] - 1)
        aw = rec.get("width_in") or box_w
        ah = rec.get("height_in") or box_h
        scale = min(box_w / aw, box_h / ah) if aw and ah else 1.0
        panels.append({"path": rec["path"], "letter": letters[i],
                       "row": slot["row"], "col": slot["col"],
                       "rowspan": slot["rowspan"], "colspan": slot["colspan"],
                       "authored_w_in": aw, "authored_h_in": ah,
                       "box_w_in": box_w, "box_h_in": box_h,
                       "placed_w_in": aw * scale, "placed_h_in": ah * scale,
                       "placed_scale": scale})
    spec = dict(page)
    spec.update({"nrows": nrows, "ncols": ncols, "cell_w_in": cell_w,
                 "cell_h_in": cell_h, "panels": panels})
    if out_path is not None:
        json.dump(spec, open(out_path, "w"), indent=1)
    return spec


def compile_plate(spec, out_pdf, letter_pt=9.0, letter_weight="bold", stamp_letters=True,
                  letter_font=None):
    """Place panel PDFs into their slots on a blank sheet. Vector throughout."""
    import pypdf
    import matplotlib
    from matplotlib.figure import Figure
    if isinstance(spec, str):
        spec = json.load(open(spec))
    if letter_font is None:
        letter_font = ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans")
    pw, ph = spec["page_w_in"] * 72.0, spec["page_h_in"] * 72.0
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=pw, height=ph)
    marks = []
    for pan in spec["panels"]:
        x0 = spec["margin_in"] + pan["col"] * (spec["cell_w_in"] + spec["gutter_in"])
        y_top = spec["margin_in"] + pan["row"] * (spec["cell_h_in"] + spec["gutter_in"])
        box_w = pan.get("box_w_in", spec["cell_w_in"])
        box_h = pan.get("box_h_in", spec["cell_h_in"])
        y0 = spec["page_h_in"] - y_top - box_h
        cx = x0 + (box_w - pan["placed_w_in"]) / 2.0
        cy = y0 + (box_h - pan["placed_h_in"]) / 2.0
        src = pypdf.PdfReader(pan["path"]).pages[0]
        t = pypdf.Transformation().scale(pan["placed_scale"]).translate(cx * 72.0, cy * 72.0)
        page.merge_transformed_page(src, t)
        marks.append((pan["letter"], max(0.08, cx - 0.22), cy + pan["placed_h_in"]))
    if stamp_letters and marks:
        fig = Figure(figsize=(spec["page_w_in"], spec["page_h_in"]))
        for letter, lx, ly in marks:
            fig.text(lx / spec["page_w_in"], ly / spec["page_h_in"], letter,
                     fontsize=letter_pt, fontweight=letter_weight,
                     ha="left", va="top")
        overlay = out_pdf + ".letters.pdf"
        # A producing script's rcParams are global and outlive it: savefig.bbox
        # left at "tight" crops this overlay to the glyphs and the letters land
        # in the wrong corner. Pin it for this write.
        # Pin the FACE too: the overlay is drawn in a fresh Figure, so it takes
        # whatever font.family is ambient — matplotlib's DejaVu default in a
        # clean kernel. The panel letters then embed a face no panel uses, and
        # the composite fails a font check every panel passes on its own.
        with matplotlib.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0.0,
                                    "font.family": "sans-serif",
                                    "font.sans-serif": list(letter_font),
                                    "pdf.fonttype": 42}):
            fig.savefig(overlay, format="pdf", transparent=True)
        page.merge_page(pypdf.PdfReader(overlay).pages[0])
        os.remove(overlay)
    with open(out_pdf, "wb") as fh:
        writer.write(fh)
    return out_pdf


def predict_print_size(spec, authored_min_pt=None, floor_pt=5.0):
    """Smallest text size as printed, per panel, from the placement scale."""
    if isinstance(spec, str):
        spec = json.load(open(spec))
    if authored_min_pt is None:
        authored_min_pt = 6.0
    rows = []
    for pan in spec["panels"]:
        pt = authored_min_pt * pan["placed_scale"]
        rows.append({"letter": pan["letter"], "path": pan["path"],
                     "placed_scale": round(pan["placed_scale"], 3),
                     "authored_min_pt": authored_min_pt,
                     "printed_min_pt": round(pt, 2),
                     "ok": pt >= floor_pt})
    return pd.DataFrame(rows)


def write_plate_manifest(rows, out_path=None):
    """Emit the plate manifest with the canonical column order."""
    if out_path is None:
        out_path = "plate_manifest.tsv"
    df = pd.DataFrame(rows)
    for col in MANIFEST_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[list(MANIFEST_COLS) + [c for c in df.columns if c not in MANIFEST_COLS]]
    if "panel_pdf" in df.columns:
        hashes = []
        for p in df["panel_pdf"]:
            try:
                hashes.append(hashlib.sha256(open(p, "rb").read()).hexdigest())
            except Exception:
                hashes.append("")
        df["panel_sha256"] = [h or s for h, s in zip(hashes, df["panel_sha256"])]
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(
                lambda v: re.sub(r"[\r\n]+", "; ", v).strip() if isinstance(v, str) else v)
    df.to_csv(out_path, sep="\t", index=False)
    return df

def plate_paths(slug, panel_letters, root=None, make_dirs=True):
    """Canonical output paths for one plate, plus the exact save_artifacts list.

    Filenames carry the slug even inside the plate directory. That is
    deliberate: save_artifacts derives the artifact name from the basename and
    the store discards the directory, so a bare panel_a.pdf becomes permanently
    ambiguous the moment a second plate exists. Naming the file once, here,
    removes the step where disk name and artifact name can diverge.
    """
    if root is None:
        root = "plates"
    stem = "plate_" + str(slug)
    pdir = os.path.join(root, str(slug))
    andir = os.path.join(pdir, "panels")
    if make_dirs:
        os.makedirs(andir, exist_ok=True)
    out = {"slug": slug, "stem": stem, "dir": pdir, "panels_dir": andir,
           "plate_pdf": os.path.join(pdir, stem + ".pdf"),
           "proof_png": os.path.join(pdir, stem + "_proof.png"),
           "layout_json": os.path.join(pdir, stem + "_layout.json"),
           "manifest_tsv": os.path.join(pdir, stem + "_manifest.tsv"),
           "legend_md": os.path.join(pdir, stem + "_legend.md"),
           "flags_csv": os.path.join(pdir, stem + "_flags.csv"),
           "sources_tar": os.path.join(pdir, stem + "_sources.tar.gz"),
           "panels": {}}
    for letter in panel_letters:
        tag = "%s_panel_%s" % (stem, letter)
        out["panels"][letter] = {
            "pdf": os.path.join(andir, tag + ".pdf"),
            "svg": os.path.join(andir, tag + ".svg"),
            "png": os.path.join(andir, tag + ".png"),
            "script": os.path.join(andir, "%s_regen_panel_%s.py" % (stem, letter))}
    out["bundle_contents"] = [out["panels"][k][x] for k in panel_letters
                              for x in ("svg", "script")]
    out["save_files"] = ([out["plate_pdf"], out["proof_png"], out["layout_json"],
                          out["manifest_tsv"], out["legend_md"], out["flags_csv"]]
                         + [out["panels"][k]["pdf"] for k in panel_letters]
                         + [out["sources_tar"]])
    return out


def bundle_plate_sources(paths):
    """Tar the per-panel SVGs and regeneration scripts into one artifact."""
    import tarfile
    missing = [p for p in paths["bundle_contents"] if not os.path.exists(p)]
    with tarfile.open(paths["sources_tar"], "w:gz") as tf:
        for p in paths["bundle_contents"]:
            if os.path.exists(p):
                tf.add(p, arcname=os.path.join(paths["stem"] + "_sources",
                                               os.path.basename(p)))
    return {"tar": paths["sources_tar"], "n_added": len(paths["bundle_contents"]) - len(missing),
            "missing": missing}

CMYK_PROFILE_CANDIDATES = ("/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc",
                           "/usr/share/color/icc/ghostscript/default_cmyk.icc",
                           "/usr/share/color/icc/colord/CoatedFOGRA39.icc")


def find_cmyk_profile(icc_path=None):
    """Locate an ICC CMYK profile. Journals that name a press profile ship it."""
    if icc_path is not None:
        if not os.path.exists(icc_path):
            raise FileNotFoundError("ICC profile not found: %s" % icc_path)
        return icc_path
    for p in CMYK_PROFILE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def export_plate_rasters(plate_pdf, dpis=None, fmt="tiff", cmyk=False, icc_path=None,
                         out_dir=None, stem=None):
    """Render the vector plate to submission-grade rasters at declared DPIs.

    Terminal step: no external binary, no hand-finishing. Returns a frame of
    what was written, including the effective pixel dimensions journals ask for.
    """
    import pypdfium2
    from PIL import Image, ImageCms
    if dpis is None:
        dpis = (300, 600, 900)
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(plate_pdf) or ".", "raster")
    if stem is None:
        stem = os.path.splitext(os.path.basename(plate_pdf))[0]
    os.makedirs(out_dir, exist_ok=True)
    ext = {"tiff": ".tif", "tif": ".tif", "png": ".png"}[str(fmt).lower()]
    prof = find_cmyk_profile(icc_path) if cmyk else None
    if cmyk and prof is None:
        raise RuntimeError("cmyk=True but no ICC CMYK profile found; pass icc_path=")
    page = pypdfium2.PdfDocument(plate_pdf)[0]
    rows = []
    for dpi in dpis:
        img = page.render(scale=float(dpi) / 72.0).to_pil().convert("RGB")
        mode = "RGB"
        if cmyk:
            src = ImageCms.createProfile("sRGB")
            img = ImageCms.profileToProfile(img, src, ImageCms.getOpenProfile(prof),
                                            outputMode="CMYK")
            mode = "CMYK"
        name = "%s_%dppi%s" % (stem, dpi, ext)
        path = os.path.join(out_dir, name)
        kw = {"dpi": (dpi, dpi)}
        if ext == ".tif":
            kw["compression"] = "tiff_lzw"
        img.save(path, **kw)
        rows.append({"dpi": dpi, "mode": mode, "px_w": img.size[0], "px_h": img.size[1],
                     "path": path, "bytes": os.path.getsize(path),
                     "icc": os.path.basename(prof) if prof else ""})
    return pd.DataFrame(rows)

def write_plate_flags(flags, out_path=None):
    """Structured flag ledger — one row per flag, with a life cycle.

    Rule 3 says flag, don't fix. A flag can also turn out to be WRONG: a defect
    read off a low-resolution proof may not survive re-reading at print
    resolution. Free text in a manifest cell cannot record that a flag was
    retracted, or why. status is one of FLAG_STATUSES.
    """
    if out_path is None:
        out_path = "plate_flags.csv"
    df = pd.DataFrame(list(flags))
    for col in FLAG_COLS:
        if col not in df.columns:
            df[col] = ""
    bad = sorted(set(str(s) for s in df["status"]) - set(FLAG_STATUSES))
    if bad:
        raise ValueError("unknown flag status %s; use one of %s" % (bad, list(FLAG_STATUSES)))
    df = df[list(FLAG_COLS) + [c for c in df.columns if c not in FLAG_COLS]]
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(
                lambda v: re.sub(r"[\r\n]+", "; ", v).strip() if isinstance(v, str) else v)
    df.to_csv(out_path, index=False)
    return df


def write_plate_legend(rows, out_path=None, title=None, figure_label=None, preamble=None,
                       opening=None, closing=None, methods=None, abbreviations=None,
                       scope_note=None, word_cap=None):
    """Assemble the journal legend FROM the manifest rows. Never invents prose.

    rows is the same list passed to write_plate_manifest, so the legend is a
    serialisation of the manifest rather than a parallel document that can
    disagree with it. word_cap warns and never truncates: which sentence to cut
    is an author's decision, not a helper's.

    Three text slots, and the difference between them decides the word count:

    - opening -- the design sentence ("Cells were treated with ... and profiled
      by ..."). Joins the title's paragraph, INSIDE the caption, and IS counted.
    - closing -- the statistics sentence ("n = 3 per condition except ...").
      Its own paragraph after the last panel, INSIDE the caption, IS counted.
    - preamble -- front matter for whoever reads this file (which manifest the
      numbers came from). Sits OUTSIDE the caption behind a rule and is NOT
      counted, because a journal never sees it.

    A caption has sentences belonging to no single panel. Without opening and
    closing they can only go in preamble, where they land outside the caption
    and outside the count the cap is checked against.
    """
    if out_path is None:
        out_path = "plate_legend.md"
    # Rows with a blank letter are unlettered plate elements -- a shared colour
    # key, a scale bar -- not caption blocks. Including them emitted a "**()**"
    # block that sorted ahead of (A). They are dropped here, so the same rows
    # list can be passed to write_plate_manifest and to this function.
    recs = [r for r in rows if str(r.get("letter", "")).strip()]
    recs = sorted(recs, key=lambda r: str(r.get("letter", "")))
    missing = [str(r.get("letter")) for r in recs
               if not str(r.get("legend") or "").strip()]
    if missing:
        raise ValueError("panel(s) %s have an empty legend column; write the legend in the "
                         "manifest row, not here" % ", ".join(missing))
    label = figure_label or "Figure"
    if title:
        # Journals set the title sentence with terminal punctuation INSIDE the
        # bold. Without it, an `opening` that follows runs on: "**Figure 2.
        # Claim** Cells were treated ..." reads as one ungrammatical sentence.
        _t = str(title).strip()
        if _t and _t[-1] not in ".?!":
            _t += "."
        head = "**%s. %s**" % (label, _t)
    else:
        head = ""
    if opening:
        # The design sentence shares the title's paragraph -- the journal
        # convention is "**Figure 2. Claim.** Cells were treated with ..."
        head = ((head + " " + str(opening).strip()).strip() if head
                else str(opening).strip())
    blocks = ["**(%s)** %s" % (str(r["letter"]).upper(), str(r["legend"]).strip())
              for r in recs]
    tail = [str(closing).strip()] if closing else []
    caption = "\n\n".join(([head] if head else []) + blocks + tail)
    caption_words = len(re.findall(r"\S+", re.sub(r"[*_`]", "", caption)))
    over = bool(word_cap) and caption_words > int(word_cap)
    out = ["# %s — legend" % label, ""]
    if preamble:
        out += [str(preamble).strip(), "", "---", ""]
    out += ["## Journal-ready legend", "", caption, ""]
    if methods:
        out += ["## Points to carry into supplementary methods rather than the legend", ""]
        out += [str(m).strip() + "\n" for m in methods]
    if scope_note:
        out += ["## Scope", "", str(scope_note).strip(), ""]
    if abbreviations:
        items = (sorted(abbreviations.items()) if isinstance(abbreviations, dict)
                 else [(a, "") for a in abbreviations])
        out += ["## Abbreviations", ""]
        out += ["- **%s**%s" % (a, " — " + b if b else "") for a, b in items]
        out.append("")
    if word_cap:
        verdict = "OVER" if over else "within"
        out += ["", "> Caption section: %d words, %s the %d-word cap. Nothing was truncated — "
                    "decide what to cut." % (caption_words, verdict, int(word_cap))]
    with open(out_path, "w") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    return {"path": out_path, "caption_words": caption_words, "over_cap": over,
            "panels": len(recs)}

def assert_plate_complete(paths, require=None):
    """Fail early, by name, if anything in save_files has not been written yet.

    save_files is an INTENT list — it names every output a finished plate owes,
    including the legend and the flag ledger. A caller who composes the plate but
    never calls write_plate_legend gets a missing-file error at save time, far
    from the cause. Call this immediately before saving.
    """
    if require is None:
        require = paths.get("save_files", [])
    missing = [p for p in require if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(
            "plate '%s' is incomplete — %d declared output(s) not written: %s. "
            "Legend comes from write_plate_legend(rows, paths['legend_md'], ...); "
            "the ledger from write_plate_flags(flags, paths['flags_csv']); "
            "the sources bundle from bundle_plate_sources(paths)."
            % (paths.get("slug", "?"), len(missing), ", ".join(os.path.basename(m) for m in missing)))
    return list(require)
