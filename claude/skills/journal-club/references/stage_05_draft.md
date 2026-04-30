# Stage 5: Draft — Slide-by-Slide Content

**Goal**: Convert the outline into actual slide content. Each slide gets a
title, body bullets (≤4 per slide), figure placement, and speaker notes.

## Format choice

By default, produce a markdown draft that maps cleanly to PowerPoint, Google
Slides, or Reveal.js. If the user explicitly wants a `.pptx` file, invoke the
`pptx` skill at the end and convert.

## Procedure

1. **Read** `04_outline.md`, `01_ingest.md`, `02_comprehension.md`,
   `03_critique.md`, `_meta.json`.

2. **For each slide in the outline**, generate:
   - **Title** (≤8 words)
   - **Bullets** (≤4 bullets, ≤12 words each — strict)
   - **Visual** (figure URL/path, or "diagram needed", or "text-only")
   - **Speaker notes** (2–4 sentences, what the user actually says — not
     just rehashing the bullets)
   - **Source citation** (which paper section / figure this comes from)

3. **Apply the "one slide, one idea" rule**: if a slide has two distinct
   takeaways, split it. Better 26 focused slides than 22 packed ones.

4. **Figure placement**: every results slide must specify where the figure
   goes (full-slide, right half, embedded inline). Pull URLs from
   `01_ingest.md` Figure catalogue.

5. **Speaker notes are critical**: this is the part the user will rehearse.
   They should read like a transcript, not bullet expansions. Include
   transitions ("Now that we've seen X, let's look at Y...").

6. **Comprehension flag**: if `02_comprehension.md` is missing or marked
   "bypass-unilateral", prepend the artifact with:
   ```
   ⚠ Generated without comprehension check.
   Review carefully before presenting — risk of shallow answers in Q&A.
   ```

## Output template — `05_slides_draft.md`

```markdown
# Stage 5: Slide Draft — <paper_id>

**Total slides**: <N>
**Estimated runtime**: <X> min

---

## Slide 1 — <Title>
**Section**: Title slide
**Visual**: text-only (title slide layout)
**Bullets**:
- <Paper title>
- <Authors et al., Journal Year>
- Presented by <user> | <date>

**Speaker notes**:
"Today I'm presenting <title>, published in <journal> in <year>. The reason
this caught my attention is <hook>. Over the next <N> minutes I'll walk
through the central question, methods, key results, and what I think this
means for our work."

**Source**: `01_ingest.md`

---

## Slide 2 — Why this paper matters
**Section**: Why this paper
**Visual**: <suggested image or "text-only">
**Bullets**:
- <hook bullet 1>
- <hook bullet 2>
- <relevance to audience>

**Speaker notes**:
"<2–3 sentences explaining why the audience should care>"

**Source**: `01_ingest.md` (TL;DR + user_angle)

---

## Slide 3 — Background: what was known
...

## Slide 10 — Result 1: <one-line takeaway>
**Section**: Figure walk
**Visual**: Figure 1 (full-slide)
URL: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11464121/bin/<filename>`
**Bullets**:
- What they did: <one phrase>
- What they found: <one phrase>
- Effect size: <number>

**Speaker notes**:
"In Figure 1, the authors <method>. The y-axis shows <metric>, the x-axis
shows <variable>. The key takeaway is <finding>. Notice that <interesting
detail or caveat>."

**Source**: `01_ingest.md` Figure 1, `02_comprehension.md` Q4

---

[continue for all slides]

---

## Pre-talk checklist
- [ ] All figures load (test in slide software)
- [ ] Speaker notes printed or visible in presenter view
- [ ] Time-checked sections against budget
- [ ] Backup slide for audience question about <weakness>
- [ ] Glossary slide for <terms> if specialist audience
```

## Conversion to PowerPoint

If the user asks for `.pptx`:
1. Confirm the slide count and figure URLs are settled
2. Invoke the `pptx` skill (or `example-skills:pptx`)
3. Pass the slide draft markdown as input

## Anti-patterns

- **Bullet-expansion speaker notes**: speaker notes that just rephrase the
  bullets are useless. They should add what the bullet doesn't.
- **Wall-of-text slides**: if a slide has 5+ bullets, split it. The audience
  reads instead of listening.
- **Embedded full paragraphs**: never. If you need to quote, pull a single
  sentence in italics.
- **Tiny figures**: figures should occupy ≥40% of the slide area unless
  truly supplementary.
