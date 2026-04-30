# Stage 1: Ingest

**Goal**: Get the paper into the project, parse it into structured form, capture
audience and time-budget metadata, and produce a one-page ingestion report
the user can scan in 60 seconds.

## Inputs

- A paper identifier: PMCID (preferred), bioRxiv/medRxiv DOI, PMID, or path to a local PDF
- (Optional) audience profile and time budget — if not given, ask once

## One-time setup (for preprint support)

bioRxiv and medRxiv preprints are protected by Cloudflare Turnstile, so
fetching full text requires a real headless browser. Install once per machine:

```bash
pip install playwright cloudscraper
python -m playwright install chromium
```

`scripts/pmc_utils.py::fetch_preprint()` will use these tools automatically
when needed. If they're missing, the function gracefully degrades to
metadata + abstract only and tells the user how to install.

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

3. **Fetch + parse** (route by source):

   **PMC source**:
   ```python
   from scripts.pmc_utils import download_pmc_xml, parse_pmc_xml
   download_pmc_xml([pmc_id], output_folder='xml/')
   paper = parse_pmc_xml(f'xml/{pmc_id}.xml')
   ```

   **Preprint source (bioRxiv / medRxiv)**:
   ```python
   from scripts.pmc_utils import fetch_preprint, parse_pmc_xml
   info = fetch_preprint(
       doi, server='biorxiv',
       output_folder=f'{paper_dir}/xml',
       pdf_folder=f'{paper_dir}/pdf',
       images_folder=f'{paper_dir}/images',  # auto-extracted on PDF success
   )
   # info['source'] tells you which path succeeded:
   #   'europepmc'      → full JATS XML (preferred)
   #   'cloudscraper'   → full JATS XML via Cloudflare bypass
   #   'playwright-xml' → JATS XML via headless Chromium
   #   'playwright-pdf' → PDF download + auto-extracted images
   #   'metadata-only'  → only abstract returned; user must fetch PDF manually

   # When source == 'playwright-pdf':
   #   info['pdf_path']   → saved PDF
   #   info['images_dir'] → directory of per-page PNG figures
   #   info['n_images']   → count of extracted images
   # No separate `extract_pdf_images.py` invocation needed; it's automatic.

   if info['xml_path']:
       paper = parse_pmc_xml(info['xml_path'])
   elif info['pdf_path']:
       # PDF + images already extracted. Use markitdown +
       # clean_markitdown_pdf.sh for text; images are at info['images_dir'].
       pass
   else:
       # Only metadata available. Use info['title'], info['abstract'].
       # Tell the user the preprint isn't fully accessible programmatically
       # and suggest manual PDF download via info['pdf_url'].
       pass
   ```

   **Local PDF**: use markitdown + `clean_markitdown_pdf.sh` for text and
   `extract_pdf_images.py` for figures. Build a synthetic `paper` dict with
   the same shape as `parse_pmc_xml()` output so downstream stages don't
   need to know which source produced it.

4. **Build figure catalogue**:
   - **PMC**: parse `<fig>` blocks in the JATS XML for label, caption, and
     `<graphic xlink:href>` filename. Construct URL:
     `https://www.ncbi.nlm.nih.gov/pmc/articles/<PMCID>/bin/<filename>`.
   - **Preprint XML (EPMC / Playwright)**: parse `<fig>` blocks the same way.
     bioRxiv preprint figures aren't always linked in the XML — for those,
     fall back to PDF figure extraction.
   - **PDF (preprint or local)**: run `scripts/extract_pdf_images.py` on the
     PDF. List extracted images with page numbers. For preprints, the PDF is
     usually saved at `pdf/<server>_<slug>.pdf` by `fetch_preprint()`.

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

7. **Write artifacts**:
   - `journal_club/<paper_id>/_meta.json`
   - `journal_club/<paper_id>/01_ingest.md` (template below)

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
| # | Label | One-line description | URL/path |
|---|-------|---------------------|----------|
| 1 | Figure 1 | <description> | <url> |
| ... |

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
  "audience": "HIV/aging postdocs",
  "talk_minutes": 25,
  "qa_minutes": 5,
  "presentation_date": "2026-05-15",
  "user_angle": "...",
  "stages_completed": ["ingest"]
}
```

For preprints, populate `fetch_source` from `info['source']` returned by
`fetch_preprint()`. Downstream stages use this to know whether they have
structured XML or only PDF / metadata.

## Notes

- **Don't summarize results in this stage** — that comes later. Stage 1 is
  scaffolding only. The user shouldn't read this and feel they "know" the
  paper; they should know how to navigate it.
- If parsing fails (paper not on PMC, PDF corrupt), capture what you can
  manually from the user and proceed.
