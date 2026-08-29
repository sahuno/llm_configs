# Stage 1: Ingest

**Goal**: Get the paper into the project, parse it into structured form, capture
audience and time-budget metadata, and produce a one-page ingestion report
the user can scan in 60 seconds.

## Inputs

- A paper identifier: PMCID (preferred), bioRxiv/medRxiv DOI, PMID, or path to a local PDF
- (Optional) audience profile and time budget — if not given, ask once

## One-time setup (for the rare not-yet-PMC-indexed preprint)

For PMC-indexed papers (the common case, including most bioRxiv preprints
within a few weeks of posting), the vendored `scripts/pmc_fetch.py` works
out of the box with stdlib only. **No setup needed.**

For the rare not-yet-PMC-indexed preprint where Cloudflare Turnstile blocks
direct bioRxiv fetches, install playwright + cloudscraper once per machine:

```bash
pip install playwright cloudscraper
python -m playwright install chromium
```

For closed-access papers where the user provides a local PDF, the vendored
`scripts/extract_pdf_images.py` requires PyMuPDF:

```bash
pip install pymupdf
```

`pdftotext` (poppler) is needed for text extraction from PDFs and is usually
already installed; on macOS via Homebrew: `brew install poppler`.

## Procedure

1. **Resolve the journal-club home directory** (where `<paper_id>/`
   subdirectories will live):
   - If the user passed `--dest /some/path`, use that.
   - Else if `JOURNAL_CLUB_HOME` env var is set, use it.
   - Else default to `~/journalClub/` (expand `~` to user home).
   - Create the home directory silently if missing.

2. **Identify paper_id and source**:
   - PMCID (`PMC<digits>`) → PMC source, `paper_id = PMC<digits>`
   - PMID (numeric) → try `pmid2pmcid` first; if PMC mapping exists,
     treat as PMC; else treat as a generic DOI lookup
   - bioRxiv/medRxiv DOI (`10.1101/...`, `10.64898/...`, or any DOI hosted
     on biorxiv.org / medrxiv.org) → preprint source, `paper_id = <server>_<slug>`
     where slug = DOI with `/` and `.` replaced by `_`
   - Generic DOI (journal articles) → ask user for the PDF or PMCID
   - Local PDF path → PDF source, `paper_id = <pdf_stem>`

3. **Create paper directory**: `<journal_club_home>/<paper_id>/`
   plus subdirectories `pdf/`, `xml/`, `images/` (created on demand).

3. **Fetch + parse** using the **vendored** `scripts/pmc_fetch.py` (stdlib only,
   ships with the skill — no dependency on the user's main project).

   **PMC source** (also covers bioRxiv preprints once PMC-indexed):
   ```python
   import sys
   sys.path.insert(0, '<skill_dir>/scripts')  # e.g. "${CLAUDE_PLUGIN_ROOT}/skills/journal-club/scripts"
   from pmc_fetch import fetch_paper

   paper = fetch_paper(
       pmcid='PMC12918801',           # OR: pmid='41727087', OR: doi='10.64898/2026.02.12.705658'
       out_dir=paper_dir,
       fetch_supplement=True,         # pulls EuropePMC supplementaryFiles ZIP, unpacks PDFs+images
   )
   # paper['xml_path'] → saved JATS XML
   # paper['figures']  → list of dicts: {label, headline, caption_full, graphic_href, url}
   # paper['data_availability'], paper['funding'], paper['supplements']
   # paper['supplement_zip_path'] → None if no supplement; else path
   # paper['unpacked'] → {'pdfs': [...], 'images': [...]} (None if no zip)
   ```

   `fetch_paper()` chains: `pmid_to_pmcid` (or `doi_to_pmcid`) → `download_pmc_xml`
   → `parse_pmc_xml` (verbatim caption extraction included) → `fetch_supplement_zip`
   → `unpack_supplement_zip`. Returns the parsed `paper` dict augmented with
   `xml_path` and supplement paths.

   **bioRxiv preprint NOT yet PMC-indexed** (rare; most appear in PMC within
   weeks):
   ```python
   from pmc_fetch import doi_to_pmcid, fetch_biorxiv_metadata

   pmcid = doi_to_pmcid('10.1101/2026.xx.xx.yyyyyy')
   if pmcid:
       paper = fetch_paper(pmcid=pmcid, out_dir=paper_dir)
   else:
       # Fall back to bioRxiv API for metadata + abstract (not Cloudflare-protected)
       meta = fetch_biorxiv_metadata(doi)
       # paper title, authors, abstract, license available
       # For full text, fall back to playwright/cloudscraper-based fetch_preprint()
       # (not vendored — install separately per the one-time setup section above).
   ```

   **Closed-access local PDF**: text via `pdftotext -layout` (poppler),
   figures via the vendored `scripts/extract_pdf_images.py` (PyMuPDF).
   Build a synthetic `paper` dict matching `parse_pmc_xml()` output shape so
   downstream stages remain source-agnostic.

   ```bash
   pdftotext -layout local_paper.pdf paper.txt
   python <skill_dir>/scripts/extract_pdf_images.py local_paper.pdf \
       --out-dir images/ --render-pages --dpi 200
   ```

4. **Build figure catalogue with full caption text**. Captions are
   load-bearing for downstream stages — Stage 5 speaker notes pull from
   them, Stage 2c per-figure micro-audit checks N/error-bar conventions
   stated in legend text, and Stage 6 Q&A prep depends on them. Extract
   captions verbatim, do not paraphrase.

   - **PMC / Preprint XML (EPMC / Playwright)**: parse `<fig>` blocks
     in the JATS XML. For each figure, capture four fields:
     - `label` — e.g., `"Fig. 1."`
     - `caption_full` — verbatim text of the entire `<caption>` element,
       all panels (A/B/C/...). Concatenate `itertext()` and strip whitespace.
     - `graphic_href` — value of `<graphic xlink:href>`; use this to
       construct the URL: `https://www.ncbi.nlm.nih.gov/pmc/articles/<PMCID>/bin/<href>`.
     - `headline` — derived: the first sentence of `caption_full` (split
       on `". "`); typical journal convention puts the headline finding there.

     Reference snippet (Python, stdlib only):
     ```python
     import xml.etree.ElementTree as ET
     XLINK = '{http://www.w3.org/1999/xlink}href'

     def text_of(el):
         return ' '.join(t.strip() for t in el.itertext()).strip()

     def figure_catalogue(xml_path, pmcid):
         root = ET.parse(xml_path).getroot()
         out = []
         for fig in root.iter('fig'):
             label_el = fig.find('label')
             cap_el = fig.find('caption')
             gfx_el = fig.find('graphic')
             caption = text_of(cap_el) if cap_el is not None else ''
             href = gfx_el.attrib.get(XLINK, '') if gfx_el is not None else ''
             out.append({
                 'label': label_el.text if label_el is not None else '',
                 'caption_full': caption,
                 'headline': caption.split('. ', 1)[0] + '.' if caption else '',
                 'graphic_href': href,
                 'url': f'https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{href}' if href and pmcid else '',
             })
         return out
     ```

     bioRxiv preprint figures aren't always linked via `<graphic>` in the
     XML — for those, fall back to PDF figure extraction (below) but
     still extract caption text from the XML when available; the JATS
     `<fig>` blocks usually retain captions even when image links don't
     resolve.

   - **PDF (preprint or local)**: figures from PyMuPDF page-level
     extraction do not carry captions automatically. Pair caption to
     figure heuristically — caption text is conventionally the paragraph
     immediately below or beside the figure on the same page. Best-effort
     options: `pdfplumber` for layout-aware text extraction, or
     `pdftotext -layout` followed by regex match on `^(Figure|Fig\.?)\s+\d+`.
     If the pairing is uncertain, mark caption as `(auto-paired, verify)`
     in the artifact rather than guessing.

   - **Caption length**: captions can run 100–2000+ characters
     (Lee et al. 2026 Fig. 2 caption is 1420 chars). Keep the per-figure
     summary table compact (one-line `headline` only) and put the
     verbatim `caption_full` in a separate "Figure captions" section
     below the table. Do not truncate `caption_full` — downstream stages
     need it intact.

5. **Build glossary**: Identify 8–15 technical terms that a non-specialist in
   the audience might struggle with. Define each in one line. Sources: abstract,
   methods section, keywords. Prefer terms that appear in 2+ figures or
   methods subsections — these will need explanation in the talk.

6. **Capture metadata** (ask once, persist):
   - Audience profile (e.g., "HIV/aging postdocs")
   - Time budget (default: 25 min talk + 5 min Q&A)
   - User's angle / focus / skepticism
   - User's existing knowledge of the topic
   - Date of presentation

7. **Write artifacts** under `<journal_club_home>/<paper_id>/`:
   - `_meta.json`
   - `01_ingest.md` (template below)

## Output template — `01_ingest.md`

```markdown
# Stage 1: Ingest — <paper_id>

**Paper**: <title>
**Authors**: <first 6 authors> [et al. if more]
**Journal**: <journal> (<year>)
**IDs**: PMCID <pmcid> | PMID <pmid> | DOI <doi>

**Audience**: <audience profile>
**Time budget**: <talk_min> min talk + <qa_min> min Q&A
**Presentation date**: <date>
**My angle**: <user's stated focus or skepticism>

---

## TL;DR (3 sentences)
<your 3-sentence summary, grounded in the abstract and conclusion>

## Central question
<one sentence — the question the paper is trying to answer>

## Headline finding
<one sentence — what they discovered>

---

## Section map
- INTRODUCTION → <1-line summary>
- RESULTS → <subsections>
- DISCUSSION → <1-line summary>
- METHODS → <key methods worth presenting>

## Figure catalogue
| # | Label | Headline (first sentence of caption) | URL/path |
|---|-------|--------------------------------------|----------|
| 1 | Fig. 1 | <first sentence of caption — the headline finding for that figure> | <url> |
| ... |

## Figure captions (verbatim)

> Captions extracted directly from the paper's `<fig><caption>` blocks.
> Used by Stage 2c per-figure micro-audit, Stage 5 speaker notes, and
> Stage 6 Q&A prep. Do not paraphrase or truncate.

### Fig. 1 — <headline>
> <full caption text, including all panel descriptions A/B/C/...>

### Fig. 2 — <headline>
> <full caption text>

### Fig. N — <headline>
> <full caption text>

## Glossary
- **<term>**: <one-line definition>
- ...

## Methods worth highlighting
- <novel method 1> — why it matters
- <novel method 2> — why it matters

## Standard methods to skim
- <e.g., bulk RNA-seq with standard pipeline>

## References worth following up
- [<ref number>] <citation> — relevance

---

## Next step
Run `/journal-club quiz` to test your comprehension before you build slides.
```

## `_meta.json` schema

```json
{
  "paper_id": "PMC11464121",
  "title": "...",
  "pmcid": "PMC11464121",
  "pmid": "...",
  "doi": "...",
  "source_type": "pmc | preprint | pdf",
  "fetch_source": "pmc | europepmc | playwright-xml | playwright-pdf | metadata-only",
  "xml_path": "xml/PMC11464121.xml",
  "pdf_path": null,
  "supplement_path": null,
  "supplement_text_path": null,
  "supplement_pages": null,
  "supplement_fetch_source": null,
  "audience": "HIV/aging postdocs",
  "talk_minutes": 25,
  "qa_minutes": 5,
  "presentation_date": "2026-05-15",
  "user_angle": "...",
  "stages_completed": ["ingest"],
  "audit_iterations": []
}
```

For preprints, populate `fetch_source` from `info['source']` returned by
`fetch_preprint()`. Downstream stages use this to know whether they have
structured XML or only PDF / metadata.

**Supplement fields** (populated by Stage 2c Step 0 when retrieved):
- `supplement_path`: path to the supplement PDF, e.g. `pdf/media-1.pdf`
- `supplement_text_path`: path to extracted text, e.g. `pdf/media-1.txt`
  (produced by `pdftotext -layout` for grep-based audit search)
- `supplement_pages`: integer page count (from `pdfinfo`)
- `supplement_fetch_source`: one of `europepmc-supplementaryFiles-zip`,
  `pmc-bin-direct`, `playwright-pdf`, `manual-upload`

**`audit_iterations`** is an append-only log of Stage 2c re-runs. Each
entry captures evidence-state at the time of audit so that re-running
the audit (e.g., after fetching the supplement) preserves a record of
how findings shifted. Entry shape:

```json
{
  "stage": "stats",
  "date": "2026-04-30 10:40 EDT",
  "scope": "body-XML + supplement SD1",
  "supplement_retrieved": true,
  "deferred_row_rate_pct": 10,
  "artifact": "2c_stats_repro.md",
  "superseded_artifact": "2c_stats_repro.md.bak.20260430"
}
```

The latest entry's `artifact` is the canonical audit; earlier entries
point to timestamped `.bak.<YYYYMMDD>` backups. This pattern generalizes
to other stages (Stage 3 critique re-runs after new evidence, Stage 6
rehearsal re-runs after audience change) — keep the field stage-agnostic.

## Notes

- **Don't summarize results in this stage** — that comes later. Stage 1 is
  scaffolding only. The user shouldn't read this and feel they "know" the
  paper; they should know how to navigate it.
- If parsing fails (paper not on PMC, PDF corrupt), capture what you can
  manually from the user and proceed.
