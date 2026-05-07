# Stage 2c: Statistics & Reproducibility Audit

**Goal**: Mechanically audit the paper's statistical rigor and reproducibility
posture against a fixed checklist. Produce a per-figure stats table and a
deposition/code/reagent inventory. Every concern must be backed by a quoted
line or a missing-evidence note (e.g., "no FDR threshold stated in Methods").

This stage is the analytical complement to Stage 2b. Stage 2b asks *what was
claimed and what was proven*. Stage 2c asks *whether the numbers and the
materials behind those claims would survive a careful reviewer or a
replication attempt*.

## When to invoke

- The paper makes quantitative claims (essentially every biomedical paper)
- The user will be presenting to a stats-literate audience (most labs)
- Always recommended for: omics / sequencing papers, clinical cohort studies,
  any paper with N ≤ 10 per group, any paper claiming an effect size
- Trigger phrases: "audit the stats", "is this reproducible", "what's their N",
  "did they correct for multiple testing", "is the data public", "check the
  GitHub repo", "are the antibodies reliable"

This stage runs **after Stage 1 (Ingest)** and is independent of Stages 2 and
2b. Its outputs feed Stage 3 (Critique) and Stage 6 (Rehearsal Q&A) — the
defensible-weakness section in Stage 3 should pull verbatim from the
"Top concerns" section here.

## What this stage audits

Three pillars, each with a checklist. The auditor's job is to fill each
checklist row with one of:

| Symbol | Meaning |
|--------|---------|
| ✓ | Reported and adequate |
| ⚠ | Reported but concerning (e.g., test choice questionable) |
| ✗ | Not reported / not done |
| ⊘ | Deferred — supplement not retrieved (auditor's view limited; not a paper failure) |
| N/A | Genuinely doesn't apply |

Every ⚠ and ✗ must include a quote or an explicit "not stated in [section]".

**Why ⊘ is distinct from ✗.** Many papers — especially Nature/Cell/Cell-Press
— place statistical methods, QC criteria, and reagent identity in a
supplementary "STAR Methods" or "Methods" PDF that is *not* in the JATS
body XML. If the auditor couldn't fetch the supplement (Cloudflare-blocked,
embargoed, behind paywall), record ⊘ rather than ✗. ⊘ tells the reader the
paper *might* have done the right thing; the auditor just hasn't seen it
yet. ✗ is reserved for "I looked everywhere I had access to and the paper
genuinely doesn't address this." When a row is ⊘, list the supplement file
that needs retrieval (e.g., "see SD1 — not retrieved").

### Pillar A — Statistical rigor

1. **Sample size & replication structure**
   - N per group (write the actual numbers)
   - **Abstract↔body consistency**: do the headline N, cohort sizes,
     experimental-system count, and other quantitative claims in the
     abstract match what's reported in the body and figure legends?
     Mismatches are usually copy-edit drift between revisions but
     occasionally indicate substantive scope changes; either way, an
     audience member who read only the abstract will ask about it.
   - Biological vs technical replicates clearly distinguished?
   - Pseudoreplication: are within-subject observations (cells from one
     mouse, reads from one library) treated as independent? **This is the
     single most common stats failure in genomics** — flag aggressively
   - Power calculation pre-specified?
2. **Test choice & assumptions**
   - Test name (t-test, Wilcoxon, DESeq2 Wald, log-rank, χ², mixed model…)
   - Appropriate for data type? (count data → negative binomial, not t-test;
     non-normal small-N → non-parametric)
   - Distributional assumptions tested or stated?
   - Paired vs unpaired correctly applied?
   - One-tailed vs two-tailed justified?
3. **Multiple testing**
   - Number of tests run (genes tested, cells compared, contrasts)
   - Correction method: Bonferroni / Benjamini-Hochberg / Holm / none / "we
     report nominal p"
   - FDR threshold stated and consistent across figures?
   - "Top genes" picked by p-value with no correction → red flag
4. **Effect size & uncertainty**
   - Effect size reported alongside p (log2FC, Cohen's d, hazard ratio,
     odds ratio, mean difference)?
   - Confidence intervals or only p-values?
   - Are error bars labeled as SEM / SD / 95% CI / IQR? (Unlabeled = ✗)
   - Do error bar choices match the test (e.g., bootstrap CI for non-parametric)?
5. **Confounding & batch effects**
   - Batch effects acknowledged?
   - Regressed / modeled / matched / ignored?
   - Was the comparison balanced across batches?
6. **Outliers & data exclusion**
   - Pre-specified exclusion criteria?
   - Number of samples excluded + reason?
   - Sensitivity analysis with/without exclusions?
7. **Survival / regression / longitudinal**
   - Proportional hazards tested (Cox)?
   - Regression diagnostics (residuals, leverage)?
   - Repeated measures handled (mixed model vs naïve pooling)?
8. **Garden-of-forking-paths signals**
   - Many subgroup analyses with only "significant" ones featured?
   - Outcome switching between abstract and Methods?
   - Inconsistent FDR thresholds across figures (q<0.05 here, q<0.1 there)?
   - "Trend toward significance" framing?

### Pillar B — Reproducibility & deposition

1. **Raw data deposition**
   - Accession(s): GEO / SRA / ENA / EGA / dbGaP / PRIDE / MetaboLights /
     ArrayExpress / Zenodo
   - **Resolve each accession** — does the URL actually work? Is the data
     released or under embargo? Is it controlled-access?
   - Sample-level metadata (`sample_metadata.csv`) included?
2. **Processed data**
   - Count matrices, peak calls, variant VCFs, methylation matrices
     deposited or only available "on request"?
   - "Available on request" = ✗ for reproducibility purposes
3. **Code availability**
   - Repo URL (GitHub / Bitbucket / GitLab / Zenodo DOI)
   - Last commit date (active or orphaned?)
   - License present (MIT / GPL / Apache / none)
   - README with install + run instructions
   - Dependency pinning: `requirements.txt` / `environment.yml` / `renv.lock` /
     `Dockerfile` / `Singularity.def`
   - **Specific commit hash or release tag** cited in the paper?
4. **Pipeline documentation**
   - Software versions pinned (samtools 1.17, not "samtools")
   - Reference genome build (hg38 / GRCh38.p14 / mm10 / mm39 — note vagueness)
   - Annotation version (GENCODE v44, Ensembl 110)
   - Random seeds reported for stochastic steps (UMAP, clustering, splits)?
5. **Reagent identity**
   - Antibodies: catalog #, clone, lot, RRID, validation citation
   - Cell lines: RRID + authentication method (STR profiling, mycoplasma test)
   - Mice: strain, vendor, RRID, age, sex distribution
   - Plasmids: Addgene ID or full sequence
   - Primers / oligos: in supplementary table?
6. **Figure-source data**
   - "Source Data" files (per-figure CSVs / numerical values) provided?
   - Individual data points overlaid on summary statistics for low-N (Nature/
     Cell standard since ~2017)?
7. **Pre-registration**
   - Analysis plan pre-registered (clinicaltrials.gov / OSF / AsPredicted)?
   - For exploratory work: clearly labeled as exploratory?
8. **Orthogonal validation**
   - Key findings replicated by an independent method (e.g., RNA-seq finding
     confirmed by qPCR; CRISPR result confirmed by independent guide)?
   - Replicated in an independent cohort or system?

### Pillar C — Per-figure micro-audit

For **every main figure** with quantitative data, fill one row of:

| Figure | Y-axis (unit, log/linear) | N (and what N counts) | Error bar type | Test + p-value source | Issues |

Where "what N counts" is the load-bearing question:
- N = mice? cells per mouse? reads per cell? technical reps per sample?
- The paper might say "n=300" — does that mean 300 mice, or 300 cells from
  3 mice? Pseudoreplication detection lives here.

Supplementary figures: audit only those that carry a load-bearing claim.

## Procedure

0. **Fetch the supplementary methods before auditing.** Most modern
   biomedical papers — especially Cell-Press, Nature, and Science — put
   statistical methods, QC criteria, reagent identity, and per-figure N
   details in a supplementary "Methods" or "STAR Methods" PDF that is
   *not* included in the JATS body XML. Detect this case:
   - If `01_ingest.md` flags inline `(Methods)` or `(STAR Methods)`
     references *without* a corresponding body Methods section in the
     section map, the paper is supplement-housed.
   - If body grep for `<sec ` returns no Methods / Statistical Analysis
     section, the paper is supplement-housed.

   When supplement-housed, locate and retrieve before proceeding:
   - **PMC papers — preferred path**: use the Europe PMC supplementary-files
     ZIP endpoint. **Not Cloudflare-protected**, returns supplement PDF +
     all main-figure images in one call:
     ```bash
     curl -sL "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/supplementaryFiles" \
       -o supplementary.zip
     unzip supplementary.zip
     ```
     Typical contents: `media-1.pdf` (the supplement; rename to a
     descriptive slug under `pdf/`), plus `nihpp-<doi-slug>-f<NNNN>.{jpg,gif}`
     (each main figure as both JPG and GIF). Move figure files to
     `images/` and extract supplement text with `pdftotext -layout
     <pdf> <pdf-stem>.txt` for grep-based audit-keyword discovery.
   - **PMC papers — fallback**: enumerate `<supplementary-material>`
     tags in the JATS XML and download each `<media xlink:href="...">`
     individually via `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC<id>/bin/<href>`.
     Note: this path is occasionally 404 even when the EuropePMC ZIP works.
   - **bioRxiv / medRxiv preprints**: the supplement is usually one or
     more PDFs at `https://www.biorxiv.org/content/<doi>v<N>.full.pdf+html`
     or linked from the abstract page. Cloudflare-protected — falls under
     the same `fetch_preprint()` path as the main PDF. **If the preprint
     is also indexed in Europe PMC** (search for the DOI in EuropePMC and
     get a `PMC<id>`), use the supplementaryFiles ZIP path above first —
     it bypasses Cloudflare entirely. If unretrievable, mark all
     supplement-dependent rows as ⊘ (deferred — not ✗) and tell the user
     explicitly which supplement file blocked the audit.
   - **Closed-access journals**: the user must provide the supplement PDF
     locally; ask once and proceed in degraded mode if not available.

   Do not skip this step. An audit done from body XML alone on a
   supplement-housed paper will register ~40% ⊘ rows in Pillars A and B
   — readable, but a much weaker artifact than a full audit.

1. **Read** `01_ingest.md`, the body sections it links, and the
   supplementary methods (if retrieved in Step 0).

2. **Ground truth from primary sources**:
   - For accessions: actually fetch the URL (or use PubMed MCP / direct
     `urllib`). Don't trust that "GSE12345" exists because the paper says so.
   - For code repos: visit the URL, capture last commit date, file listing
     (Dockerfile / env yml / README presence), license status (`license`
     field of the GitHub API — `null` means no LICENSE file → ✗ for B3).
   - For RRIDs: cross-reference against scicrunch.org if any look fabricated.

3. **Walk the three pillars in order**, filling each checklist row with
   ✓/⚠/✗/⊘/N/A and a one-line evidence quote (or explicit absence note).
   Reserve ⊘ for "supplement not retrieved"; never use ⊘ as a fallback
   when you simply didn't look.

4. **Per-figure micro-audit**: build the table for every main figure. If
   the figure legend doesn't state N or the error bar type, that's an
   automatic ⚠ — record exactly what's missing. (If the supplement was
   retrieved in Step 0, check there before flagging — supplementary
   methods often state per-figure N collectively.)

5. **Aggregate to "Top concerns"**: distill the pillar findings into ≤5
   stats concerns and ≤5 reproducibility concerns ranked by reviewer-
   weight (a missing FDR correction outranks a missing antibody lot).
   ⊘ rows are not concerns — they are auditor blind spots; don't pad the
   "Top concerns" with them.

6. **Score each pillar** (Strong / Adequate / Concerning / Inadequate)
   based on the proportion of ✓ rows *among rows the auditor could see*
   (exclude ⊘ from the denominator). Be calibrated — most papers will
   score Adequate-Concerning across at least one pillar; this isn't a
   hit piece. If the ⊘ rate is high (>30%), prefix the headline verdict
   with "*provisional*" and note the supplement-fetch gap explicitly.

7. **If this is a re-run** (a prior `2c_stats_repro.md` exists, e.g.,
   after a Step 0 supplement fetch that previously failed):
   - Back up the prior artifact to `2c_stats_repro.md.bak.<YYYYMMDD>`
     **before** writing the new one — never overwrite silently.
   - Append an entry to `_meta.json` `audit_iterations` with the new
     scope, date, supplement-retrieval state, and ⊘ rate.
   - Populate the **"Iteration shift"** section in the output template
     (below) — call out which verdicts moved, which top concerns
     changed grade, and which top concerns are new. The shift section
     is the highest-leverage part of a re-run; it tells the reader what
     evidence accumulation revealed without forcing them to diff two
     long files.

## Output template — `2c_stats_repro.md`

```markdown
# Stage 2c: Stats & Reproducibility Audit — <paper_id>

**Paper**: <title>
**Citation**: <Authors et al., Journal Year, PMID/DOI>
**Date audited**: <YYYY-MM-DD>
**Auditor**: <user>

---

## Headline assessment

| Pillar | Verdict | One-line summary |
|--------|---------|------------------|
| A. Statistics | <Strong/Adequate/Concerning/Inadequate> | <e.g., "FDR control consistent, but pseudoreplication in Fig 4"> |
| B. Reproducibility | <…> | <e.g., "Raw data on GEO; code repo orphaned 18 months"> |
| C. Per-figure clarity | <…> | <e.g., "3 of 6 figures lack error-bar legend"> |

**Overall**: <one sentence — would I trust the numbers if I had to bet?>

---

## Iteration shift *(re-runs only — omit on first audit)*

Use this section when a prior audit exists and is being superseded
(e.g., after Step 0 supplement fetch resolves rows previously marked ⊘).
On a first-run audit, omit this section entirely.

**Prior artifact**: `<path to .bak.YYYYMMDD>`
**Iteration**: <N> (see `_meta.json` `audit_iterations`)
**Scope shift**: <e.g., "body-XML only → body-XML + supplement SD1 (28 pp)">
**⊘ rate**: <prior%> → <current%>

### Verdicts that moved

| Row | Prior | Now | What the new evidence showed |
|-----|-------|-----|------------------------------|
| A3. Correction method | ✗ | ⚠ | BH-FDR is applied to pathway scoring (q ≤ 0.05) but not to HLAMP region tests — selective, not absent |
| A1. Pseudoreplication | ⚠ (risk) | ⚠ (confirmed) | Supplement explicitly uses cells, not subclones, as units in subclone-level t-tests |
| ... | | | |

### Top concerns that changed grade or framing

| Concern | Prior framing | Refined framing |
|---------|---------------|------------------|
| Multi-test correction | "absent" | "**inconsistent** — applied selectively" |
| Pseudoreplication | "risk" | "**confirmed** in subclone CN comparisons" |
| ... | | |

### Top concerns that are new (only visible after this iteration's evidence)
- <new concern 1>: <one-line evidence>
- <new concern 2>: <one-line evidence>

### Top concerns that are unchanged
- <concern>: <one-line — note that scope shift didn't affect this finding>

**Why this section matters**: A re-run is not just a longer audit — it
is a record of what evidence was added and how it shifted the calibrated
critique. Audiences (and Stage 3) should know which conclusions were
robust to evidence accumulation and which were driven by a single piece
of newly-retrieved evidence.

---

## Pillar A — Statistical rigor

### A1. Sample size & replication structure
| Item | Status | Evidence |
|------|--------|----------|
| N per group reported | ✓/⚠/✗/⊘ | "<quote or 'not stated in Methods'>" |
| Abstract↔body consistency | ✓/⚠/✗ | <e.g., "Abstract: 'n=93 patients, 9 systems'; Body: 'n=94 patients, 8 systems' → ⚠"> |
| Bio vs technical reps distinguished | ✓/⚠/✗/⊘ | "<quote>" |
| Pseudoreplication risk | ✓/⚠/✗/⊘ | <e.g., "Fig 3D: 1200 cells from 3 mice treated as N=1200"> |
| Power calculation | ✓/⚠/✗ | "<quote or absent>" |

### A2. Test choice & assumptions
| Item | Status | Evidence |
|------|--------|----------|
| Test name(s) used | — | <e.g., "Wilcoxon for Fig 2; DESeq2 Wald for Fig 4"> |
| Test appropriate for data type | ✓/⚠/✗ | <e.g., "t-test on count data → ⚠"> |
| Distributional assumptions checked | ✓/⚠/✗ | "<quote or absent>" |
| Paired/unpaired correct | ✓/⚠/✗ | <evidence> |

### A3. Multiple testing
| Item | Status | Evidence |
|------|--------|----------|
| Number of tests stated | ✓/⚠/✗ | <e.g., "32,415 genes tested in Fig 4"> |
| Correction method | — | <e.g., "BH-FDR, q<0.05"> |
| Threshold consistent across figures | ✓/⚠/✗ | <e.g., "q<0.05 in Fig 4, nominal p in Fig 5"> |

### A4. Effect size & uncertainty
| Item | Status | Evidence |
|------|--------|----------|
| Effect size alongside p | ✓/⚠/✗ | <evidence> |
| Confidence intervals | ✓/⚠/✗ | <evidence> |
| Error bars labeled | ✓/⚠/✗ | <evidence> |
| Error bar type matches test | ✓/⚠/✗ | <evidence> |

### A5. Confounding & batch effects
| Item | Status | Evidence |
|------|--------|----------|
| Batch effects acknowledged | ✓/⚠/✗ | <quote> |
| Modeled / regressed / matched | ✓/⚠/✗ | <quote> |
| Comparison balanced across batches | ✓/⚠/✗ | <evidence> |

### A6. Outliers & exclusion
| Item | Status | Evidence |
|------|--------|----------|
| Pre-specified exclusion rules | ✓/⚠/✗ | <quote> |
| N excluded + reason | — | <e.g., "2 mice excluded post-hoc; reason: 'low quality'"> |
| Sensitivity analysis | ✓/⚠/✗ | <evidence> |

### A7. Survival / regression / longitudinal (if applicable)
| Item | Status | Evidence |
|------|--------|----------|
| PH assumption tested | ✓/⚠/✗/N/A | <evidence> |
| Regression diagnostics | ✓/⚠/✗/N/A | <evidence> |
| Repeated measures handled | ✓/⚠/✗/N/A | <evidence> |

### A8. Forking-paths signals
- <signal>: <evidence>
- <signal>: <evidence>

---

## Pillar B — Reproducibility & deposition

### B1. Raw data
| Resource | Accession | Resolves? | Public/Embargo | Notes |
|----------|-----------|-----------|-----------------|-------|
| RNA-seq | GSE<NNNNN> | ✓/✗ | Public | <e.g., "Released, processed counts only — raw FASTQs require dbGaP"> |
| WGS | <…> | | | |

### B2. Processed data
- <e.g., "Count matrices on Zenodo (DOI: …)">
- <"Methylation matrices: 'available on request' → ✗">

### B3. Code
| Item | Status | Evidence |
|------|--------|----------|
| Repo URL | — | <https://github.com/...> |
| Last commit | — | <YYYY-MM-DD; X months ago> |
| License | ✓/✗ | <license name or absent> |
| README | ✓/⚠/✗ | <evidence> |
| Dependency pinning | ✓/⚠/✗ | <e.g., "Dockerfile present"> |
| Commit hash cited in paper | ✓/✗ | <evidence> |

### B4. Pipeline docs
| Item | Status | Evidence |
|------|--------|----------|
| Software versions pinned | ✓/⚠/✗ | <evidence> |
| Reference genome build | ✓/⚠/✗ | <e.g., "hg38" → ⚠ no patch level> |
| Annotation version | ✓/⚠/✗ | <evidence> |
| Random seeds | ✓/⚠/✗ | <evidence> |

### B5. Reagent identity
| Item | Status | Evidence |
|------|--------|----------|
| Antibodies (cat# + RRID + clone) | ✓/⚠/✗ | <e.g., "Cat# given but no RRID for 2/5 antibodies"> |
| Cell line authentication | ✓/⚠/✗ | <evidence> |
| Mouse strain RRID | ✓/⚠/✗/N/A | <evidence> |
| Plasmids (Addgene / sequence) | ✓/⚠/✗/N/A | <evidence> |

### B6. Figure source data
- Per-figure source data files: ✓/⚠/✗ — <evidence>
- Individual data points shown when N≤10: ✓/⚠/✗ — <evidence>

### B7. Pre-registration
- <Pre-registered? Where? Or "exploratory, no pre-reg">

### B8. Orthogonal validation
- <Key finding 1>: <independent method or replication>
- <Key finding 2>: <independent method or replication>

---

## Pillar C — Per-figure micro-audit

| Figure | Y-axis (unit, scale) | N (and what N counts) | Error bar | Test + source | Issues |
|--------|----------------------|----------------------|-----------|----------------|--------|
| Fig 1A | log2(TPM+1), linear | n=6 mice/group | SEM | t-test, legend | — |
| Fig 1B | % positive cells | n=4500 cells from 3 mice | SD | t-test, legend | ⚠ pseudoreplication |
| Fig 2A | <…> | <…> | <…> | <…> | <…> |
| ... |

---

## Top concerns (feed Stage 3)

### Stats — top 3
1. **<concern>** — <evidence>. **Why it matters**: <impact on headline claim>
2. ...
3. ...

### Reproducibility — top 3
1. **<concern>** — <evidence>. **Why it matters**: <impact>
2. ...
3. ...

---

## Reproducibility wins worth highlighting
- <e.g., "Full Snakemake pipeline + Dockerfile, pinned to commit a3f9b2">
- <e.g., "All antibodies have RRIDs and validation refs">

---

## Recommended audience-prep phrases

For Q&A defense (cross-reference these with `06_rehearsal.md`):
- If asked about pseudoreplication: "<honest framing>"
- If asked about FDR: "<paper's actual threshold + your view>"
- If asked about data availability: "<accession + what's missing>"
- If asked "would you trust these numbers": "<calibrated bottom line>"
```

## Notes on rigor

- **Verify accessions, don't trust them.** A surprising fraction of papers
  cite accessions that 404, are still embargoed, or contain only processed
  data labeled as raw. The audit should record what actually resolves.
- **Pseudoreplication is the #1 finding in genomics audits.** When in
  doubt, ask: "If we increased the cells-per-mouse 10×, would N go up?"
  If yes, those cells are pseudoreplicates and the effective N is mice,
  not cells. Flag every figure where this matters.
- **"Available on request" = ✗.** This is a 2020s-era reproducibility
  failure mode. The decade of data shows requests overwhelmingly go
  unanswered. Score it accordingly without apology.
- **Calibration over harshness.** A high-quality paper will pass most rows.
  An audit that flags everything is uncalibrated. Reserve ⚠/✗ for items
  that would change a careful reader's confidence.
- **Don't fabricate.** If Methods is silent on a test assumption, write
  "not stated in Methods" — do not infer that the assumption was checked.

## One-shot retrieval mode

When the user asks something like "audit the stats and reproducibility of
Smith et al. 2024 (PMID 12345678)":

1. Run Stage 1 (Ingest) silently if `01_ingest.md` doesn't exist
2. Run this stage in full — including resolving all accessions and
   visiting the code repo URL
3. Print a condensed view in the conversation: the headline assessment
   table, plus "Top concerns" stats + repro lists
4. Tell the user the artifact path and offer to feed concerns directly
   into Stage 3 (Critique)

## Stop conditions

- All three pillars audited + per-figure table built → write artifact,
  update `_meta.json`, suggest Stage 3
- Paper has no quantitative claims (rare; review papers, perspectives) →
  produce a short artifact noting Stage 2c is N/A and explaining why,
  then suggest Stage 3 directly

## How this feeds downstream stages

- **Stage 3 (Critique)** — "Top concerns" lists become the spine of the
  Defensible Weaknesses section. Don't restate the same concerns in
  free-form prose; reference them.
- **Stage 4 (Outline)** — the Critical Evaluation section gets a
  pre-populated bullet per Top Concern, ranked by severity.
- **Stage 6 (Rehearsal Q&A)** — every ⚠/✗ in the audit becomes a
  candidate Q&A item. Statistics-flavored audiences ask exactly these
  questions; pre-loading the answers is the whole point.
- **Stage 7 (Writeup)** — if the audience surfaces concerns the audit
  missed, log them in `07_writeup.md` so future Stage 2c runs can be
  improved.
