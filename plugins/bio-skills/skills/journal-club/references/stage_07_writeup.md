# Stage 7: Writeup — Post-Presentation Summary

**Goal**: After the journal club, capture what was discussed, what the user
learned, what they got wrong, and what's worth following up. This becomes a
durable reference — for the user's notes, for future presenters, and for
extending the user's research.

## When to run

Immediately after the talk while it's fresh. The longer the gap, the more
gets lost.

## Procedure

1. **Read** all prior artifacts plus `06_rehearsal.md`.

2. **Ask the user** (one at a time):
   - "How did the talk go overall?"
   - "What questions came up that you didn't anticipate?"
   - "What did you get wrong in your answers? What did you not know?"
   - "What new ideas came out of the discussion?"
   - "What follow-up reading or experiments did people suggest?"
   - "Would you change anything in your slides for next time?"

3. **Build a structured writeup** using the template below.

4. **Update the `06_rehearsal.md`** with the actual questions asked
   (separate section: "Asked at journal club") so future runs of this skill
   on similar papers can learn from it.

## Output template — `07_writeup.md`

```markdown
# Stage 7: Journal Club Writeup — <paper_id>

**Paper**: <title>
**Date presented**: <YYYY-MM-DD>
**Audience**: <audience>
**Duration**: <actual minutes>

---

## TL;DR (3 sentences)
<distilled, post-discussion understanding>

## What the paper showed
<2–3 paragraphs — your refined understanding after presenting>

## Methods used
<table or list of methods, with key parameters>

## Key results
1. <result 1, with effect size>
2. <result 2>
3. ...

## Strengths
- ...

## Limitations (post-discussion view)
- <limitation>: <how the room reacted, anything new that emerged>
- ...

---

## Q&A debrief

### Questions I anticipated and handled well
- <question>: <how it went>

### Questions I didn't anticipate
- **Q**: <question>
  - **Asked by**: <person/role>
  - **My answer**: <what you said>
  - **Better answer**: <what you'd say next time>
  - **Action**: <follow up reading/experiment if any>

### Questions I got wrong
- **Q**: <question>
  - **What I said**: <answer>
  - **What I should have said**: <correct answer with citation>

---

## New insights from discussion
- <insight 1>: <how it changes your view>
- <insight 2>: ...

## Follow-up
- **Reading**: <papers/reviews suggested>
- **Methods to learn**: <techniques mentioned>
- **Experiments to try**: <ideas that came up>
- **People to talk to**: <if mentioned>

## Connection to your work
<how this paper changes or supports your research direction>

---

## Lessons for next journal club
- What I'd structure differently: <slide changes>
- What I'd prep more for: <Q&A topic>
- What worked well: <keep doing this>

---

## References for follow-up
- <citation 1>
- <citation 2>
```

## Notes

- This artifact has long-term value. Encourage the user to commit it to
  their lab notebook or shared knowledge base.
- If the user is too tired right after the talk, suggest doing a 5-minute
  voice memo of "what came up" and parsing it later — better than nothing.
- The "Connection to your work" section is the highest-leverage part for
  the user's research. Don't skip it.

## Closing the loop

After Stage 7:
- Update `_meta.json` `stages_completed` to include all 7 stages.
- Tell the user the artifact path and offer to print a clean
  consolidated PDF combining `01_ingest.md` + `07_writeup.md` for their
  records.
