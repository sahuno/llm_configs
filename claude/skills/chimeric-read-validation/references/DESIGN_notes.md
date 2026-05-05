# Skill design brief: chimeric-read-validation

**Status**: design notes, not yet built. Captured before context clear so a
fresh session can pick it up. Sibling files (skill.md, scripts/, references/,
examples/) will be authored from this brief.

---

## What this skill is for

A reusable read-level validation toolkit for **breakpoint-style structural
events** called by any tool — viral integrations (HTLV-1, HBV, HPV, EBV,
MCV…), gene fusions (BCR-ABL, RUNX1-RUNX1T1, IGH translocations…), large
insertions (mobile elements, retrotransposons), and inter-chromosomal
translocations. The skill takes a list of candidate breakpoints + the BAMs
that produced them and emits a per-call validation TSV with explicit
verdicts (`pass` / `needs_review` / `fail`), turning "open IGV and look"
into a deterministic, scriptable, auditable step.

This skill exists because in the ATLL HTLV-1 cohort work (May 2026) we
discovered that:
- caller PASS does not mean validated;
- naive Layer-2 spread metrics (stdev) produced false-alarm flags on
  integrations that were actually fine;
- repeat-overlap criteria appropriate for de-novo SV calling are
  inappropriate for viral-integration biology because HTLV-1 integrates
  into AT-rich/repeat-dense regions by design.

Reference implementation that demonstrated the patterns:
`/data1/greenbab/projects/ont/Project_17424/results/20260503_hg38plusHTLV1EBV_cohort_chimeric_read_evidence/`
(`extract_chimeric_reads.py`, `compute_validation_report.py`, plus
`cohort_validation_report.tsv` showing the 9/9 PASS outcome).

---

## Capabilities (3 entry points)

1. **extract** — given a breakpoint table (VCF/BEDPE/BED/TSV) + tumor BAM
   ± normal BAM + target contig name, write per-call chimeric-read TSVs
   with read-name, host primary CIGAR + mapQ, soft-clip lengths, inferred
   host breakpoint, target supplementary mapQ + aligned length, and a
   summary row per call (counts, breakpoint median, MAD, etc.).

2. **validate** — given the per-call TSVs from `extract`, compute the
   validation report TSV: chimeric-read counts, mapQ medians,
   caller-vs-consensus offset, breakpoint concordance (median + MAD +
   fraction-within-X-bp), bimodality split distance, T/N read-name
   overlap, host-flank repeat overlap (informational), and a verdict
   under a tunable rubric.

3. **report** — render a one-page markdown summary of the validation
   table for inclusion in a manuscript Methods section, plus a
   supplementary-table caption.

A samplesheet-driven cohort mode mirrors the `igv-reports` skill pattern.

---

## Top 3 working patterns (the lessons that justified the skill)

### 1. Robust statistics on per-read measurements, not mean+stdev

Per-read breakpoint positions, mapQ values, soft-clip lengths — anything
where each read contributes one observation — should be summarized with
**median + median absolute deviation (MAD) + fraction within ±X bp of the
median**, NOT mean and standard deviation.

Why it matters: stdev squares deviations, so one outlier read with a
breakpoint 5,000 bp off the consensus dominates the metric and produces a
false alarm. The cohort hit this exact pattern: p17424_2 chr7 had stdev =
2,867 bp (alarming) but 94 % of its 18 chimeric reads sat within 10 bp of
the median (clean). The integration is real; the metric was bad.

The skill encodes this rule globally — stdev never enters a verdict
rubric; only median, MAD, and fraction-within-X do.

### 2. Caller PASS + read-level forensics = two layers, both required

A breakpoint caller's PASS is necessary but not sufficient. PASS means
the caller's internal heuristics fired correctly; it doesn't say whether
the supporting reads actually agree with each other or with the called
breakpoint position. For breakpoint-style events the only ground truth
is the chimeric reads themselves.

The skill's verdict logic is therefore: caller PASS → extract chimeric
reads → check whether they support the call at the read level. We
caught no false positives in the ATLL cohort, but the skill's job is to
catch them when they appear; the work pattern matters even when zero
fire on a particular cohort.

Corollary: when a caller's matched-normal classifier rejects a call (as
Severus did for p17424_3 chr3 and p17424_6 chr14), that rejection itself
is informative — it's a contamination signal, not a false-positive
verdict. The skill surfaces this distinction explicitly: "rejected for
contamination" ≠ "rejected for low evidence."

### 3. Biology-aware rubrics, not generic SV thresholds

Generic SV-validation rubrics flag breakpoints in repeat-rich regions
because repeats can cause mapping ambiguity. For viral integration
biology, this is exactly backwards: HTLV-1, HBV, retrotransposons all
preferentially integrate into AT-rich / repeat-dense regions. Flagging
"breakpoint sits in 90 %+ repeat content" as suspicious for a viral
integration miscalls 60-90 % of the cohort.

The skill's rubric makes repeat-overlap **informational** by default and
only escalates to a flag when paired with a corroborating signal (low
host mapQ, low chimeric-read concordance, etc.). The skill ships with a
small library of named rubrics (`viral_integration`, `gene_fusion`,
`mobile_element`, `generic_sv`) so users pick a rubric that matches
their event's biology.

---

## Gotchas the skill must encode (and why)

| # | Gotcha | Why it matters | Fix in the skill |
|---|---|---|---|
| 1 | `mean` / `stdev` on per-read metrics | Outlier reads inflate stdev and trigger false alarms (covered above) | `stdev` never used; rubric uses median + MAD + fraction-within-X |
| 2 | Soft-clip-side heuristic picks wrong end on ambiguous reads | "Pick the larger soft-clip" can be wrong when both clips are near-equal; produces a false breakpoint | Bimodality check: split reads by dominant clip side; if cluster medians differ by ~SVLEN, flag |
| 3 | Caller VAF is per-call, not cohort-clonality | Need cohort-aware reading: similar VAFs across multi-event patient ⇒ truncal; differing ⇒ subclonal | Skill emits per-patient VAF concordance metric (max−min within patient) for downstream interpretation |
| 4 | `samtools view` on supplementary alignments only catches half the chimeric population | Primary alignments with `SA` tags are the right query, not `-f 0x800` filtered reads | Skill defaults to primary-only + SA-tag parsing; documented in answer.md |
| 5 | `minimap2 -L` vs `-Y` produces different SA tag content | Without `-Y`, supplementary alignments may not have the soft-clipped sequence; SA tag parsing breaks | Skill validates SA tag schema before extraction; warns if `-Y` flag absent in BAM @PG header |
| 6 | T/N read-name overlap test must be PER CALL, not per sample | A per-sample contamination signal hides which integration is actually contaminated; per-call resolution is the right unit | Skill computes overlap per integration, not per BAM pair |
| 7 | Hard-coding the target contig name | Skill deployed for HTLV-1 will fail silently on HBV / EBV cohorts | Target contig is a required `--target-contig` argument; skill validates the contig exists in the BAM header |
| 8 | mosdepth summary file naming convention | Reusing existing mosdepth outputs is faster than recomputing, but path conventions differ between projects | Skill accepts `--mosdepth-summary <pattern>` with `{patient}` substitution; falls back to running mosdepth if absent |
| 9 | Repeat-overlap as a verdict trigger | Miscalls viral integrations (covered above) | Repeat overlap demoted to informational; only fires as a flag when paired with low host mapQ |
| 10 | BAM index staleness | `samtools view region` silently returns wrong reads if `.bai` is older than `.bam` | Skill validates `.bai` mtime ≥ `.bam` mtime as a preflight check |
| 11 | Defective-provirus aligned-length expected to be small | A "short" supplementary alignment is biology for defectives, not a low-confidence call | Aligned-length thresholds are conditional on `provirus_class` (intact vs defective); defectives have separate rubric |

---

## Defaults locked in

- `--target-contig` (required, no default — fails fast on misconfiguration)
- `--flanking-bp` 1000 (per-call read-extraction window around the host position)
- `--concordance-window-bp` 10 (the X in "fraction-within-X-bp")
- `--rubric viral_integration` (other choices: `gene_fusion`, `mobile_element`, `generic_sv`)
- `--min-chimeric-reads-pass` 8
- `--min-chimeric-reads-fail` 5
- `--max-caller-vs-consensus-pass-bp` 50
- `--max-caller-vs-consensus-fail-bp` 1000
- `--min-concordance-frac` 0.7
- Logs every run to `logs/run_<TS>.log` per CLAUDE.md §Logging requirements

---

## Triggers (for the SKILL.md description)

Fire when the user asks to:
- "validate" / "audit" / "QC" / "verify" structural-variant calls or breakpoints
- compute per-call chimeric-read evidence
- check whether a caller's PASS calls are real
- "is this integration real?" / "should I trust this fusion call?"
- inspect read-level support for breakpoints, fusions, viral integrations
- /chimeric-read-validation
- references to false-positive checking / read-level confirmation

DO NOT fire when:
- the user is calling SVs / fusions / integrations from scratch (that's the
  caller's job, not validation)
- the user wants visual inspection only (that's igv-reports / igv-screenshots)

---

## Reference materials to bundle

- `references/best_practices.md` — full version of "Top 3 working patterns"
  + extended gotcha table + per-event-type rubric guidance
- `references/rubrics.md` — the named rubrics (viral_integration,
  gene_fusion, mobile_element, generic_sv) with thresholds + rationale
- `references/sa_tag_primer.md` — how to parse SA tags, soft-clip
  semantics, why `-Y` matters
- `scripts/extract_chimeric_reads.py` — generalize from the ATLL ref impl;
  add `--target-contig` parameterization, samplesheet mode
- `scripts/compute_validation_report.py` — generalize from the ATLL ref
  impl; add `--rubric` flag, per-event-type defective handling
- `scripts/render_supp_table_caption.py` — emit a manuscript-ready
  caption + Methods paragraph from the validation TSV
- `examples/htlv1_cohort_validation.sh` — reproduce the ATLL run end-to-end
- `examples/fusion_call_validation.sh` — placeholder for fusion case
- `examples/mobile_element_validation.sh` — placeholder for L1/Alu insertion case

---

## Reference implementation (already on disk, ready to generalize)

`/data1/greenbab/projects/ont/Project_17424/results/20260503_hg38plusHTLV1EBV_cohort_chimeric_read_evidence/`

- `scripts/extract_chimeric_reads.py` — works, ATLL-specific
- `scripts/compute_validation_report.py` — works, ATLL-specific
- `data/cohort_chimeric_read_summary.tsv` — Layer 2 output (raw chimeric-read counts + breakpoint median/stdev)
- `data/cohort_validation_report.tsv` — Layer 3 output (validation verdicts; 9/9 PASS)
- `data/per_integration/<patient>_<chr>_<pos>_<sid>.chimeric_reads.{tumor,normal}.tsv` — 18 per-call TSVs

Generalization tasks for the skill (~4–6 hours of work):
1. Replace hard-coded `HTLV1` with a `--target-contig` argument
2. Replace hard-coded mosdepth path with a `--mosdepth-summary` arg + auto-fallback
3. Add the named-rubric system (viral / fusion / mobile / generic)
4. Add the `--Y-flag` BAM @PG validation preflight
5. Add the bimodality interpretation (currently in skill design but not in script)
6. Add the per-patient VAF concordance metric
7. Skill-creator standard: skill.md + references/ + scripts/ + examples/ + evals/
