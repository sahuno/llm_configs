# Stage 2: Quiz — Comprehension Check

**Goal**: Test the user's actual understanding before they build slides. Find
the weak spots where their grasp is shallow, then patch them. Output is a
report the user can re-read before presenting.

## Why this matters

Speakers who skip comprehension and go straight to slides get destroyed in Q&A.
This stage is the firewall: if the user can't articulate the methods, results,
or limitations in their own words, no amount of slide polish saves them.

## Modes

Stage 2 has two complementary modes. Run **both** for any paper the user will
present; the modes catch different kinds of comprehension failure.

| Mode | Catches | When to run | Sub-command |
|---|---|---|---|
| **Text mode** | Conceptual gaps — "I memorized the headline but can't articulate why" | Always; default mode | `/journal-club quiz` |
| **Figure mode** | Visual-literacy gaps — "I read the headline but can't read the y-axis" | Any paper with quantitative figures (almost all biomedical papers) | `/journal-club quiz --figures` |

The figure mode is the higher-yield mode for stats-rigorous audiences. Most
journal-club Q&A failures come from "what does N really count on this axis?"
not from "what is the central question?" — and only the figure mode tests that.

## Procedure — text mode

1. **Read** `<journal_club_home>/<paper_id>/01_ingest.md` and `_meta.json`.
   `<journal_club_home>` resolves to `~/journalClub/` by default; override
   priority is `--dest` arg > `JOURNAL_CLUB_HOME` env var > default. If the
   artifact is missing, run Stage 1 first.

2. **Generate 8–12 questions** spanning these layers:
   - **Comprehension** (3–4): "In your own words, what was the central question?
     What was the key control? What does Figure X actually show?"
   - **Methods** (2–3): "Why did they use method Y instead of Z? What's the key
     parameter that determines outcome?"
   - **Statistics** (1–2): "What's the sample size? Was multiple-testing
     correction applied? What's the effect size?"
   - **Critical** (2–3): "What's the most likely alternative explanation? What's
     the strongest control they're missing?"

3. **Ask one question at a time**. Wait for the user's answer. Do not dump all
   questions up front — the goal is dialogue.

4. **For each answer**, classify silently:
   - ✅ Correct and articulate → praise briefly, next question
   - 🟡 Partially correct or vague → fill the gap, ask follow-up
   - ❌ Incorrect or unsure → explain the actual answer with citation back to
     the paper, mark as a weak spot

5. **Track weak spots** in a running list. After all questions, summarize.

## Procedure — figure mode (multimodal)

This mode requires Claude to **actually look at** the figure images. It depends
on Stage 1 having extracted both the local image files (`images/...`) and the
verbatim caption text (`01_ingest.md` "Figure captions" section).

1. **Read** `01_ingest.md` and `_meta.json` as in text mode. Confirm the
   figure catalogue exists with both `images/<href>` local paths and verbatim
   caption text. If either is missing, route the user to re-run Stage 1.

2. **Pick figures to drill into.** Default: walk all main figures in order. If
   the user supplies `--figure N` or `--figures 1,3,5`, restrict accordingly.

3. **For each figure**:
   a. **Look at the image** at `<paper_dir>/images/<href>` using vision
      capability. Do not skip this step — the whole point of the mode is
      grounding answers against the actual visual content.
   b. **Read the verbatim caption** from `01_ingest.md` — this is the ground
      truth for what the figure shows.
   c. **Ask 3–5 questions per figure** drawing from the question bank below.
      Mix general (open-ended interpretation) with specific (panel-level
      details). Always include at least one **N-source question** — this is
      where pseudoreplication failures hide.
   d. **For each user answer**, compare against (i) what's actually visible
      in the figure and (ii) the caption text. Classify ✅/🟡/❌. For ❌,
      cite the panel and quote the caption fragment that establishes the
      correct answer.

4. **Question bank for figure mode** (pick 3–5 per figure):

   - **What does this figure show?** — open question. The user should be
     able to summarize the figure in 2–3 sentences without reading the
     caption. Compare to the caption headline.
   - **What is the y-axis on panel X?** — units, log/linear, raw vs
     normalized vs z-scored. Tests basic visual literacy.
   - **What does each [dot / bar / cell / point] represent?** — **the
     pseudoreplication trap.** Is it cells, biological replicates, technical
     replicates, patients, regions? Push back if the user gives a vague
     "samples" answer — make them name the unit.
   - **What is the comparison?** — what's being compared to what; is it
     paired or unpaired; is the comparison apples-to-apples (same baseline,
     same conditions)?
   - **What is the take-home from this panel?** — synthesize one sentence.
   - **What's the test?** — what statistical test produced the p-value
     shown on the figure (often this requires the user to consult the
     legend or Methods, not just the image).
   - **Where are the controls?** — identify which panels show control
     conditions vs experimental conditions.
   - **What would change if [X]?** — counterfactual: "If the y-axis were
     log-scaled instead of linear, would the difference still look this big?"
     Tests robustness understanding.
   - **Is the effect size meaningful?** — distinct from "is it
     significant" — what's the absolute change, and is it biologically
     interpretable?

5. **Per-figure verdict**: after the questions for figure N, summarize the
   user's grasp of that figure as ✅/🟡/❌ overall. Move on.

6. **After all figures**: aggregate weak spots into the same running list as
   text mode (or merge with the text-mode list if both were run).

### Figure-mode example flow (Lee paper Fig 1G)

> **Q (mode shows image):** "Looking at Fig. 1G — the classification of 507
> HLAMP regions — what does each dot in this panel represent? Is the unit
> a cell, a region, a case, or something else?"
>
> **A (user):** "I think it's cells."
>
> **Verdict 🟡:** Partial. The caption says "*Classification of 507 HLAMP
> regions from 86,239 cancer cells based on single-cell CN distribution*" —
> so each dot is a *region*, not a cell. The 86,239-cell number is the
> input data, but the unit of inference here is the region. This matters
> because regions are not independent — many come from the same case.
> *Recorded as a weak spot in Pillar A1 (pseudoreplication awareness).*

The figure mode is also where the audit's `2c_stats_repro.md` per-figure
micro-audit table can be cross-referenced — if the audit flagged Fig N for
"unstated error-bar type" or "test not reported in legend", surface that as
context after the user answers.

## Bypass mode

If the user says "just give me the answers" or "I don't have time to do the
quiz", offer:
- A condensed 5-question version (still interactive)
- Or skip to a unilateral comprehension report flagged as ⚠ Unverified

Don't refuse — but explain the cost: "If you skip this, the slide draft will
be technically correct but you may stumble in Q&A. Your call."

## Output template — `02_comprehension.md`

```markdown
# Stage 2: Comprehension — <paper_id>

**Date**: <YYYY-MM-DD>
**Modes run**: Text | Figure | Both
**Interactivity**: Interactive | Bypass-condensed | Bypass-unilateral

## Strengths (what the user understood well)
- <topic>: <one-line note>
- ...

## Weak spots (review before presenting)
- **<topic>**: <gap identified> → <correct answer with citation>
- ...

## Per-figure verdicts *(figure mode only — omit if text mode only)*
| Fig | Headline grasp | Y-axis literacy | N-source / pseudoreplication | Test/test-choice | Overall |
|-----|----------------|-----------------|------------------------------|------------------|---------|
| 1   | ✅ / 🟡 / ❌   | ✅ / 🟡 / ❌    | ✅ / 🟡 / ❌                 | ✅ / 🟡 / ❌    | ✅ / 🟡 / ❌ |
| 2   | ...            | ...             | ...                          | ...              | ... |

## Key facts to memorize for Q&A
- Sample sizes: <numbers from each cohort>
- Effect sizes: <key statistics>
- Comparison group: <what was compared to what>
- One-sentence summary of each main result
- Per-figure: what each dot/bar/point represents (the N-source question)

## Methods checklist (must be able to explain)
- [ ] Why method X was chosen over alternatives
- [ ] What parameter most affects the outcome
- [ ] How they validated the main finding
- [ ] What controls were used

---

## Transcript (full Q&A)

### Text-mode transcript
**Q1**: <question>
**A1** (user): <answer>
**Note**: <classification + any gap-fill>

**Q2**: ...

### Figure-mode transcript
**Fig 1, Q1**: <question — note which panel and what aspect>
**A** (user): <answer>
**Note**: <classification + caption fragment cited if ❌>

**Fig 1, Q2**: ...

**Fig 2, Q1**: ...
```

## Stop conditions

- All questions answered → write artifact, suggest Stage 3 (`critique`)
- User stops mid-quiz → save partial transcript, mark `stages_completed`
  unchanged in `_meta.json`, tell user how to resume

## Notes

- Don't lecture. The user is supposed to be doing the thinking; you're a coach.
- If the user gives a strong answer, say so briefly and move on. Don't pad.
- If the paper itself is wrong about something (e.g., a statistical claim),
  flag it — but only if you're confident.
