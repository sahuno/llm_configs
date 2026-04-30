# Stage 2: Quiz — Comprehension Check

**Goal**: Test the user's actual understanding before they build slides. Find
the weak spots where their grasp is shallow, then patch them. Output is a
report the user can re-read before presenting.

## Why this matters

Speakers who skip comprehension and go straight to slides get destroyed in Q&A.
This stage is the firewall: if the user can't articulate the methods, results,
or limitations in their own words, no amount of slide polish saves them.

## Procedure

1. **Read** `journal_club/<paper_id>/01_ingest.md` and `_meta.json`. If
   missing, run Stage 1 first.

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
**Mode**: Interactive | Bypass-condensed | Bypass-unilateral

## Strengths (what the user understood well)
- <topic>: <one-line note>
- ...

## Weak spots (review before presenting)
- **<topic>**: <gap identified> → <correct answer with citation>
- ...

## Key facts to memorize for Q&A
- Sample sizes: <numbers from each cohort>
- Effect sizes: <key statistics>
- Comparison group: <what was compared to what>
- One-sentence summary of each main result

## Methods checklist (must be able to explain)
- [ ] Why method X was chosen over alternatives
- [ ] What parameter most affects the outcome
- [ ] How they validated the main finding
- [ ] What controls were used

---

## Transcript (full Q&A)
**Q1**: <question>
**A1** (user): <answer>
**Note**: <classification + any gap-fill>

**Q2**: ...
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
