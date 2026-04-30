# Stage 3: Critique — Critical Evaluation

**Goal**: Co-build a structured critique of the paper. The user's own
observations come first; you layer in observations they missed.

## Why interactive

A unilateral critique reads like a hit piece. A co-built critique reflects
what the user actually believes — which is what they need to defend during
Q&A. Audience members can smell when a presenter is parroting someone else's
critique.

## Procedure

1. **Read** `01_ingest.md` and `02_comprehension.md`. The weak spots from
   Stage 2 often hint at where the critique should focus.

2. **Ask the user three opening questions, one at a time**:
   - "What's the strongest thing about this paper?"
   - "What bothers you about it? What's your gut concern?"
   - "If you were the reviewer, what would you have asked them to add?"

3. **Layer in additional observations** along these dimensions:
   - **Statistical rigor**: sample sizes, multiple-testing, effect sizes,
     confidence intervals, power
   - **Controls**: what's missing, what's confounded
   - **Generalizability**: cohort selection bias, single-site studies,
     demographic skew, missing replication
   - **Methodological limits**: choice of method, parameter sensitivity,
     reproducibility of pipelines, data availability
   - **Alternative explanations**: technical artifacts, batch effects,
     reverse causation, selection bias
   - **Claim vs evidence**: places where the discussion overstates findings
   - **What they buried**: limitations only mentioned in supplementary or
     skipped entirely

4. **For each observation**, ask: "Do you agree this is a real concern, or
   am I being too harsh?" Capture the user's verdict.

5. **Identify defensible critiques** (ones the user agrees with and can
   articulate) vs. **speculative critiques** (interesting but not load-bearing).

## Output template — `03_critique.md`

```markdown
# Stage 3: Critique — <paper_id>

**Date**: <YYYY-MM-DD>

## Strengths (worth highlighting in the talk)
- <strength>: <why it matters>
- ...

## Defensible weaknesses (will hold up in Q&A)
### Statistical
- <issue>: <evidence from paper> → <why it's a concern>

### Controls / Confounds
- ...

### Generalizability
- ...

### Methodological
- ...

### Claim vs evidence
- ...

## Speculative critiques (interesting, not load-bearing)
- <observation>: <why it might matter, why it's not airtight>

## Alternative explanations
- For result X: alternative is Y because <reasoning>

## What I would do differently
- <experiment or analysis>: <why it would strengthen the paper>

## Bottom line
<2–3 sentence honest assessment: is this paper convincing? Why or why not?
What's the takeaway despite the limitations?>

---

## Transcript
<the dialogue between you and the user>
```

## Anti-patterns

- **Don't manufacture critiques** to seem rigorous. If the paper is solid,
  say so. Audiences respect honest praise more than performative skepticism.
- **Don't critique the writing style** unless it materially obscures the
  science. "Long sentences" isn't a journal club critique.
- **Don't pile on**. Three strong critiques beat ten weak ones.

## Output must support Stage 4

The "Defensible weaknesses" and "Bottom line" sections feed directly into
Stage 4's `Critical evaluation` slide section.
