---
name: journal-club
description: Orchestrates a phased workflow for rigorously analyzing and presenting research papers — paper ingestion, comprehension quiz, causal-claims breakdown with quoted evidence (necessity vs. sufficiency vs. what was not proven), critical evaluation, slide outline, slide draft, Q&A rehearsal, and post-talk writeup. Use this skill whenever the user mentions journal club, lab meeting paper presentation, paper deep-dive, preparing slides for a research paper, walking through a study, or asks for help understanding/critiquing/presenting a specific paper — even if they don't explicitly say "journal club." Also trigger on requests like "give me a structured breakdown of this paper", "what causal claims does paper X make and what couldn't they prove", "extract necessity and sufficiency experiments", "what mechanism does this paper establish", or any combination of paper-id (PMID/PMCID/DOI) plus a request for structured analysis, mechanism, causation, or critical reading.
---

# Journal Club Workflow Skill

**Author**: Samuel Ahuno (ekwame001@gmail.com)
**Date**: 2026-04-29

A 7-stage, resumable workflow that transforms a research paper into a polished
journal club presentation — without sacrificing the deep understanding that
keeps speakers from getting destroyed in Q&A.

## Why phased, not one-shot

A one-shot "paper → slides" generator produces polished output but leaves the
presenter shallow on the underlying science. Real journal clubs reward people
who genuinely understand the paper. This skill enforces that depth by splitting
the work into stages where the user must engage actively (Stages 2 and 3),
not just consume Claude's summary.

Each stage produces a markdown artifact, so the user can stop after any stage,
come back later, and pick up where they left off.

## Invocation

```
/journal-club ingest <PMCID|DOI|PDF_path>     # Stage 1: parse paper
/journal-club quiz                            # Stage 2: comprehension Q&A
/journal-club causal                          # Stage 2b: causal claims breakdown (with quoted evidence)
/journal-club critique                        # Stage 3: critical evaluation
/journal-club outline --time <minutes>        # Stage 4: slide outline
/journal-club draft                           # Stage 5: slide content
/journal-club rehearse                        # Stage 6: audience Q&A prep
/journal-club writeup                         # Stage 7: post-talk summary
```

Stage 2b (`causal`) is **strongly recommended** for any paper making
mechanistic claims. It also supports a one-shot retrieval mode where the
user gives a paper ID and asks for a structured causal breakdown — Stage 1
runs silently, then 2b produces the analysis.

If the user's prompt doesn't include an explicit subcommand, infer the stage
from context (e.g., "help me prep journal club for PMC11464121" → Stage 1
`ingest`).

## Project layout

All artifacts live under a **single user-level home for journal clubs** —
default `~/journalClub/`, not the project working directory. This way one
skill instance accumulates a personal library of paper deep-dives across
projects, instead of fragmenting `journal_club/` folders into every repo.

```
~/journalClub/                       # default; override with JOURNAL_CLUB_HOME env var or --dest
└── <paper_id>/                      # paper_id = PMC11464121, doi-slug, or pdf-stem
    ├── _meta.json                   # audience, time budget, paper IDs, stage status
    ├── 01_ingest.md
    ├── 02_comprehension.md
    ├── 2b_causal.md                 # Stage 2b — causal claims with quoted evidence
    ├── 03_critique.md
    ├── 04_outline.md
    ├── 05_slides_draft.md
    ├── 06_rehearsal.md
    ├── 07_writeup.md
    ├── pdf/                         # source PDF (preprints) or copy
    ├── xml/                         # PMC / EPMC JATS XML if available
    ├── images/                      # extracted figure panels (one PNG per page)
    └── <paper_id>.pptx              # final deck (after Stage 5 conversion)
```

**Override the default** in three ways, in priority order:
1. Per-call argument: `/journal-club ingest <paper_id> --dest /some/path`
2. Environment variable: `JOURNAL_CLUB_HOME=/some/path`
3. Default: `~/journalClub/`

When the default home doesn't exist on first run, create it silently — no
prompt needed.

The `_meta.json` file carries audience profile, time budget, paper IDs, and
which stages have completed. Stages downstream of Stage 1 read it to stay
consistent.

## Stage selection logic

When the skill triggers:

1. **If the user named a stage** (`ingest`, `quiz`, `causal`, `critique`, `outline`, `draft`, `rehearse`, `writeup`), run that stage.
2. **If the user named a paper but no stage**, run Stage 1 (`ingest`).
3. **If the user asks a one-shot causal/mechanism question** about a paper (e.g., "what causal claims does X make and what couldn't they prove?"), run Stage 1 silently, then Stage 2b.
4. **If neither**, list the user's `journal_club/` directory and ask which paper + stage they want to resume.

For each stage, read the matching reference file in `references/` for the
detailed protocol — they contain the templates and prompts that make each
stage actually useful.

| Stage | Reference file |
|-------|----------------|
| 1. Ingest      | `references/stage_01_ingest.md` |
| 2. Quiz        | `references/stage_02_quiz.md` |
| 2b. Causal     | `references/stage_2b_causal.md` |
| 3. Critique    | `references/stage_03_critique.md` |
| 4. Outline     | `references/stage_04_outline.md` |
| 5. Draft       | `references/stage_05_draft.md` |
| 6. Rehearse    | `references/stage_06_rehearse.md` |
| 7. Writeup     | `references/stage_07_writeup.md` |

The presentation skeleton used by Stages 4–5 lives in
`references/presentation_template.md`.

## Tools to prefer

- **PMC papers**: use `scripts/pmc_utils.py` from the user's project (functions:
  `download_pmc_xml`, `parse_pmc_xml`, `explore_pmc_xml`). It produces structured
  output (sections, abstract, references, keywords) that's far cleaner than PDF
  parsing.
- **bioRxiv / medRxiv preprints**: use `scripts/pmc_utils.py::fetch_preprint(doi)`.
  It tries Europe PMC first, then cloudscraper, then Playwright headless
  Chromium for Cloudflare-Turnstile-protected XML, and finally Playwright PDF
  download. Returns `{xml_path, pdf_path, full_text_available, source, notes}`.
- **Closed-access PDFs (local files)**: `scripts/extract_pdf_images.py` for
  figures plus `scripts/clean_markitdown_pdf.sh` for text.
- **Figure URLs**: for PMC papers, parse `<graphic xlink:href>` tags in the
  XML — the resulting filenames map to
  `https://www.ncbi.nlm.nih.gov/pmc/articles/<PMCID>/bin/<filename>`.

If `scripts/pmc_utils.py` is missing, mention this and proceed with whatever
parser is available — don't block on it.

## One-time setup (preprint support)

To handle bioRxiv/medRxiv preprints, the user needs Playwright + cloudscraper
installed once per machine:

```bash
pip install playwright cloudscraper
python -m playwright install chromium
```

Without these, `fetch_preprint()` still returns metadata + abstract for any
preprint DOI (the bioRxiv API isn't Cloudflare-protected). It just can't pull
full text for new preprints that aren't yet indexed in Europe PMC.

If a stage runs and full text is missing because Playwright isn't installed,
tell the user once: show the install commands and continue with whatever is
available (often abstract is enough for Stage 1 ingest and Stage 2b causal
breakdown of the abstract-level claims).

## Active-engagement stages

Stages 2 (Quiz) and 3 (Critique) **require dialogue with the user**, not a
one-shot answer dump.

- **Quiz**: ask 8–12 questions one at a time, wait for the user's answer, then
  fill gaps. The goal is to find what the user actually understands vs. has
  glossed over. The output is a comprehension report showing weak spots.
- **Critique**: prompt the user for their first impressions, then layer in
  observations they missed. Don't just dump a critique — co-build it.

If the user wants Stage 2/3 in a single shot ("just give me the answers"),
explain why interaction matters but defer to their preference and produce a
unilateral version flagged as such in the output.

## Persistence

Always write each stage's output to disk before returning. If a stage produces
intermediate analysis worth keeping (e.g., the Quiz transcript), include it in
the artifact under a `## Transcript` section.

After every stage:
1. Write/update `<journal_club_home>/<paper_id>/_meta.json` with the stage status.
2. Tell the user the artifact path.
3. Suggest the next stage.

## Slide deck conversion (Stage 5 → PPTX)

When the user asks to convert the Stage 5 markdown into a PowerPoint deck
(`.pptx`), do **two** things, not one:

1. Translate the slide markdown structure into PPTX (titles + bullets + speaker notes).
2. **Embed one extracted figure image per relevant slide automatically.** For each
   slide whose `**Visual**:` field references a figure (keywords: "Figure", "Fig",
   "panel", "cartoon", "schematic", "diagram", "map"), pick the next unused image
   from `<paper_dir>/images/` (sorted by page number) and place it on the slide
   with a two-column layout (bullets on the left half, image on the right half).
   For slides marked `text-only`, leave the slide bullet-only and skip image
   embedding.

This converts the deck from a "fill in the figures yourself" template into a
working draft the user can refine in PowerPoint. Detailed protocol and a
ready-to-run helper live in `references/stage_05_to_pptx.md`.

## Defaults that matter

- **Default audience**: ask once during Stage 1 and persist. Examples: "HIV/aging postdocs", "mixed grad students", "clinical fellows", "computational biology lab".
- **Default time budget**: 25 min talk + 5 min Q&A unless the user says otherwise. Persisted in `_meta.json`.
- **Figure budget**: 3–5 main figures for a 25-min talk. More for longer talks; never fewer than 2.
- **One slide, one idea**: enforced in Stage 5.

## Error handling

- If a paper isn't on PMC and the PDF parser fails, ask the user to provide either a cleaned markdown version or the abstract + key sections pasted in.
- If `_meta.json` is missing when a downstream stage runs, ask the user for paper_id and audience instead of failing.
- Never overwrite an existing stage artifact silently — append a timestamped backup (`01_ingest.md.bak.<YYYYMMDD>`) and warn the user.

## Anti-patterns to avoid

- **Don't generate slides without the user having engaged in Stage 2 or 3.** Slide quality matters less than the speaker's depth. If the user skips comprehension/critique, flag it in Stage 5 output: "⚠ Generated without comprehension check — review carefully before presenting."
- **Don't bury figures in walls of text.** Stage 5 output should explicitly call out figure placement per slide.
- **Don't fabricate citations or methods.** Every fact in the artifacts traces to the parsed paper or to information the user explicitly provided.
