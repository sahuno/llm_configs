# Stage 4: Outline — Slide Structure with Time Budget

**Goal**: Produce a slide-level outline mapped to the time budget, with each
section specifying its slides, key points, and time allocation. No slide
content yet — that's Stage 5.

## Procedure

1. **Read** `_meta.json` (audience, time budget), `01_ingest.md` (figures,
   methods, glossary), `02_comprehension.md` (weak spots to clarify),
   `03_critique.md` (defensible weaknesses).

2. **Apply the canonical journal club skeleton** from
   `references/presentation_template.md`. Adjust per audience:
   - Specialist audience → less background, more methods/results detail
   - Mixed audience → more background, fewer methods, more figure focus
   - Clinical audience → emphasize translation/implications

3. **Map sections to time** using the budget table (default 25 min talk):

   | Section | Default % | 25 min | 15 min | 45 min |
   |---|---|---|---|---|
   | Why this paper | 5% | 1 min | 1 min | 2 min |
   | Background | 15% | 4 min | 2 min | 7 min |
   | Question / Hypothesis | 5% | 1 min | 1 min | 2 min |
   | Methods overview | 15% | 4 min | 2 min | 7 min |
   | Figure walk (results) | 40% | 10 min | 6 min | 18 min |
   | Critical evaluation | 10% | 2.5 min | 1.5 min | 4 min |
   | Implications & open Qs | 5% | 1 min | 1 min | 2 min |
   | Discussion prompts | 5% | 1.5 min | 1 min | 3 min |

4. **Pick figures**: 3–5 main figures for a 25-min talk. Each gets a slide
   (or two, if it has 4+ panels). Use figure URLs/paths from `01_ingest.md`.

5. **Slide count target**: roughly 1 slide per minute for science-heavy talks.
   25 min → ~22–28 slides. Don't pad.

6. **Each section spec includes**:
   - Number of slides
   - Time allocation
   - Key point per slide (one sentence)
   - Figures/visuals to include
   - Source artifact (which earlier stage produced this content)

## Output template — `04_outline.md`

```markdown
# Stage 4: Slide Outline — <paper_id>

**Talk**: <title>
**Audience**: <audience>
**Time**: <talk_min> min talk + <qa_min> min Q&A
**Total slides**: <N>

---

## 1. Why this paper (1 min, 1 slide)
- **Slide 1** (Title): paper title, your name, date, audience venue

## 2. Background (4 min, 4 slides)
- **Slide 2** (Hook): <relevance/controversy/citation impact>
- **Slide 3** (Field context): <what was known before>
- **Slide 4** (Gap): <what was missing>
- **Slide 5** (Glossary): key terms — pulled from `01_ingest.md`

## 3. Central question (1 min, 1 slide)
- **Slide 6**: one-sentence question + hypothesis

## 4. Methods (4 min, 3 slides)
- **Slide 7** (Study design): cohorts, sample sizes, design diagram
- **Slide 8** (Key method 1): <novel method> with one-line explanation
- **Slide 9** (Key method 2): if applicable

## 5. Results — figure walk (10 min, 10 slides)
- **Slide 10** (Result 1, Figure 1): <one-line takeaway>
  - Visual: Figure 1 panels A–C
- **Slide 11** (Result 1 interpretation): why it matters
- **Slide 12** (Result 2, Figure 2): ...
- ...

## 6. Critical evaluation (2.5 min, 2 slides)
- **Slide N** (Strengths): pulled from `03_critique.md` strengths section
- **Slide N+1** (Limitations): top 3 defensible weaknesses

## 7. Implications & open questions (1 min, 1 slide)
- **Slide N+2**: what this changes, what's still unknown

## 8. Discussion prompts (1.5 min, 1 slide)
- **Slide N+3**: 3 seed questions for the room

---

## Time check
Sum of all section minutes: <X> — should be within 1 min of `talk_min`

## Source map
- Background: `01_ingest.md` (TL;DR, glossary)
- Question: `01_ingest.md` (Central question)
- Methods: `01_ingest.md` (Methods worth highlighting), `02_comprehension.md` (gap-filled understanding)
- Figure walk: `01_ingest.md` (Figure catalogue) + `02_comprehension.md` (per-figure understanding)
- Critical eval: `03_critique.md`
- Implications: `01_ingest.md`, `03_critique.md` Bottom line
```

## Notes

- **Title slide counts as a slide** — don't forget it.
- **Discussion prompts at the end matter** — give the room something to chew
  on. Pull from `03_critique.md` if needed.
- If a section runs over budget, cut figures before cutting background.
  Backgound under-served = lost audience.
