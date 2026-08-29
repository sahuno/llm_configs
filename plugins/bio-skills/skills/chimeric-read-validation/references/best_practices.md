# Best practices — chimeric-read validation

This document captures the working patterns and gotchas behind the skill. The
SKILL.md is the entry point; this file is the long-form rationale to consult
when:

- A verdict surprises you and you need to understand why the rubric fired.
- You're deciding which rubric to use for a new event class.
- You're hitting an unexpected failure mode and want to know whether it's
  been seen before.

---

## Top 3 working patterns

### 1. Robust statistics on per-read measurements, not mean+stdev

Per-read breakpoint positions, mapQ values, soft-clip lengths — anything where
each read contributes one observation — should be summarized with
**median + median absolute deviation (MAD) + fraction within ±X bp of the
median**, NOT mean and standard deviation.

**Why it matters.** Standard deviation squares deviations, so one outlier read
with a breakpoint 5,000 bp off the consensus dominates the metric and
produces a false alarm.

**Worked example (the canonical one).** In the ATLL HTLV-1 cohort (May 2026):

- p17424_2 chr7 had **18 chimeric reads supporting the integration**.
- Naïve breakpoint stdev = **2,867 bp** (alarming — would normally trigger
  an artefact flag).
- Robust statistics: **94% (17/18) of chimeric reads sat within ±10 bp of
  the breakpoint median** (clean — call is real).
- The integration was confirmed real; the metric was bad.

**The skill encodes this rule globally.** Standard deviation never enters a
verdict rubric. Only median, MAD, and fraction-within-X do. Look at any
column in `cohort_validation_report.tsv` and you'll find no `stdev` field —
the columns are `chimeric_breakpoint_median`, `chimeric_breakpoint_mad_bp`,
and `frac_chimeric_within_window_of_median`.

**When this rule does NOT apply.** If the underlying biology produces a
genuinely bimodal distribution (e.g., reads sampling both junctions of an
integration), MAD will also look bad. That's what the bimodality check is
for — see pattern #2 below.

---

### 2. Bimodality is the highest-leverage check

When chimeric reads cluster at TWO host positions separated by ~SVLEN bp,
you're sampling both junctions of the event — both LTR-host junctions of a
viral integration, both ends of a mobile element insertion, both
breakpoints of a translocation. High overall breakpoint stdev in this case
is real biology, not an inference artefact.

**The check.** Split chimeric reads by which soft-clip side is dominant:

- Reads with `host_left_clip_bp > host_right_clip_bp` → one cluster.
- Reads with `host_right_clip_bp >= host_left_clip_bp` → the other cluster.

Compute the median breakpoint position within each cluster. If both clusters
are populated and the cluster medians differ by ~SVLEN (within the larger of
50 bp or 10% of SVLEN), the call is bimodal-matching-SVLEN and passes
review even when the global concordance fraction looks poor.

**Why this is the highest-leverage check.** Without it, the only honest
verdict on a bimodal call is "needs_review" — the global breakpoint
distribution looks broken. With it, you can promote bimodal-matching-SVLEN
calls to PASS automatically. In the ATLL cohort this was the difference
between 5/9 PASS and 9/9 PASS.

**Worked example.** p17424_1 chr9: 27 chimeric reads, breakpoint median
34913988, but 12 left-clip-dominant reads clustered at 34913980 and 15
right-clip-dominant reads clustered at 34913988. SVLEN = 9030 bp. Cluster
separation = 8 bp (not ~SVLEN). Bimodality `match=no`. Concordance was
1.0 anyway, so verdict is PASS regardless. The bimodality check pays off
when concordance < 0.7 AND split_distance ≈ SVLEN — that's the cohort
case where reads are sampling both junctions ~SVLEN apart.

---

### 3. Caller PASS + read-level forensics = two layers, both required

A breakpoint caller's PASS is necessary but not sufficient. PASS means the
caller's internal heuristics fired correctly; it doesn't say whether the
supporting reads actually agree with each other or with the called
breakpoint position. For breakpoint-style events the only ground truth is
the chimeric reads themselves.

**The verdict logic.** Caller PASS → extract chimeric reads → check whether
they support the call at the read level. The skill's verdict rubric is the
read-level layer; the caller's PASS is upstream and presupposed.

**Corollary: caller-side rejections are informative.** When a caller's
matched-normal classifier rejects a call (as Severus did for p17424_3 chr3
and p17424_6 chr14 on the ATLL cohort), that rejection itself is
informative — it's a contamination signal, not a false-positive verdict.
The skill surfaces this distinction by using the per-call T/N read-name
overlap as a FAIL criterion. "Rejected for contamination" ≠ "rejected for
low evidence."

**What the skill does NOT do.** It does not call SVs. It does not
re-evaluate a call from raw reads if the caller didn't emit it. The calls
TSV is the input contract — the user is asserting "I ran a caller and
these are the calls I want validated."

---

## Biology-aware rubrics, not generic SV thresholds

Generic SV-validation rubrics flag breakpoints in repeat-rich regions because
repeats can cause mapping ambiguity. For viral integration biology, this is
exactly backwards: HTLV-1, HBV, retrotransposons all preferentially integrate
into AT-rich / repeat-dense regions. Flagging "breakpoint sits in 90 %+
repeat content" as suspicious for a viral integration miscalls 60-90 % of
the cohort.

**The fix.** The skill ships with a small library of named rubrics
(`viral_integration`, `gene_fusion`, `mobile_element`, `generic_sv`) so
users pick a rubric that matches their event's biology. See
`references/rubrics.md` for the full thresholds + rationale per rubric.

**The repeat-overlap demotion.** In all rubrics except `generic_sv`,
repeat-overlap is informational by default and only escalates to a flag
when paired with a corroborating signal (low host primary mapQ). The
threshold pairs are:

| Rubric | `review_repeat_pct_min` | `review_host_mapq_max` | Effect |
|---|---|---|---|
| viral_integration | 85 | 30 | Flag repeats only when host mapping is also poor |
| gene_fusion | 100 | 0 | Effectively never flag repeats — fusions hit clean coding regions |
| mobile_element | 100 | 0 | Never flag — repeats ARE the biology |
| generic_sv | 50 | 40 | Flag repeats directly — they cause mapping ambiguity here |

---

## Extended gotcha table

| # | Gotcha | Why it matters | Fix in the skill |
|---|---|---|---|
| 1 | `mean` / `stdev` on per-read metrics | Outlier reads inflate stdev and trigger false alarms (see Pattern #1) | `stdev` never used; rubric uses median + MAD + fraction-within-X |
| 2 | Soft-clip-side heuristic picks wrong end on ambiguous reads | "Pick the larger soft-clip" can be wrong when both clips are near-equal; produces a false breakpoint | Bimodality check splits reads by dominant clip side; if cluster medians differ by ~SVLEN, call is bimodal-matching and passes review |
| 3 | Caller VAF is per-call, not cohort-clonality | Need cohort-aware reading: similar VAFs across multi-event patient ⇒ truncal; differing ⇒ subclonal | Skill emits per-patient VAF concordance metric (max−min within patient) to a sibling TSV for downstream interpretation |
| 4 | `samtools view -f 0x800` only catches half the chimeric population | The supplementary records are the partner ends of chimeras whose primary records ALSO have SA tags. Filtering for supplementary alone misses the primary-side population entirely. | Skill defaults to primary-only (skip flag 0x100|0x800) + SA-tag parsing — see `references/sa_tag_primer.md` |
| 5 | `minimap2 -L` vs `-Y` produces different SA tag content | Without `-Y`, supplementary alignments may not have the soft-clipped sequence; SA tag parsing breaks | Extract script validates SA tag schema before extraction; warns if `-Y` flag absent in BAM `@PG` header |
| 6 | T/N read-name overlap test must be PER CALL, not per sample | A per-sample contamination signal hides which integration is actually contaminated; per-call resolution is the right unit | Skill computes overlap per call, not per BAM pair |
| 7 | Hard-coding the target contig name | Skill deployed for HTLV-1 will fail silently on HBV / EBV cohorts | Target contig is a required `--target-contig` argument; skill validates the contig exists in the BAM header |
| 8 | mosdepth summary file naming convention | Reusing existing mosdepth outputs is faster than recomputing, but path conventions differ between projects | Skill accepts `--mosdepth-summary-pattern` with `{patient}` substitution; falls back to no coverage if absent |
| 9 | Repeat-overlap as a verdict trigger | Miscalls viral integrations (covered above) | Repeat overlap demoted to informational; only fires as a flag when paired with low host mapQ AND under the `generic_sv` rubric |
| 10 | BAM index staleness | `samtools view region` silently returns wrong reads if `.bai` is older than `.bam` | Skill validates `.bai` mtime ≥ `.bam` mtime as a preflight check |
| 11 | Defective-provirus aligned-length expected to be small | A "short" supplementary alignment is biology for defectives, not a low-confidence call | Aligned-length thresholds are conditional on `provirus_class` (intact vs defective); defective gets a separate, smaller threshold |
| 12 | Severus emits viral integrations as `SVTYPE=INS`, not `SVTYPE=BND` | Filtering on CHROM or ALT alone misses every integration call. `INFO/ALIGNED_POS=` carries the viral coord. | Skill takes calls TSV as input — upstream parsing of the VCF is the user's responsibility, see `analysis-gotchas` skill → `references/severus.md` |

---

## Per-event-type guidance

### Viral integration (HTLV-1, HBV, HPV, EBV, MCV, AAV)

- Rubric: `viral_integration`
- Expect: 5–30 chimeric reads at intact integrations; 2–10 at defective; AT-rich / repeat-dense host sites; bimodal breakpoint distribution when SVLEN > 1 kb.
- Don't treat: high host-flank repeat overlap as a red flag. It's biology.
- Watch for: defective proviruses (small target supplementary aligned length) — set `provirus_class=defective` in the calls TSV to relax the aligned-length threshold.
- Companion: `analysis-gotchas` skill → `references/severus.md` documents the upstream caller-side gotchas (small-contig flank filter, ALIGNED_POS in INFO, etc.).

### Gene fusion (BCR-ABL, RUNX1-RUNX1T1, IGH translocations)

- Rubric: `gene_fusion`
- Expect: tighter breakpoint concordance (often within ±10 bp at exon boundaries); fewer chimeric reads (3–10); coding regions with low repeat overlap.
- Don't treat: low chimeric-read counts (down to 3) as automatic fail — fusion VAFs are often subclonal. The rubric's `min_chimeric_reads_fail` is 3 to allow for this.
- Watch for: read-through transcripts that look like fusions in RNA-seq but aren't fusions at the DNA level. This skill validates DNA-level breakpoints; for RNA-level fusion validation, consider companion tools like Arriba's discarded-call analysis.

### Mobile element insertion (L1, Alu, SVA)

- Rubric: `mobile_element`
- Expect: heterozygous insertions can be present in normal samples too — the T/N overlap criterion is more permissive (still 0 by default, but consider relaxing to allow polymorphic MEIs).
- Don't treat: AT-rich integration site as suspicious. RT-mediated integration prefers AT-rich.
- Watch for: target-site duplications (TSDs) — a short insertion of duplicated host sequence adjacent to the MEI, often confused for a small SVLEN. Set SVLEN to the actual element length, not the TSD-inflated value.

### Generic SV (de novo, non-special region)

- Rubric: `generic_sv`
- Expect: tight breakpoint concordance (within ±10 bp), high host primary mapQ (≥ 40), repeat overlap is a real concern.
- This rubric is the one to use when none of the biology-specific rubrics apply. It's the strictest.

---

## Workflow checklist

Before running the skill on a new dataset:

1. **Confirm `minimap2 -Y`** in the alignment step. Check `samtools view -H <bam>` for the `@PG` line. The extract script does this preflight automatically and warns on missing `-Y`.
2. **Confirm `.bai` is fresher than `.bam`.** Stale indexes silently return wrong reads. The extract script does this preflight too.
3. **Confirm target contig exists in `@SQ`.** The extract script fails fast if `--target-contig` doesn't match a contig in the BAM header.
4. **Decide the rubric.** If unsure, default to `viral_integration` — its biology-aware repeat handling is the safest choice for any breakpoint-style event in a non-clean region.
5. **Build the calls TSV.** Required columns: `event_id, patient, host_chrom, host_pos, tumor_bam`. Optional columns recommended: `normal_bam, svlen_bp, provirus_class, caller_vaf, severus_id`. The richer the calls TSV, the richer the verdict.

---

## When the skill says NEEDS_REVIEW

The verdict is "needs_review" when the call is plausible but at least one
flag fires that warrants a manual look. The `verdict_reasons` column tells
you exactly which flag(s) fired. In the ATLL cohort, common reasons that
turned out to be benign on inspection:

- **"breakpoint concordance 0.61 < 0.70 and not bimodal-matching-SVLEN"**: the
  reads cluster at multiple positions but the cluster separation isn't ~SVLEN.
  Look at the per-call TSV — sometimes there's a third cluster from
  multi-mapping repeat reads. Often resolved by tightening
  `--min-aligned-length` upstream in the caller.
- **"caller call 80 bp from chimeric median"**: the caller's reported pos is
  slightly off from where the reads actually break. Usually fine — the
  chimeric-read consensus is more authoritative than the caller's pos.
  Rare cases where this matters: when the offset crosses an exon boundary
  in a fusion call.
- **"low tumor chimeric reads (6)"**: when 5 ≤ n < 8. Worth eyeballing in
  IGV before publishing. Often real but low-VAF / subclonal.

When the verdict is "fail":

- **"<5 tumor chimeric reads"**: not enough evidence. Re-call upstream
  with relaxed flags or accept that the call is below detection limit.
- **"T/N read-name overlap > 0"**: contamination — the same read supports
  the call in both tumor and normal. This is the strongest fail signal
  and rules out the call as somatic. Note the call may still be a real
  germline event.
- **"caller call 5230 bp from chimeric median"**: the caller pointed at
  the wrong place. Usually a problem in the upstream caller config.
