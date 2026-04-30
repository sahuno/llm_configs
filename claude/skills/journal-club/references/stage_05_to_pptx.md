# Stage 5 → PPTX: Convert slide markdown to PowerPoint with embedded figures

**Goal**: Turn `05_slides_draft.md` into a working `.pptx` deck where each
figure-walk slide already has its image dropped in place — not just a
[VISUAL] note in the speaker notes telling the user to do it manually.

This is what makes the deck useful as a *real* working draft: the user opens
PowerPoint and is editing a deck-with-images, not assembling one from scratch.

## Inputs

- `<paper_dir>/05_slides_draft.md` — slide content
- `<paper_dir>/images/` — extracted figure panels (PNG, sorted by page)
- `<paper_dir>/_meta.json` — paper metadata (title, audience, etc.)

## Outputs

- `<paper_dir>/<paper_id>.pptx` — final deck

## Procedure

1. **Parse `05_slides_draft.md`** into structured slide records:
   - `n` — slide number
   - `title` — slide title (from `## Slide N — <title>`)
   - `bullets` — list of bullet strings (from `**Bullets**:`)
   - `notes` — speaker notes paragraph (from `**Speaker notes**:`)
   - `visual` — visual instruction (from `**Visual**:`)

2. **Decide which slides need an image** by inspecting the `visual` field:
   - **Image slide**: any of these keywords matches: *figure*, *fig*, *panel*,
     *cartoon*, *schematic*, *diagram*, *map*, *cryo-em*, *cryo-EM*,
     *side-by-side*, *split*
   - **Text-only slide**: keyword `text-only` is present, OR none of the
     above matched

3. **Sort available images** in `<paper_dir>/images/` by filename (which is
   already page-sorted, e.g., `page004_img01.png`).

4. **Walk slides in order** and assign images sequentially:
   - For each image slide, pop the next image from the sorted list
   - For each text-only slide, skip
   - If images run out before image slides do, leave remaining image slides
     without an image and add `[NEEDS IMAGE]` to their notes

5. **Layout** (16:9 widescreen, 13.33×7.5″):
   - **Title slide (Slide 1)**: centered title + subtitle from bullets[1:]
   - **Text-only slides**: title at top, full-width bullets
   - **Image slides**: title at top; bullets in left half; image in right half
     (5.5″ wide × 5.0″ tall, vertically centered, left-aligned at x=7.0″)
   - **Speaker notes**: prepend `[VISUAL] <visual_text>` then a blank line, then
     the speaker text. Always populate the notes pane.

6. **Aspect-ratio handling for embedded images**: scale to fit the right-half
   bounding box (5.5″ × 5.0″) while preserving aspect ratio. Don't stretch.

## Layout constants (16:9 deck)

```
Slide:                13.33" × 7.5"
Margin:               0.5"
Title:                top of slide, full width minus margins
                      0.5", 0.3" → 12.33" × 1.0"

Text-only body:       below title, full-width
                      0.5", 1.4" → 12.33" × 5.6"

Image-slide bullets:  left half, below title
                      0.5", 1.4" → 6.2" × 5.6"

Image-slide image:    right half, below title (max bounding box)
                      6.9", 1.4" → 5.94" × 5.6"  (preserve aspect ratio)
```

## Helper script

A turnkey implementation lives in this skill at
`scripts/build_jc_pptx.py` (auto-discovers from `<paper_dir>` by convention).
Invocation:

```bash
python ~/.claude/skills/journal-club/scripts/build_jc_pptx.py <paper_dir>
# Default output: <paper_dir>/<paper_id>.pptx
```

Or, if writing the conversion inline (when running in a Python environment
that has `python-pptx` installed but no access to the packaged script):
re-implement the procedure above using `python-pptx`. See
`scripts/build_jc_pptx.py` source for the canonical implementation.

## QA after building

1. Open the .pptx — confirm 35 slides exist
2. Spot-check 3–5 figure-walk slides — image should be on the right half
3. Verify presenter notes contain the `[VISUAL]` tag plus speaker text
4. Verify title slide has the paper title (not "Title slide")
5. If LibreOffice is available, generate a thumbnail grid for visual QA:
   ```bash
   soffice --headless --convert-to pdf <paper_dir>/<paper_id>.pptx
   pdftoppm -jpeg -r 100 <paper_dir>/<paper_id>.pdf slide
   ```

## Anti-patterns

- **Don't stretch images** to fill the right-half box if their aspect
  doesn't match — preserve aspect ratio and center within the box
- **Don't embed every available image regardless of slide content** — the
  text-only / methods / critique slides should stay text-only
- **Don't fabricate captions** under embedded images — image fidelity to
  the source paper matters; let the bullets and speaker notes do the
  describing
- **Don't crop multi-panel figures automatically** — extracted images come
  from PyMuPDF page-level extraction; if a slide needs a specific panel,
  flag this for the user (write `[CROP MULTI-PANEL]` in notes) rather than
  guessing
