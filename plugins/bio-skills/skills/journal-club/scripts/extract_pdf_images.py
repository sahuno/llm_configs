#!/usr/bin/env python3
"""
extract_pdf_images.py — Extract figure images from a PDF using PyMuPDF.

Author: Samuel Ahuno (ekwame001@gmail.com)
Date: 2026-04-30

Replaces the previously-external `extract_pdf_images.py`. Self-contained except
for PyMuPDF (`pymupdf`).

Two modes
---------
1. **Embedded-image mode** (default): extract the raster images embedded in the
   PDF stream. Fast, lossless, but for vector figures may yield only fragments
   (e.g., individual sub-images of a multi-panel figure).
2. **Page-render mode** (`--render-pages`): render each page to a PNG at the
   specified DPI. Robust for vector PDFs and multi-panel composites; produces
   one image per page rather than per embedded resource.

For most journal-club use, **page-render mode is the right default for the
caption-aware figure mapping** in `build_jc_pptx.py` — it gives one image per
page that the figure-mapping logic can pair with caption pages.

Note: For PMC-indexed papers, prefer `pmc_fetch.py --supplement` — it pulls
pre-rasterized figure JPGs/GIFs from EuropePMC's supplementaryFiles ZIP without
needing the PDF or PyMuPDF at all. This script is for closed-access journals
where the user provides a local PDF.

CLI usage
---------
    # Page-render mode at 200 DPI (recommended for journal-club)
    python extract_pdf_images.py paper.pdf --out-dir images/ --render-pages --dpi 200

    # Embedded-image mode
    python extract_pdf_images.py paper.pdf --out-dir images/

    # Restrict to a page range (1-indexed)
    python extract_pdf_images.py paper.pdf --out-dir images/ --render-pages --pages 3-15

Output filenames
----------------
- Page-render mode: `page<NNN>.png` (3-digit zero-padded, 1-indexed)
- Embedded-image mode: `page<NNN>_img<NN>.<ext>` (matches build_jc_pptx.py's
  `PAGE_FROM_FILENAME_RE` for caption-aware figure pairing)
"""

import argparse
import sys
from pathlib import Path


def _import_pymupdf():
    """Lazy import with a friendly error message if PyMuPDF is missing."""
    try:
        import pymupdf  # type: ignore
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
            return pymupdf
        except ImportError:
            sys.exit(
                "Missing dependency: pymupdf\n"
                "Install with: pip install pymupdf\n"
                "(For PMC-indexed papers, prefer pmc_fetch.py --supplement, which "
                "doesn't need PyMuPDF.)"
            )


def _parse_page_range(arg: str | None, total_pages: int) -> range:
    """Parse '3-15' / '5' / None into a Python range of 0-indexed pages."""
    if not arg:
        return range(total_pages)
    if "-" in arg:
        lo, hi = arg.split("-", 1)
        return range(int(lo) - 1, min(int(hi), total_pages))
    p = int(arg) - 1
    return range(p, p + 1)


def render_pages(
    pdf_path: str | Path,
    out_dir: str | Path,
    dpi: int = 200,
    pages: str | None = None,
) -> list[Path]:
    """Render each page of the PDF to a PNG at the given DPI.

    Returns the list of saved Path objects, in page order.
    """
    pymupdf = _import_pymupdf()
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    n_pages = len(doc)
    page_indices = _parse_page_range(pages, n_pages)
    zoom = dpi / 72.0  # PDF default DPI is 72
    matrix = pymupdf.Matrix(zoom, zoom)

    saved = []
    for i in page_indices:
        page = doc[i]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out_path = out_dir / f"page{i + 1:03d}.png"
        pix.save(str(out_path))
        saved.append(out_path)
    doc.close()
    return saved


def extract_embedded(
    pdf_path: str | Path,
    out_dir: str | Path,
    pages: str | None = None,
    min_size: int = 100,
) -> list[Path]:
    """Extract embedded raster images from each page of the PDF.

    Args
    ----
    min_size : int  Skip images smaller than this many pixels on the longest
        side (filters out icons, bullet-points, decorations).

    Returns the list of saved Path objects, in extraction order.
    """
    pymupdf = _import_pymupdf()
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    n_pages = len(doc)
    page_indices = _parse_page_range(pages, n_pages)

    saved = []
    for i in page_indices:
        page = doc[i]
        for img_idx, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            try:
                pix = pymupdf.Pixmap(doc, xref)
            except Exception:
                continue
            if max(pix.width, pix.height) < min_size:
                continue
            ext = "png"
            # CMYK pixmaps need conversion to RGB before saving as PNG
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            out_path = out_dir / f"page{i + 1:03d}_img{img_idx:02d}.{ext}"
            pix.save(str(out_path))
            saved.append(out_path)
    doc.close()
    return saved


# ---------- CLI ----------------------------------------------------------------


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf", help="Path to source PDF")
    ap.add_argument("--out-dir", required=True, help="Destination directory for images")
    ap.add_argument("--render-pages", action="store_true",
                    help="Render each page to PNG (recommended; pairs with build_jc_pptx caption-mapping)")
    ap.add_argument("--dpi", type=int, default=200,
                    help="DPI for --render-pages (default: 200)")
    ap.add_argument("--pages", help="Page range (1-indexed), e.g. '3-15' or '7'")
    ap.add_argument("--min-size", type=int, default=100,
                    help="In embedded mode, skip images smaller than this px on the longest side (default 100)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"PDF not found: {pdf_path}")

    if args.render_pages:
        saved = render_pages(pdf_path, args.out_dir, dpi=args.dpi, pages=args.pages)
        print(f"Rendered {len(saved)} pages at {args.dpi} DPI to {args.out_dir}")
    else:
        saved = extract_embedded(
            pdf_path, args.out_dir, pages=args.pages, min_size=args.min_size,
        )
        print(f"Extracted {len(saved)} embedded images to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
