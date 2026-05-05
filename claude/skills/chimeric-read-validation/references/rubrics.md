# Verdict rubrics — chimeric-read validation

The skill ships with four named rubrics. Pick the one that matches your
event's biology. Generic SV-validation thresholds applied to viral
integrations or mobile elements miscall most of the cohort because the
underlying biology favors AT-rich / repeat-dense host sites — flagging
that as suspicious is exactly backwards.

If your event class doesn't fit any of these, copy the closest rubric in
`scripts/compute_validation_report.py` (the `RUBRICS` dict) and tune the
thresholds. The four shipped rubrics are themselves illustrations of how
to map biology to thresholds.

---

## viral_integration (default)

Use for: HTLV-1, HBV, HPV, EBV, MCV, AAV, any other small-contig viral
integration.

| Threshold | Value | Rationale |
|---|---|---|
| `min_chimeric_reads_pass` | 8 | Empirical from ATLL cohort: clean integrations had 18–60 reads; 8 is comfortably above the noise floor. |
| `min_chimeric_reads_fail` | 5 | Below this, the call is below detection limit even for low-VAF subclonal integrations. |
| `max_caller_vs_consensus_pass_bp` | 50 | Severus typically reports breakpoint within ±10 bp of the chimeric-read median. 50 bp is forgiving for callers with weaker breakpoint refinement. |
| `max_caller_vs_consensus_fail_bp` | 1000 | The caller pointed nowhere near the chimeric-read consensus — likely a wrong call. |
| `min_concordance_frac` | 0.7 | 70% of chimeric reads should agree on the breakpoint within the window. The ATLL cohort hit 0.94–1.00 on real integrations; 0.7 is comfortably above the noise floor. |
| `concordance_window_bp` | 10 | Reads should agree within 10 bp at the same junction. |
| `review_repeat_pct_min` | 85 | Repeat overlap is informational by default — only flag when paired with low host primary mapQ. |
| `review_host_mapq_max` | 30 | Combined with `review_repeat_pct_min`, this fires only when the host primary alignment is poor AND the host flank is repeat-dense. |
| `min_target_aligned_len_intact_bp` | 500 | Intact proviruses span the full element; supplementary aligned length should reach the LTR. |
| `min_target_aligned_len_defective_bp` | 100 | Defective proviruses (Matsuoka-style ~50% of ATLL) have partial / deleted target sequence; threshold relaxed. |

**Verdict logic:**
- FAIL: `n_chimeric_reads < 5` OR `tn_overlap_reads > 0` OR `caller_vs_chimeric_median > 1000 bp`.
- NEEDS_REVIEW (any):
  - `n_chimeric_reads < 8`
  - `caller_vs_chimeric_median > 50 bp`
  - `frac_within_window < 0.7` AND `bim_match_to_svlen != yes`
  - `host_flank_repeat_pct >= 85%` AND `host_mapq_median < 30`
  - `target_aligned_len_median < min_target_aligned_len_<class>_bp`
- PASS: otherwise.

---

## gene_fusion

Use for: BCR-ABL, RUNX1-RUNX1T1, IGH translocations, any fusion involving
two host coding regions joined at exon boundaries.

| Threshold | Value | Rationale |
|---|---|---|
| `min_chimeric_reads_pass` | 5 | Fusion VAFs are often subclonal; fewer reads expected than viral integrations. |
| `min_chimeric_reads_fail` | 3 | Below this is below detection limit. |
| `max_caller_vs_consensus_pass_bp` | 50 | Exon boundaries are tight. |
| `max_caller_vs_consensus_fail_bp` | 500 | A fusion call >500 bp from the chimeric consensus is on the wrong intron, possibly the wrong gene. |
| `min_concordance_frac` | 0.8 | Tighter than viral — fusion breakpoints are at exon boundaries, not noisy LTR-host junctions. |
| `concordance_window_bp` | 10 | |
| `review_repeat_pct_min` | 100 | Effectively never flag repeats — fusions hit clean coding regions; if the breakpoint is in a repeat, the upstream caller should have rejected it. |
| `review_host_mapq_max` | 0 | (Disabled, paired with `review_repeat_pct_min=100`.) |
| `min_target_aligned_len_intact_bp` | 100 | Partner-side read can be short — fusion partners are typically validated by the host-side breakpoint and the partner gene identity. |
| `min_target_aligned_len_defective_bp` | 50 | |

**Notes for fusion validation:**
- This skill validates DNA-level breakpoints. For RNA-level fusion validation (read-through transcripts vs DNA fusions), use Arriba's discarded-call analysis or STAR-Fusion's `FFPM` filter.
- For fusions where both partner ends sit in repetitive elements (LINE/SINE-rich), consider the `mobile_element` rubric instead.

---

## mobile_element

Use for: L1 (LINE-1), Alu, SVA, ERV, retrotransposon insertions.

| Threshold | Value | Rationale |
|---|---|---|
| `min_chimeric_reads_pass` | 5 | MEIs can be heterozygous in normal too; tumor-side counts can be modest. |
| `min_chimeric_reads_fail` | 3 | |
| `max_caller_vs_consensus_pass_bp` | 100 | MEI breakpoints are noisier than viral or fusion — TSD ambiguity, polyA tails, internal priming all introduce a few bp of slop. |
| `max_caller_vs_consensus_fail_bp` | 1000 | |
| `min_concordance_frac` | 0.6 | Looser than viral — TSD-induced clipping side ambiguity is common. |
| `concordance_window_bp` | 20 | Wider window for the same reason. |
| `review_repeat_pct_min` | 100 | Never flag repeats — repeats ARE the biology. RT-mediated integration prefers AT-rich. |
| `review_host_mapq_max` | 0 | (Disabled.) |
| `min_target_aligned_len_intact_bp` | 100 | Many MEIs are 5'-truncated; full-length L1 is the exception. |
| `min_target_aligned_len_defective_bp` | 50 | |

**Notes for mobile element validation:**
- Set SVLEN in the calls TSV to the actual element length (≈ 300 for Alu, ≈ 6000 for L1, ≈ 2000 for SVA), NOT including the TSD.
- For population-polymorphic MEIs (e.g., Alu insertions in the 1000G panel), expect non-zero T/N overlap. The default rubric still flags these as fail — relax the T/N criterion if you're explicitly validating polymorphic MEIs.

---

## generic_sv

Use for: de novo SV calls in non-special regions where neither viral
integration biology nor mobile element biology nor fusion biology
applies.

| Threshold | Value | Rationale |
|---|---|---|
| `min_chimeric_reads_pass` | 10 | Strict — generic SVs in clean regions should have plenty of evidence. |
| `min_chimeric_reads_fail` | 5 | |
| `max_caller_vs_consensus_pass_bp` | 30 | Tight — modern callers refine breakpoints to ±5 bp in clean regions. |
| `max_caller_vs_consensus_fail_bp` | 500 | |
| `min_concordance_frac` | 0.8 | Tight — generic SVs in clean regions should have nearly all reads agreeing. |
| `concordance_window_bp` | 10 | |
| `review_repeat_pct_min` | 50 | Repeat overlap is a real concern in generic SV calling — flag it. |
| `review_host_mapq_max` | 40 | |
| `min_target_aligned_len_intact_bp` | 500 | "Target" here means the partner end of an inter-chromosomal translocation, etc. |
| `min_target_aligned_len_defective_bp` | 200 | |

This rubric is the strictest. Use it when none of the biology-specific
rubrics fit.

---

## When to add a custom rubric

If you're working on an event class that genuinely doesn't fit any of the
above (e.g., circular DNA / extrachromosomal DNA, complex chromothriptic
clusters, structural variation arising from telomere fusions), copy the
closest rubric in `scripts/compute_validation_report.py` and modify.
The `RUBRICS` dict is the single source of truth — every threshold is
named and explicitly justified there.

The two key knobs to think about:

1. **Repeat-overlap handling.** If the event biology favors repeat-rich
   sites, set `review_repeat_pct_min=100` (effectively disabling the
   flag). If the biology actively avoids repeats, lower the threshold
   to 50 and pair with a host mapQ check.
2. **Concordance window.** Tight breakpoints (exon boundaries, tandem
   junctions) → window = 10. Looser breakpoints (TSD ambiguity, LTR
   ambiguity, complex SVs) → window = 20–50.

The other thresholds are usually fine as-is.
