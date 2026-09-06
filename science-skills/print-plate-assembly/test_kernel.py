"""Regression tests for print-plate-assembly. Run: pytest test_kernel.py"""
import os
import sys
import json
import tempfile

import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kernel import (MANIFEST_COLS, FLAG_COLS, FLAG_STATUSES, REGEN_ROUTES,
                    plate_paths, panel_geometry, propose_layout, compile_plate,
                    write_plate_manifest, write_plate_legend, write_plate_flags)


def make_panel(path, w=2.0, h=1.5, text="x"):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    fig = Figure(figsize=(w, h))
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, text, ha="center")
    fig.savefig(path, format="pdf")
    return path


def rows_two():
    return [{"letter": "A", "legend": "First panel legend.\nWith a hard newline.",
             "regen_route": "authored", "flags": "one\ntwo"},
            {"letter": "B", "legend": "Second panel legend.", "regen_route": "lineage",
             "flags": ""}]


# ---- #8 manifest is line-oriented -------------------------------------------

def test_manifest_one_physical_line_per_row(tmp_path):
    out = str(tmp_path / "m.tsv")
    write_plate_manifest(rows_two(), out)
    assert sum(1 for _ in open(out)) == len(rows_two()) + 1


def test_manifest_column_order_unchanged(tmp_path):
    df = write_plate_manifest(rows_two(), str(tmp_path / "m.tsv"))
    assert list(df.columns)[:len(MANIFEST_COLS)] == list(MANIFEST_COLS)


def test_manifest_newlines_become_separators(tmp_path):
    out = str(tmp_path / "m.tsv")
    write_plate_manifest(rows_two(), out)
    back = pd.read_csv(out, sep="\t")
    assert "; " in back.loc[0, "legend"] and "\n" not in back.loc[0, "legend"]


# ---- #6 authored route -------------------------------------------------------

def test_authored_is_a_documented_route():
    assert "authored" in REGEN_ROUTES


# ---- #1 legend writer --------------------------------------------------------

def test_legend_panel_order_and_verbatim(tmp_path):
    out = str(tmp_path / "l.md")
    res = write_plate_legend(rows_two(), out, title="A title.", figure_label="Figure 2")
    text = open(out).read()
    assert res["panels"] == 2
    assert text.index("**(A)**") < text.index("**(B)**")
    assert "Second panel legend." in text


def test_legend_refuses_empty_panel_legend(tmp_path):
    rows = rows_two()
    rows[1]["legend"] = "   "
    with pytest.raises(ValueError) as exc:
        write_plate_legend(rows, str(tmp_path / "l.md"))
    assert "B" in str(exc.value)


def test_legend_word_cap_warns_without_truncating(tmp_path):
    out = str(tmp_path / "l.md")
    res = write_plate_legend(rows_two(), out, title="A title.", word_cap=3)
    text = open(out).read()
    assert res["over_cap"] is True and res["caption_words"] > 3
    assert "Second panel legend." in text


def test_legend_sections_present(tmp_path):
    out = str(tmp_path / "l.md")
    write_plate_legend(rows_two(), out, title="T.", methods=["A long caveat."],
                       abbreviations={"NES": "normalised enrichment score"},
                       scope_note="Applies to B16 only.")
    text = open(out).read()
    for marker in ("supplementary methods", "A long caveat.", "## Abbreviations",
                   "NES", "## Scope"):
        assert marker in text


def test_opening_and_closing_land_inside_the_caption(tmp_path):
    """The design and statistics sentences belong to no panel but ARE caption."""
    out = str(tmp_path / "l.md")
    write_plate_legend(rows_two(), out, title="T.", figure_label="Figure 9",
                       opening="Cells were treated and profiled.",
                       closing="n = 3 per condition.",
                       methods=["A long caveat."])
    text = open(out).read()
    i_cap = text.index("## Journal-ready legend")
    i_meth = text.index("supplementary methods")
    for probe in ("Cells were treated and profiled.", "n = 3 per condition."):
        assert i_cap < text.index(probe) < i_meth, probe
    # opening shares the title's paragraph, as journals set it
    assert "**Figure 9. T.** Cells were treated and profiled." in text
    # closing is its own paragraph AFTER the last panel block
    assert text.index("Second panel legend.") < text.index("n = 3 per condition.")


def test_unlettered_rows_are_not_caption_blocks(tmp_path):
    """A shared colour key is a plate element, not a panel; it emitted "**()**"."""
    out = str(tmp_path / "l.md")
    rows = rows_two() + [dict(letter="", what="colour key", legend="Colour key.",
                              source_file="key.pdf", regen_route="authored")]
    res = write_plate_legend(rows, out, title="T.", figure_label="Figure 9")
    text = open(out).read()
    assert "**()**" not in text
    assert res["panels"] == 2
    assert "Colour key." not in text


def test_title_gets_terminal_punctuation(tmp_path):
    """Without it, an opening that follows the title runs on as one sentence."""
    out = str(tmp_path / "l.md")
    write_plate_legend(rows_two(), out, title="A claim with no period",
                       figure_label="Figure 9", opening="Cells were treated.")
    text = open(out).read()
    assert "**Figure 9. A claim with no period.** Cells were treated." in text
    # an author-supplied terminator is not doubled
    out2 = str(tmp_path / "m.md")
    write_plate_legend(rows_two(), out2, title="Already ends here.",
                       figure_label="Figure 9")
    assert "**Figure 9. Already ends here.**" in open(out2).read()


def test_opening_and_closing_are_counted_but_preamble_is_not(tmp_path):
    """Controlled: identical title, one slot added at a time."""
    base = write_plate_legend(rows_two(), str(tmp_path / "a.md"), title="T.")
    with_pre = write_plate_legend(rows_two(), str(tmp_path / "b.md"), title="T.",
                                  preamble="Read back from the manifest.")
    with_open = write_plate_legend(rows_two(), str(tmp_path / "c.md"), title="T.",
                                   opening="One two three four five.")
    with_close = write_plate_legend(rows_two(), str(tmp_path / "d.md"), title="T.",
                                    closing="Six seven eight.")
    assert with_pre["caption_words"] == base["caption_words"]
    assert with_open["caption_words"] == base["caption_words"] + 5
    assert with_close["caption_words"] == base["caption_words"] + 3


def test_word_cap_sees_caption_level_prose(tmp_path):
    """The bug this closes: caption text in preamble escaped the cap."""
    out = str(tmp_path / "l.md")
    base = write_plate_legend(rows_two(), str(tmp_path / "base.md"), title="T.")
    cap = base["caption_words"] + 2
    res = write_plate_legend(rows_two(), out, title="T.", word_cap=cap,
                             opening="One two three four five six.")
    assert res["over_cap"] is True
    assert "Nothing was truncated" in open(out).read()


def test_opening_without_a_title_still_opens_the_caption(tmp_path):
    out = str(tmp_path / "l.md")
    write_plate_legend(rows_two(), out, opening="Standalone opening.")
    text = open(out).read()
    assert text.index("## Journal-ready legend") < text.index("Standalone opening.")
    assert text.index("Standalone opening.") < text.index("**(A)**")


# ---- #7 structured flags -----------------------------------------------------

def test_flags_columns_and_roundtrip(tmp_path):
    out = str(tmp_path / "f.csv")
    df = write_plate_flags([{"letter": "A", "flag_id": "f1", "status": "retracted",
                             "claim": "label occluded", "evidence": "re-read at 200 dpi",
                             "resolution": "metrics artifact"}], out)
    assert list(df.columns)[:len(FLAG_COLS)] == list(FLAG_COLS)
    assert pd.read_csv(out).loc[0, "status"] == "retracted"


def test_flags_reject_unknown_status(tmp_path):
    with pytest.raises(ValueError):
        write_plate_flags([{"letter": "A", "status": "maybe"}], str(tmp_path / "f.csv"))


def test_all_flag_statuses_accepted(tmp_path):
    write_plate_flags([{"letter": "A", "status": s} for s in FLAG_STATUSES],
                      str(tmp_path / "f.csv"))


# ---- #1/#7 wiring ------------------------------------------------------------

def test_plate_paths_exposes_legend_and_flags(tmp_path):
    p = plate_paths("t", ["a"], root=str(tmp_path))
    joined = " ".join(p["save_files"])
    assert "_legend.md" in joined and "_flags.csv" in joined
    assert p["legend_md"].endswith("plate_t_legend.md")


# ---- #9 signatures -----------------------------------------------------------

def test_panel_geometry_accepts_plate_paths_dict(tmp_path):
    p = plate_paths("t", ["a", "b"], root=str(tmp_path))
    for letter in ("a", "b"):
        make_panel(p["panels"][letter]["pdf"])
    geom = panel_geometry(p)
    assert len(geom) == 2 and geom["width_in"].notna().all()


# ---- #5 (pulled forward) composite typography --------------------------------

def test_letter_overlay_does_not_embed_ambient_face(tmp_path):
    import matplotlib
    import pypdf
    p = plate_paths("t", ["a"], root=str(tmp_path))
    make_panel(p["panels"]["a"]["pdf"])
    geom = panel_geometry(p)
    spec = propose_layout(geom, sheet="letter", out_path=p["layout_json"])
    with matplotlib.rc_context({"font.family": "sans-serif",
                                "font.sans-serif": ["DejaVu Sans"]}):
        compile_plate(p["layout_json"], p["plate_pdf"],
                      letter_font=("Liberation Sans", "Helvetica"))
    names = []
    for page in pypdf.PdfReader(p["plate_pdf"]).pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for key in fonts:
            names.append(str(fonts[key].get_object().get("/BaseFont", "")))
    # The PANEL legitimately carries the ambient face; the OVERLAY must not.
    # Proof the pin took effect is a face from letter_font in the composite.
    assert any(("Helvetica" in n) or ("Liberation" in n) for n in names), names

def test_export_plate_rasters_returns_dataframe(tmp_path):
    from kernel import export_plate_rasters
    p = plate_paths("t", ["a"], root=str(tmp_path))
    make_panel(p["panels"]["a"]["pdf"])
    geom = panel_geometry(p)
    propose_layout(geom, sheet="letter", out_path=p["layout_json"])
    compile_plate(p["layout_json"], p["plate_pdf"])
    out = export_plate_rasters(p["plate_pdf"], dpis=(72,), fmt="png")
    assert isinstance(out, pd.DataFrame)
    assert {"dpi", "px_w", "px_h", "path", "mode"} <= set(out.columns)
    assert os.path.exists(out.loc[0, "path"])

def test_assert_plate_complete_names_missing_outputs(tmp_path):
    from kernel import assert_plate_complete
    p = plate_paths("t", ["a"], root=str(tmp_path))
    make_panel(p["panels"]["a"]["pdf"])
    with pytest.raises(FileNotFoundError) as exc:
        assert_plate_complete(p)
    msg = str(exc.value)
    assert "plate_t_legend.md" in msg and "plate_t_flags.csv" in msg


def test_assert_plate_complete_passes_when_written(tmp_path):
    from kernel import assert_plate_complete
    p = plate_paths("t", ["a"], root=str(tmp_path))
    for path in p["save_files"]:
        open(path, "w").write("x")
    assert assert_plate_complete(p) == p["save_files"]
