---
name: print-plate-assembly
description: Assemble existing figures into one printable plate on a US Letter or A4 sheet, with a manifest recording what each panel is, where it came from, and its legend. Use when rendered figures must be laid out on paper for a manuscript, thesis, poster or print submission; when working titles and in-figure commentary must come off analysis figures; or when a paper needs a ready-to-paste figure legend or caption for panels it already has. Never plots data or edits a source figure; to BUILD a figure from data use figure-composer. The legend is its own deliverable: caption with (A)-(D) blocks, opening and closing sentences, a supplementary-methods section for caveats too long to caption, abbreviations, and a word cap that warns without truncating. Emits vector PDF plus TIFF, optionally CMYK. Ships plate_paths, panel_geometry, propose_layout, compile_plate, predict_print_size, write_plate_manifest, write_plate_legend, write_plate_flags, assert_plate_complete, bundle_plate_sources, export_plate_rasters.
---

# Print plate assembly

A *plate* is a physical sheet — US Letter or A4 — carrying several finished
panels, lettered, with a legend and a record of where each panel came from. It
is the last thing made before a figure leaves the project, and it is a different
job from making the figures.

Analysis figures are argumentative by design: they carry claim-titles, inline
commentary, and a reading order that served the question being asked at the
time. That is correct for analysis and wrong for a plate, where the argument
belongs in the legend and the panel must stand on its own. So this pass strips
the commentary, re-renders each panel standalone, and composes onto paper.

## Where this sits

| you want | use |
|---|---|
| one plot, correct and legible | `figure-style` (+ `lab-figure-format`) |
| a multi-panel figure built from data or a claim | `figure-composer` / `lab-figure-composer` |
| existing renders arranged on a paper sheet, lettered, with a manifest | **this skill** |

The distinction is generative versus assembling. The composers create panels from
data. This skill treats every figure as an immutable input and produces new
files. It may *read* a data table to check a number a panel already declares —
that is the value-check path — but never to **decide** what a panel shows. If
you find yourself opening a table to choose the content of a panel, you are in
the wrong skill.

## Three hard rules

**1. A source figure is read-only.** Never save a new version of a source
artifact, never overwrite its file, never "clean it up in place". Every output —
each standalone panel, the plate, the manifest — is a new artifact. The analysis
figures must remain exactly as the analysis left them, because they are the
record of what was actually reviewed.

**2. Never crop a raster to make a panel.** Cropping inherits the source's
resolution, its stripped-off titles' whitespace, and its baked-in panel letter,
and it cannot produce vector output. Panels are re-rendered from code.

**3. A defect you notice is flagged, not fixed.** Re-rendering a panel puts you
closer to the underlying numbers than anyone has been since the figure was made,
so this pass finds real errors — a mislabelled axis, a value that disagrees with
the source table, a colorbar whose range clips data. Record it in the manifest's
`flags` column and raise it in your response. Do not correct it here: a silent
fix at plate time produces a figure that disagrees with the analysis it came
from, and nobody knows which is right. The fix belongs upstream, in the analysis,
where it can be reviewed.

## Step 1 — inventory the sources

List the figures going onto the plate with their `version_id`s. Read each one
(`host.view_image` or `read_file`) and write down, per source figure, how many
panels it contains and what each shows. A two-panel figure contributes two
entries, not one.

## Step 2 — regenerate each panel standalone

**Lineage first.** `host.lineage[version_id]["code"]` is the producing code, and
`["inputs"]` resolves the data files it read. A multi-panel producer is usually a
`GridSpec` with one block per panel, so the edit is mechanical: keep the block
for one panel, replace the grid with a single-axes figure, and emit vector.

Recover the code **once per source figure and cache it** — a cold
`host.lineage[vid]` read can take upwards of a minute, and doing it per panel
multiplies that for no gain.

**Data-replot as fallback.** When the code is unrecoverable or too entangled to
split, re-plot the panel from the same input tables, matching the source's
encoding. State in the manifest that this route was used: a replot is a
reconstruction, and a reader comparing plate to analysis figure deserves to know.

**Flag when neither works.** If the panel cannot be regenerated, do not crop it
out of the raster to keep things moving. Record it as `regen_route=flagged` and
tell the user which panel is stuck and why.

**Apply the house style, after the recovered code, before the save.** This is
the point where the house typography is imposed, and it is the only one — the
composer that made the source figure does not guarantee it, so a panel arrives
in whatever face and sizes its producing script chose. Re-rendering here is
what makes the plate the house style's enforcement gate rather than its last
checkpoint.

```python
exec(recovered_panel_code)   # the producer sets its own rcParams -- let it
apply_figure_style()         # figure-style: ticks, spines, legend, layout
house_style()                # lab-figure-format: Arial chain, mathtext, fonttype 42
```

**Order matters twice.** `house_style()` goes after `apply_figure_style()`
because `apply_figure_style(font=...)` overwrites `font.sans-serif` and the
mathtext roles, and the house face has to win. Both go *after* the recovered
code, because that code's rcParams outlive it — the gotcha already documented
below for `savefig.bbox` applies to `font.family` in exactly the same way, and
styling before the exec means styling nothing.

Check the return value of `house_style()`. `installed=False` means matplotlib
silently substituted another face, so the panel will not match its neighbours
on the sheet — that is a flag for Step 6, not something to paper over.

**Point sizes come from the house ladder, never from per-figure taste.** A
plate is multi-panel by definition, so it is the ladder in `lab-figure-format`
that applies, not the 8 pt single-panel default its `.mplstyle` sets:

| role | pt |
|---|---|
| panel title | 9 |
| axis label, body text | 8 |
| tick label, legend, annotation | 7 |
| dense in-plot label (gene names, cell values) | 6 |

Nothing below 6 pt in the source, nothing that *prints* below ~5 pt — which is
what `predict_print_size()` checks in Step 5. Authoring a panel at 7 in for a
3.4 in slot halves every one of these, so author at the placed width where you
can.

**Bare `house_style()` does not apply that whole ladder.** Its default
`SIZE_LADDER = (8, 7, 6)` is `(base, annotation, tick)`, which lands axis label
and *title* at 8 and tick labels at 6 — so a bare call gives you neither the
9 pt title nor the 7 pt tick the table above asks for. Pass the sizes you mean
and set the title explicitly:

```python
house_style(sizes=(8, 7, 7))          # label 8, legend/annotation 7, tick 7
ax.set_title(..., fontsize=9)         # the ladder's title row
```

Dense in-plot text at 6 pt is a per-artist choice, not an rcParam; set it where
you draw it.

**Emit PDF and SVG, plus a PNG proof.** The plate is vector, so the panels must
be. The PNG exists only so you can look at the panel and at the composed plate;
it is not what gets placed.

## Step 3 — what comes off, and what must not

**Strip, and log verbatim to the manifest:**

- the claim-title — the line asserting what the panel shows
  (*"proliferative programs suppressed"*, *"only MHC-I loading is
  combination-specific"*)
- the descriptive title too — the panel is identified by its legend entry on a
  plate, not by a title
- the baked-in panel letter — letters are stamped at compile time from the slot
  the panel lands in, so a letter drawn into the source render will collide with
  the real one the moment panels are rearranged
- inline interpretive annotations and arrows pointing at conclusions

**Keep — this is data, not commentary:**

cell values and their significance markers, row and column labels, tick labels
and axis titles, colorbars with their scale labels, group dividers and their
labels, error bars, sample-size annotations, units.

The test is whether removing it changes what a reader can measure off the panel.
If yes it stays. A stripped string is not discarded — it goes into the manifest
and is the raw material for that panel's legend entry.

## Step 4 — propose a layout, then compile only from the approved spec

`panel_geometry(paths)` measures each panel — pass it the `plate_paths` dict
directly, which is the only thing you hold at this point, or a list of PDF
paths. `propose_layout(geom, sheet=...)`
returns a spec — sheet, orientation, margins, gutters, grid, and one slot per
panel with `row`, `col`, spans and reading-order letter — and writes it to JSON.

Show the proposal, take the edits, then compile **from the spec file only**.
Compilation never re-decides the arrangement. That is what makes a plate
reproducible: the same spec and the same panels give the same sheet, and a
one-panel nudge is a two-line diff rather than a re-derivation.

**Panels that need more than one cell.** Pass `spans={"a": (1, 2)}` — a
(rowspan, colspan) per panel letter — for a wide panel above two square ones.
Placement is row-major into the first free block that fits, and the scale is
computed against the spanned box rather than a single cell.

## Step 5 — compile in vector

`compile_plate(spec, out_pdf)` places each panel PDF into its slot, scaled to
fit while preserving aspect ratio, and stamps the panel letters as vector text
at slot position. Nothing is rasterised.

Then look at it. `predict_print_size(spec, authored_min_pt=...)` reports the
placement scale per panel and the smallest text size as printed — a panel
authored at 7 in and placed at 3.4 in has every point size halved. Anything
printing below ~5 pt needs the panel re-rendered at its placed width, not
scaled down; the print-size ladder in `lab-figure-format` is the reference.

## Step 6 — the manifest

One row per placed panel. This is the deliverable that makes the plate
auditable, so it ships alongside the PDF, always.

| column | content |
|---|---|
| `letter` | the panel letter as stamped, from slot position |
| `what` | one line: what this panel shows |
| `source_artifact` / `source_version_id` | the figure it came from |
| `source_panel_index` | which panel of that figure |
| `producer` | script or notebook that made the original |
| `regen_route` | `lineage` / `replot` / `authored` / `flagged` — `authored` means the panel was made for this plate from data tables, so `source_artifact` names those tables and the stripped-title fields are legitimately empty |
| `stripped_title` | the claim- and descriptive titles removed, verbatim |
| `stripped_annotations` | other removed commentary, verbatim |
| `legend` | the panel's legend sentence |
| `panel_pdf` / `panel_svg` | paths to the standalone renders |
| `panel_sha256` | content hash of the placed PDF |
| `slot` | `row,col,rowspan,colspan` |
| `placed_scale` | placed width ÷ authored width |
| `flags` | one-line summary of defects noticed and NOT fixed; the ledger with status and evidence is the sibling flags CSV |

`write_plate_manifest(rows, out)` emits it as TSV with these columns in this
order, flattening embedded newlines to `"; "`. That flattening is not cosmetic:
a manifest with hard newlines inside quoted cells is one row to pandas and
several records to `cut`, `awk`, a naive spreadsheet import and `git diff`. One
real four-panel manifest spanned eleven physical lines.

## The flag ledger

Rule 3 says flag, don't fix. A flag can also turn out to be **wrong** — a defect
read off a low-resolution proof may not survive re-reading at print resolution,
and a retraction written as prose inside a manifest cell is unfindable.

`write_plate_flags(flags, out)` writes `plate_<slug>_flags.csv` with
`letter, flag_id, status, claim, evidence, resolution`, where status is `open`,
`retracted` or `fixed_upstream`; an unrecognised status raises rather than
silently entering the record. Keep the manifest's `flags` column as the one-line
summary and put the life cycle here.

## The legend

The manifest already carries a per-panel `legend`. Nothing assembled it, so on a
real four-panel build the legend was hand-written separately and **only one of
four manifest sentences survived verbatim** — two artifacts describing the same
panels in different words, with no way to tell which was current.

`write_plate_legend(rows, out, title=..., word_cap=...)` takes **the same rows
you pass to the manifest**, so the legend is a serialisation of the manifest
rather than a parallel document. It emits the bold title sentence, then
`**(A)** …` blocks in letter order using each panel's `legend` verbatim, plus
optional `methods` (material too long for a caption — shrinkage mismatches,
gene-universe differences), `scope_note` and `abbreviations` sections. It
returns `{path, caption_words, over_cap, panels}`.

**A caption has sentences that belong to no panel**, and they are not
interchangeable with front matter. Use the right slot:

| slot | where it lands | counted in `caption_words`? |
|---|---|---|
| `opening` | joins the title's paragraph, **inside** the caption | **yes** |
| `closing` | own paragraph after the last panel, **inside** the caption | **yes** |
| `preamble` | **outside** the caption, behind a rule | no |

`opening` is the design sentence — *"B16 cells were treated with vehicle, CKi,
QSTAT or the combination and profiled by bulk RNA-seq"* — which reads as one
paragraph with the bold title, exactly as journals set it. `closing` is the
statistics sentence — *"n = 3 per condition except CKi (n = 2); all statistics
derive from one shared fit"*. `preamble` is for whoever opens this **file** —
which manifest the numbers were read back from — and a journal never sees it,
which is why it is not counted.

Putting the design sentence in `preamble` was the first thing tried on a real
build. It puts caption text outside the caption **and** outside the number the
cap is checked against, so a 300-word cap silently passes on a caption that is
over it.

Two rules it enforces. **An empty `legend` cell raises**, naming the letter — a
silently thin legend is worse than a refusal. And **`word_cap` warns, never
truncates**: it reports the count against the cap and leaves the text intact,
because which sentence to cut is the author's decision.

## Step 7 — the plate is the deliverable, so finish it here

Assume there is no downstream hand-finishing step. Nothing gets nudged in a
vector editor afterwards, which means anything wrong at compile time ships
wrong. Three things follow.

**Export the raster ladder journals actually ask for.**
`export_plate_rasters(paths["plate_pdf"], dpis=(300, 600, 900), fmt="tiff")`
returns a DataFrame of what was written — one row per DPI with pixel dimensions
and path, not a list of paths —
renders the vector plate at each DPI and writes LZW-compressed TIFFs with the
DPI in both the filename and the file metadata. A US Letter sheet comes out at
2550 x 3301 px at 300 ppi and 7650 x 9900 px at 900 ppi. Keep the PDF as the
primary — it is resolution-independent — and treat the rasters as what you
upload when a submission system demands a bitmap at a stated resolution.

**CMYK when a journal requires it, with a real profile.** Pass `cmyk=True` and
the conversion runs through LittleCMS with an ICC profile and embeds it in the
TIFF, rather than the naive channel arithmetic that makes blacks muddy.
`find_cmyk_profile()` looks for a system profile; if the journal names a press
profile (US Web Coated SWOP, Coated FOGRA39), they publish the `.icc` and you
pass `icc_path=`. The CMYK path has been exercised end to end with a generic
system profile (600 ppi TIFF, mode CMYK, 76 KB profile embedded and readable on
reopen); conversion against a journal-supplied press profile has not been tested
here. A generic system CMYK profile is a reasonable default and is
not the same thing as the named profile — say which one was used in the
manifest.

**Check the fonts are embedded, not substituted.** A plate with a referenced
rather than embedded face renders differently on the publisher's machine.
`lab-figure-format` ships `verify_embedded_fonts()`; run it on the plate PDF
before you call the plate done.

**Two orientations means two plates, not one file with variants.** A landscape
and a portrait arrangement of the same panels are different layout specs, so
give them different slugs (`meki_hdaci_immune`, `meki_hdaci_immune_portrait`)
and let each carry its own manifest. Trying to express both in one spec makes
the reproducibility guarantee ambiguous.

## Where the outputs go

A plate produces a lot of files, and they arrive in batches. Call
`plate_paths(slug, panel_letters)` once at the start and write everything to the
paths it returns; do not compose paths by hand.

```
plates/meki_hdaci_immune/
├── plate_meki_hdaci_immune.pdf, _proof.png, _layout.json, _manifest.tsv
├── plate_meki_hdaci_immune_sources.tar.gz
└── panels/plate_meki_hdaci_immune_panel_a.{pdf,svg,png}
    panels/plate_meki_hdaci_immune_regen_panel_a.py
```

`root` defaults to `plates` and is a parameter — a project that already has
`manuscript/fig3/` should not have to fight this skill, and getting the root
wrong costs nothing durable.

**Why the slug is repeated inside the directory.** The workspace is scratch: it
is swept, and nothing in it is the deliverable. The artifact store is what
lasts, and it **discards the directory** — saving `panels/panel_a.pdf` stores it
as `panel_a.pdf`. Artifact filenames are also not unique, so a bare
`panel_a.pdf` becomes permanently ambiguous the moment a second plate exists,
and a bare `manifest.tsv` says nothing about which plate it describes. Renaming
after the fact only works while you still remember which is which.

So the two problems are asymmetric: an untidy workspace is cosmetic and
recoverable, a badly named artifact is forever. Putting the slug in the filename
means the name you save under *is* the name on disk — there is no staging step
where the two can diverge, and nothing to remember at save time.

**`save_files` is the list to hand to `save_artifacts`.** It contains the plate,
the proof, the layout spec, the manifest, each panel PDF, and the sources
bundle. Panel PDFs are individual because a panel is a reusable unit that may
end up on another plate, a poster or a slide. The SVGs and regeneration scripts
go into `plate_<slug>_sources.tar.gz` via `bundle_plate_sources(paths)` — the SVG
is there for a downstream consumer that wants an editable vector, the script is
there as the panel's producer, and one artifact per panel per format
would turn a six-panel plate into twenty entries in the file list for no gain.

**Save in two passes, manifest last.** The manifest's `panel_version_id` column
can only be filled once the panels have been saved and returned their ids. Save
the panels and the plate first, collect the ids, write the manifest, save it.
Workspace paths do not survive the session; the version ids are the only
reference that still resolves next month.

## Requirements

`pypdf` (composition), `pypdfium2` (proof rendering and rasterisation),
`pillow` with libtiff (TIFF and ICC colour), plus matplotlib and pandas. In a
fresh environment: `pip install pypdf pypdfium2 pillow`. No external binary is
needed or used — Ghostscript, ImageMagick and Inkscape are absent from this
sandbox and nothing here calls them.

## Runtime gotchas

These cost a wrong plate the first time and are cheap to avoid.

- **A producing script's rcParams outlive it.** Analysis figure code routinely sets
  `savefig.bbox: "tight"` globally. Exec that code to regenerate a panel and the
  setting is still live when you write the panel-letter overlay, which then gets
  cropped to the glyphs and merges into the wrong corner of the sheet. Pin the
  write: `with matplotlib.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0}):`.
  `compile_plate` already does this; do the same for anything else you draw at
  sheet scale.
- **`bbox_inches="tight"` means figsize is not the authored size.** It is the right
  setting for a panel — no dead margin to place — but it makes the saved size
  differ from what the code asked for. This is why `panel_geometry` reads the PDF
  mediabox instead of trusting the producer, and why placement scale is computed
  from measurement.
- **Lineage reads are slow and worth caching.** A cold `host.lineage[vid]` on a
  figure with a dozen inputs can take a minute. One read per source figure, held
  in a variable; write the split panel scripts to disk so a re-render is free.
- **Keep the regenerated panel scripts.** They are the producer for the new panel
  artifacts — the plate has the same provenance obligation as any other output.

## Anti-patterns

- Editing a source figure "just to remove the title" — that is rule 1; regenerate.
- Cropping panels out of a composite PNG because lineage was slow.
- Baking panel letters into the standalone panel renders.
- Fixing an error found during the pass instead of flagging it.
- Stripping axis labels or units along with the titles, which makes the panel
  unmeasurable and the plate worthless.
- Re-deciding the layout at compile time so the spec and the output disagree.
