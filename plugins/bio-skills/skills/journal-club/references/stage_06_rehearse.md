# Stage 6: Rehearse — Audience Q&A Prep

**Goal**: Anticipate the questions the audience will ask, and draft suggested
answers. The user practices answering before the talk.

## Why this stage exists

Q&A is where journal club presentations succeed or fail. A speaker who's
prepped 10 likely questions handles a 30-min Q&A confidently. A speaker
who hasn't will freeze on question 2.

## Procedure

1. **Read all prior artifacts**: `01_ingest.md`, `02_comprehension.md`,
   `03_critique.md`, `04_outline.md`, `05_slides_draft.md`, `_meta.json`.

2. **Generate question categories** (8–15 questions total):
   - **Methods clarification** (2–3): "Why did they use X instead of Y?"
   - **Statistics** (2–3): "What was the sample size? Was that powered?"
   - **Limitations** (2–3): pulled from `03_critique.md`
   - **Generalizability** (1–2): "Does this apply to <other context>?"
   - **Translation / impact** (1–2): "What's the clinical relevance?"
   - **Follow-up experiments** (1–2): "What would you do next?"
   - **Hostile / skeptical** (1–2): the toughest questions a critical reviewer
     would ask

3. **For each question**, draft:
   - **Suggested answer** (2–3 sentences max — short, confident)
   - **Confidence level**: 🟢 confident / 🟡 partial / 🔴 honest "I don't know"
   - **Backup**: pointer to a paper section, figure, or stage artifact

4. **For 🔴 questions**, the suggested answer is *how to gracefully say "I
   don't know"*. Examples:
   - "That's a great question — the paper doesn't address it directly.
     My guess would be X, but I'd want to look at Y to confirm."
   - "I noticed that limitation too. The authors don't comment on it."

5. **Rehearsal mode** (optional): offer to quiz the user with 3–5 random
   questions and critique their answers.

## Output template — `06_rehearsal.md`

```markdown
# Stage 6: Audience Q&A Prep — <paper_id>

**Audience**: <audience>
**Anticipated questions**: <N>

---

## Methods clarification

### Q1: Why did they use <method> instead of <alternative>?
**Confidence**: 🟢
**Suggested answer**: <2–3 sentences>
**Backup**: Methods section, paragraph 3 / `01_ingest.md`

### Q2: ...

---

## Statistics

### Q3: What was the sample size and was it powered for the primary analysis?
**Confidence**: 🟢
**Suggested answer**: <numbers, with caveats>
**Backup**: Table 1 / `02_comprehension.md` Q5

---

## Limitations

### Q4: <hardest critique from `03_critique.md`>
**Confidence**: 🟡
**Suggested answer**: <honest engagement, not deflection>
**Backup**: `03_critique.md`

---

## Generalizability

### Q5: Does this generalize to <population the audience cares about>?
**Confidence**: 🟡
**Suggested answer**: ...

---

## Translation / Impact

### Q6: What's the practical implication for <field>?
**Confidence**: 🟢
**Suggested answer**: ...

---

## Follow-up experiments

### Q7: What's the next experiment you'd want to see?
**Confidence**: 🟢
**Suggested answer**: ...

---

## Hostile / skeptical

### Q8: Aren't they over-claiming based on <weakness>?
**Confidence**: 🟡
**Suggested answer**: <agree partially, then explain what's still solid>

### Q9: <toughest reviewer question>
**Confidence**: 🔴
**Suggested answer**: "I don't know — that's a fair critique. My instinct is
<honest take>, but I'd want to see <data/control> to be sure."

---

## Pre-talk drill (recommended)
- Read the 🔴 questions out loud once. Practice the "I don't know" framing.
- Pick 3 random questions and answer them out loud, timed.
- For 🟢 questions, make sure your one-sentence answer is crisp.

## Topics to refresh in your head right before going up
- Sample sizes: <numbers>
- Effect sizes: <numbers>
- The one limitation you're proud to acknowledge: <weakness>
```

## Notes

- **Honesty wins**. Audiences respect "I don't know" much more than bluffing.
- **Don't overprep**. 8–15 questions is enough. If you prep 30, you'll
  forget half. Quality over quantity.
- **Hostile questions are practice gold**. The user should rehearse these
  out loud, not just read them.
