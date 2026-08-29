# Stage 2b: Causal Claims Breakdown

**Goal**: Extract every causal claim the paper makes, map each to the
specific experiments that support it, classify the evidence as necessity vs.
sufficiency, and explicitly call out what the paper *cannot* establish.
Every claim and limitation must be backed by **a quoted line from the paper**
with a section/figure/page citation.

This is the analytical counterpart to Stage 3 (Critique). Stage 2b extracts
*what is being claimed*; Stage 3 evaluates *whether the claims hold up*.

## When to invoke

- The user asks for a "structured breakdown" of causal claims
- The user mentions necessity, sufficiency, mechanism, causation
- The paper makes mechanistic claims (e.g., "X drives Y", "Y depends on X",
  "loss of X is sufficient to cause Z")
- Always recommended for biomedical mechanism papers and any paper that
  the user will defend or critique on causal grounds

This stage can run independently — the user does not need to have completed
Stage 2 first. It can be invoked one-shot:

> "Retrieve De Cecco et al. Nature 2019 (PMID 30728521) on LINE-1 and
> senescence. I want to understand: (1) what causal claim they make,
> (2) what experiments they used to establish that causality — specifically
> necessity and sufficiency — and (3) what they could not prove."

In that case, run Stage 1 (Ingest) silently first if no `01_ingest.md`
exists, then run this stage.

## The causal framework

A clean causal argument in biomedicine usually requires showing:

| Type | What it shows | Classic experimental form |
|------|---------------|---------------------------|
| **Correlation** | A and B co-occur | Observation, profiling |
| **Necessity** | Removing A abolishes B | Knockout, knockdown, inhibitor, depletion, deletion |
| **Sufficiency** | Adding A alone produces B | Overexpression, ectopic induction, treatment with purified A |
| **Mechanism** | Pathway from A to B is identified | Epistasis, rescue experiments, biochemistry |
| **Generalizability** | Works in multiple systems | Multiple cell lines, organisms, primary cells, in vivo |

A strong causal claim ideally has correlation + necessity + sufficiency +
mechanism. Many papers fall short on one or more — that's not a flaw, it's
a limitation worth naming explicitly.

### Useful framings to apply

- **Bradford Hill criteria** (epidemiology heritage): strength, consistency,
  specificity, temporality, biological gradient, plausibility, coherence,
  experiment, analogy
- **Koch's postulates** (microbiology heritage): isolation → reintroduction →
  recapitulates disease
- **Genetic epistasis**: if A acts upstream of B, knocking out A and
  overexpressing B should rescue the phenotype

You don't need to formally apply these — but they help structure what to
look for.

## Procedure

1. **Read the paper sections** parsed in `01_ingest.md`. Focus on:
   - Abstract — usually contains the headline causal claim
   - Last paragraph of Introduction — claim statement
   - Each Results subsection — one claim per subsection, typically
   - Discussion paragraph 1 — restated claim
   - Discussion final paragraphs — what they admit they couldn't show

2. **Identify each distinct causal claim**. A claim has the structure:
   "X causes/drives/induces/promotes/inhibits Y in context Z."
   List them. Most papers have 1 main claim and 2–4 supporting claims.

3. **For each claim**, fill out the schema below.
   - Quote 1–2 specific lines from the paper that *state* the claim
     (with section + paragraph reference)
   - List the experiments that support it, classified as
     correlation / necessity / sufficiency / mechanism / generalizability
   - Quote 1–2 lines that describe the *result* of the key experiment
   - Note the model system (cell line, organism, primary cells, patients)

4. **Identify what the paper does NOT prove** — explicitly. This is the
   highest-value section of the breakdown. Look for:
   - Claims made in Discussion that exceed the data shown
   - Necessity shown but not sufficiency (or vice versa)
   - Mechanism inferred but not directly demonstrated
   - Single-system findings claimed as general
   - Statistical association claimed as causal
   - Quote the line where the claim overreaches, and pair it with the
     experiments that would have been needed to support it

5. **Quote everything**. Every claim, every result, every limitation must
   include the exact line from the paper. Use ellipsis for trimming
   (`"...key phrase..."`) if quoting in full would be excessive.

## Output template — `2b_causal.md`

```markdown
# Stage 2b: Causal Claims Breakdown — <paper_id>

**Paper**: <title>
**Citation**: <Authors et al., Journal Year, PMID/DOI>
**Date analyzed**: <YYYY-MM-DD>

---

## Headline causal claim
**Claim**: <one sentence: A causes B in context C>

**Stated in paper**:
> "<exact quoted line>" — Abstract, sentence N
> "<exact quoted line>" — Discussion, paragraph 1

**Model systems used**: <cell line / organism / primary cells / patient cohort>

---

## Evidence map

### Claim 1: <restate claim>

| Evidence type | Experiment | Result quote | Figure/section | Verdict |
|---------------|-----------|--------------|----------------|---------|
| Correlation | <exp> | "<line>" | Fig 1A | ✓ |
| Necessity | <e.g., LINE-1 knockdown> | "<line>" | Fig 3B | ✓ |
| Sufficiency | <e.g., LINE-1 overexpression> | "<line>" | Fig 4C | ✓ |
| Mechanism | <e.g., cGAS-STING epistasis> | "<line>" | Fig 5 | partial |
| Generalizability | <e.g., multiple cell types> | "<line>" | Fig 6 | ✓ |

**Strength of the causal argument**: <strong / moderate / weak>
**Why**: <one sentence>

### Claim 2: <next claim>
...

---

## What the paper CANNOT establish

### Limitation 1: <e.g., directionality not shown in vivo>

**Where the paper overreaches**:
> "<exact line where the discussion goes beyond the data>" — Discussion, paragraph N

**What was shown**: <e.g., correlation in vivo, causation only in vitro>

**What would be needed**: <e.g., conditional knockout in mice with tissue-specific
expression>

**Why it matters**: <one sentence — does this undermine the headline claim,
or is it a known boundary condition?>

### Limitation 2: ...

---

## Causal scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Correlation established | ✓ / ✗ | |
| Necessity demonstrated | ✓ / ✗ / partial | |
| Sufficiency demonstrated | ✓ / ✗ / partial | |
| Mechanism dissected | ✓ / ✗ / partial | |
| Generalizable across systems | ✓ / ✗ / partial | |
| Reverse causation excluded | ✓ / ✗ / partial | |
| Confounders addressed | ✓ / ✗ / partial | |

**Overall causal strength**: <strong / moderate / weak / suggestive>

**One-sentence honest summary**: <e.g., "The paper convincingly establishes
necessity but sufficiency is shown only in vitro and the in vivo claim is
correlational.">

---

## Citations to follow up
- <related paper that confirms / refutes a key causal claim>
- <method paper for one of the necessity/sufficiency experiments>

## How this feeds Stages 3 (Critique) and 6 (Rehearse)
- The "What the paper CANNOT establish" section becomes ammunition for the
  Critique limitations.
- The strongest causal experiments become the "lean on this" answers in
  Rehearsal Q&A.
- The overreaching Discussion lines become high-probability audience
  questions: "Did they really show that?"
```

## Notes on rigor

- **Quote exactly**. If the line is long, use ellipsis but preserve the
  load-bearing words. Never paraphrase a load-bearing claim.
- **Distinguish claim types**:
  - Methods-section claim = description of what was done (not causal)
  - Results-section claim = factual statement of outcome (often associative)
  - Discussion-section claim = interpretation/extrapolation (often where
    overreach happens)
- **Don't manufacture limitations**. If a paper genuinely supports its
  causal argument well, say so. The goal is calibrated assessment.
- **Quote with context**. A line out of context can be misleading; if needed,
  include the preceding sentence to anchor what's being claimed.

## One-shot retrieval mode

When the user makes a one-shot request like the De Cecco example:
1. Run Stage 1 (Ingest) silently — fetch and parse the paper
2. Run this stage immediately, producing `2b_causal.md`
3. Print a condensed version directly in the conversation (the headline
   claim, the evidence-map table, and the "Cannot establish" section)
4. Tell the user the full artifact path
