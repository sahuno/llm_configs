#!/usr/bin/env python3
"""
build_jc_pptx.py — Convert Stage 5 slide markdown into a PPTX with embedded figures.

Author: Samuel Ahuno (ekwame001@gmail.com)
Date: 2026-04-29

Usage:
    python build_jc_pptx.py <paper_dir>
    python build_jc_pptx.py <paper_dir> --output /custom/path.pptx
    python build_jc_pptx.py <paper_dir> --images /custom/images/dir

Conventions assumed:
    <paper_dir>/05_slides_draft.md   — Stage 5 slide content (required)
    <paper_dir>/_meta.json           — paper metadata (read for paper_id)
    <paper_dir>/images/              — extracted figure panels (PNG)
                                       — falls back to <paper_dir>/<paper_id>/images/

Output:
    <paper_dir>/<paper_id>.pptx (default; override with --output)

Layout (16:9 widescreen, 13.33"×7.5"):
    Title:          0.5", 0.3" → 12.33"×1.0"
    Text-only body: 0.5", 1.4" → 12.33"×5.6"
    Image-slide bullets: 0.5", 1.4" → 6.2"×5.6"
    Image:          6.9", 1.4" → 5.94"×5.6" (preserves aspect ratio)
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from PIL import Image
except ImportError as e:
    sys.exit(
        f"Missing dependency: {e}\n"
        "Install with:\n"
        "  pip install python-pptx Pillow"
    )


# ---------- markdown parsing ---------------------------------------------------

SLIDE_PATTERN = re.compile(
    r"^## Slide (\d+)\s*[\u2014\-]\s*(.+?)\n(.*?)(?=^## Slide |\Z)",
    re.MULTILINE | re.DOTALL,
)

STOP_MARKERS = (
    "## Pre-talk checklist",
    "## Conversion to PowerPoint",
    "## Source map",
)

IMAGE_KEYWORDS = (
    "figure", "fig ", "fig.", "panel", "cartoon", "schematic",
    "diagram", "map", "cryo-em", "cryo-EM", "side-by-side", "split",
    "overlay", "structure",
)


def parse_field(block: str, label: str) -> str:
    pat = rf"\*\*{label}\*\*:\s*(.*?)(?=\n\*\*[A-Za-z][A-Za-z ]+\*\*:|\n---|\Z)"
    m = re.search(pat, block, re.DOTALL)
    return m.group(1).strip() if m else ""


def parse_bullets(text: str) -> list[str]:
    return [
        line.strip()[1:].strip()
        for line in text.splitlines()
        if line.strip().startswith("-")
    ]


def parse_slides(md_path: Path) -> list[dict]:
    text = md_path.read_text()
    for marker in STOP_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    slides = []
    for m in SLIDE_PATTERN.finditer(text):
        body = m.group(3)
        notes = parse_field(body, "Speaker notes")
        if notes.startswith('"') and notes.endswith('"'):
            notes = notes[1:-1]
        slides.append({
            "n": int(m.group(1)),
            "title": m.group(2).strip(),
            "bullets": parse_bullets(parse_field(body, "Bullets")),
            "notes": notes,
            "visual": parse_field(body, "Visual"),
        })
    return slides


def needs_image(visual_text: str) -> bool:
    """True if the slide's Visual: field implies a figure should be embedded."""
    if not visual_text:
        return False
    low = visual_text.lower()
    if "text-only" in low:
        return False
    return any(kw in low for kw in IMAGE_KEYWORDS)


# ---------- pptx building ------------------------------------------------------

def fit_image_box(img_path: Path, max_w_in: float, max_h_in: float
                  ) -> tuple[float, float]:
    """Return (width, height) in inches that fits img into (max_w, max_h)
    while preserving aspect ratio."""
    with Image.open(img_path) as img:
        iw, ih = img.size
    aspect = iw / ih
    if max_w_in / max_h_in > aspect:
        h = max_h_in
        w = h * aspect
    else:
        w = max_w_in
        h = w / aspect
    return w, h


def set_font(run, name: str = "Arial", size: int | None = None,
             bold: bool | None = None) -> None:
    run.font.name = name
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def build_pptx(slides: list[dict], images_dir: Path, out_path: Path) -> None:
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]  # blank — gives full control of shapes

    # Available images sorted by filename (PyMuPDF outputs are page-sorted)
    image_files = sorted(images_dir.glob("*.png")) if images_dir.exists() else []
    img_iter = iter(image_files)
    images_used = 0
    images_total = len(image_files)

    # Layout constants (inches)
    TITLE_X, TITLE_Y, TITLE_W, TITLE_H = 0.5, 0.3, 12.33, 1.0
    FULL_BODY_X, FULL_BODY_Y, FULL_BODY_W, FULL_BODY_H = 0.5, 1.4, 12.33, 5.6
    HALF_BODY_X, HALF_BODY_Y, HALF_BODY_W, HALF_BODY_H = 0.5, 1.4, 6.2, 5.6
    IMG_X, IMG_Y, IMG_MAX_W, IMG_MAX_H = 6.9, 1.4, 5.94, 5.6

    for s in slides:
        slide = prs.slides.add_slide(blank_layout)

        is_title = (s["n"] == 1)
        is_image = (not is_title) and needs_image(s["visual"])

        # ---- Title shape ----
        title_box = slide.shapes.add_textbox(
            Inches(TITLE_X), Inches(TITLE_Y),
            Inches(TITLE_W), Inches(TITLE_H),
        )
        title_tf = title_box.text_frame
        title_tf.word_wrap = True
        if is_title and s["bullets"]:
            paper_title = s["bullets"][0]
        else:
            paper_title = s["title"]
        title_tf.text = paper_title
        for run in title_tf.paragraphs[0].runs:
            set_font(run, "Arial", 32 if is_title else 28, bold=True)

        # ---- Body / image ----
        if is_title:
            # Subtitle: remaining bullets, centered visual region
            subtitle_lines = s["bullets"][1:] if len(s["bullets"]) > 1 else []
            if subtitle_lines:
                sub_box = slide.shapes.add_textbox(
                    Inches(FULL_BODY_X), Inches(FULL_BODY_Y + 1.5),
                    Inches(FULL_BODY_W), Inches(3.5),
                )
                sub_tf = sub_box.text_frame
                sub_tf.word_wrap = True
                for i, line in enumerate(subtitle_lines):
                    para = sub_tf.paragraphs[0] if i == 0 else sub_tf.add_paragraph()
                    para.text = line
                    for run in para.runs:
                        set_font(run, "Arial", 18)
        else:
            # Bullets — full width if text-only, half width if image slide
            if is_image:
                body_x, body_w = HALF_BODY_X, HALF_BODY_W
            else:
                body_x, body_w = FULL_BODY_X, FULL_BODY_W
            body_box = slide.shapes.add_textbox(
                Inches(body_x), Inches(FULL_BODY_Y),
                Inches(body_w), Inches(FULL_BODY_H),
            )
            body_tf = body_box.text_frame
            body_tf.word_wrap = True
            for i, b in enumerate(s["bullets"]):
                para = body_tf.paragraphs[0] if i == 0 else body_tf.add_paragraph()
                para.text = "• " + b
                para.level = 0
                for run in para.runs:
                    set_font(run, "Arial", 18)

            # Embed an image on image slides
            if is_image:
                try:
                    img_path = next(img_iter)
                    w, h = fit_image_box(img_path, IMG_MAX_W, IMG_MAX_H)
                    # Center within the right-half box
                    cx = IMG_X + (IMG_MAX_W - w) / 2
                    cy = IMG_Y + (IMG_MAX_H - h) / 2
                    slide.shapes.add_picture(
                        str(img_path),
                        Inches(cx), Inches(cy),
                        width=Inches(w), height=Inches(h),
                    )
                    images_used += 1
                except StopIteration:
                    # Out of images; flag in notes
                    s["notes"] = "[NEEDS IMAGE — out of extracted figures]\n\n" + s["notes"]

        # ---- Speaker notes ----
        notes_parts = []
        if s["visual"]:
            notes_parts.append(f"[VISUAL] {s['visual']}")
        if s["notes"]:
            notes_parts.append(s["notes"])
        slide.notes_slide.notes_text_frame.text = "\n\n".join(notes_parts)

    prs.save(str(out_path))
    print(f"Wrote: {out_path}")
    print(f"Slides: {len(slides)}")
    print(f"Images embedded: {images_used} / {images_total} available")


# ---------- CLI ---------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build PPTX from Stage 5 slide markdown with embedded figures.")
    ap.add_argument("paper_dir", help="Path to journal-club paper directory")
    ap.add_argument("--output", help="Output .pptx path (default: <paper_dir>/<paper_id>.pptx)")
    ap.add_argument("--images", help="Override images directory")
    ap.add_argument("--md", help="Override slide markdown path")
    args = ap.parse_args()

    paper_dir = Path(args.paper_dir).expanduser().resolve()
    if not paper_dir.is_dir():
        sys.exit(f"Not a directory: {paper_dir}")

    md_path = Path(args.md) if args.md else paper_dir / "05_slides_draft.md"
    if not md_path.exists():
        sys.exit(f"Slide draft not found: {md_path}")

    # paper_id
    meta_path = paper_dir / "_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        paper_id = meta.get("paper_id", paper_dir.name)
    else:
        paper_id = paper_dir.name

    # images dir: paper_dir/images, then paper_dir/<paper_id>/images
    if args.images:
        images_dir = Path(args.images).expanduser().resolve()
    else:
        candidates = [paper_dir / "images", paper_dir / paper_id / "images"]
        images_dir = next((p for p in candidates if p.exists()), candidates[0])

    out_path = Path(args.output) if args.output else paper_dir / f"{paper_id}.pptx"

    print(f"Source markdown: {md_path}")
    print(f"Images dir:      {images_dir}{' (missing)' if not images_dir.exists() else ''}")
    print(f"Output:          {out_path}")
    print()

    slides = parse_slides(md_path)
    print(f"Parsed {len(slides)} slides.")
    build_pptx(slides, images_dir, out_path)


if __name__ == "__main__":
    main()
