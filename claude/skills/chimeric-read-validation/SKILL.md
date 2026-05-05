---
name: chimeric-read-validation
description: Verify that structural-variant / breakpoint calls are actually real by checking the chimeric reads that support them. Use whenever the user has caller output (Severus, Manta, Sniffles2, Delly, GRIDSS, MELT, Arriba, SvABA) and wants to validate / audit / QC / double-check their calls — viral integrations (HTLV-1, HBV, HPV, EBV), gene fusions (BCR-ABL, IGH translocations), mobile element insertions (L1, Alu, SVA), translocations. Trigger on phrasings like "is this integration real?", "should I trust this fusion call?", "are these false positives?", "are these PASS calls actually supported by reads?", "QC my SV calls", or any per-call chimeric-read / contamination / bimodality / T-vs-N read overlap question. Also fires on BAM @PG -Y / SA-tag questions on chimeric BAMs, and on /chimeric-read-validation. Output: per-call TSV with pass / needs_review / fail verdicts. NOT for: calling SVs (use the caller), IGV screenshots (use igv-reports), RNA-level fusion FDR (use Arriba).
---

# Chimeric-read validation

## What this skill does

Caller PASS is necessary but not sufficient. PASS means the caller's internal heuristics fired correctly; it doesn't say whether the supporting reads actually agree with the called breakpoint at the read level. For breakpoint-style events the only ground truth is the chimeric reads themselves.

This skill takes a candidate breakpoint table + the BAMs and answers four questions per call:

1. How many tumor-side chimeric reads support the breakpoint?
2. Do they agree on the host breakpoint position (median, MAD, fraction within ±10 bp)?
3. What fraction of those reads (by name) also appear in the matched normal? (per-call contamination check)
4. Are the host primary mapQ and target supplementary mapQ acceptable?

Output is a per-call TSV with a verdict (`pass` / `needs_review` / `fail`) and explicit reasons, ready to drop into a manuscript Methods section as Supplementary Table.

The reference run on the ATLL HTLV-1 cohort (May 2026) classified 9/9 integrations as PASS with no false positives — but the skill's job is to catch them when they appear. The work pattern matters even when zero fire on a particular cohort.

## Three capabilities

### 1. `extract` — per-call chimeric-read extraction

Given a breakpoint table + tumor BAM (± normal BAM) + target contig name, write per-call chimeric-read TSVs with:
- read name, host primary CIGAR + mapQ, soft-clip lengths, host strand
- inferred host breakpoint position
- target supplementary mapQ + aligned length (parsed from SA tag)
- one summary row per call (counts, breakpoint median, MAD, T/N overlap)

```bash
python scripts/extract_chimeric_reads.py \
  --calls calls.tsv \
  --target-contig HTLV1 \
  --bam-dir analysis/realign \
  --output-dir results/<run>/data
```

Samplesheet mode mirrors the `igv-reports` skill pattern — calls.tsv is a TSV with columns: `event_id, patient, host_chrom, host_pos, tumor_bam, normal_bam` (normal_bam optional).

### 2. `validate` — apply the verdict rubric

Given the per-call TSVs from `extract`, compute the validation report TSV:
- chimeric-read counts (tumor, normal)
- mapQ medians (host primary, target supplementary)
- caller-vs-consensus offset (caller's reported pos vs chimeric-read median)
- breakpoint concordance (median + MAD + fraction-within-X-bp)
- bimodality split distance (the highest-leverage check — see "Why robust statistics")
- T/N read-name overlap per call
- host-flank repeat overlap (informational by default, see "Biology-aware rubrics")
- a verdict under a tunable rubric

```bash
python scripts/compute_validation_report.py \
  --per-int-dir results/<run>/data/per_integration \
  --calls calls.tsv \
  --rubric viral_integration \
  --output results/<run>/data/cohort_validation_report.tsv
```

### 3. `report` — manuscript-ready output

Render a one-page Markdown summary of the validation table for inclusion in a Methods section, plus a supplementary-table caption.

```bash
python scripts/render_supp_table_caption.py \
  --validation-tsv results/<run>/data/cohort_validation_report.tsv \
  --rubric viral_integration \
  --output results/<run>/Methods_validation.md
```

## Core working patterns

These are the patterns that justify the skill — read `references/best_practices.md` for the full rationale and worked examples.

### Robust statistics on per-read measurements, not mean+stdev

Per-read breakpoint positions, mapQ values, soft-clip lengths — anything where each read contributes one observation — should be summarized with **median + median absolute deviation (MAD) + fraction within ±X bp of the median**, NOT mean and standard deviation.

Why: stdev squares deviations, so one outlier read with a breakpoint 5,000 bp off the consensus dominates the metric and produces a false alarm. The ATLL cohort hit this exact pattern: p17424_2 chr7 had stdev = 2,867 bp (alarming) but 94% of its 18 chimeric reads sat within 10 bp of the median (clean). The integration is real; the metric was bad.

The skill encodes this rule globally — stdev never enters a verdict rubric; only median, MAD, and fraction-within-X do.

### Bimodality is the highest-leverage check

When chimeric reads cluster at TWO host positions separated by ~SVLEN bp, you're sampling both LTR-host junctions of an integration (or both ends of an inversion / large insertion). High overall stdev in this case is real biology, not an inference artifact.

The skill splits chimeric reads by dominant soft-clip side and checks whether the two cluster medians are separated by ~SVLEN. When yes, the call passes review even if the global breakpoint stdev looks alarming.

### Caller PASS + read-level forensics = two layers, both required

When a caller's matched-normal classifier rejects a call, that rejection itself is informative — it's a contamination signal, not a false-positive verdict. The skill surfaces this distinction explicitly: "rejected for contamination" ≠ "rejected for low evidence."

### Biology-aware rubrics, not generic SV thresholds

Generic SV-validation rubrics flag breakpoints in repeat-rich regions because repeats can cause mapping ambiguity. For viral integration biology, this is exactly backwards: HTLV-1, HBV, retrotransposons all preferentially integrate into AT-rich / repeat-dense regions. Flagging "breakpoint sits in 90%+ repeat content" as suspicious for a viral integration miscalls 60-90% of the cohort.

The skill ships with a small library of named rubrics. Pick the one that matches your event's biology — see `references/rubrics.md`:

| Rubric | Use for | Repeat-overlap |
|---|---|---|
| `viral_integration` | HTLV-1, HBV, HPV, EBV, MCV, AAV | informational; flag only when paired with low host mapQ |
| `gene_fusion` | BCR-ABL, RUNX1-RUNX1T1, IGH translocations | informational; pairs with breakpoint-coding-exon distance |
| `mobile_element` | L1, Alu, SVA, retrotransposons | informational; expected by biology |
| `generic_sv` | de novo SV in a non-special region | flags repeat-overlap directly |

## Workflow

Recommended sequence:

1. **Preflight**: confirm BAMs were aligned with `minimap2 -Y` (or equivalent) so SA tags carry soft-clipped sequence. Check `samtools view -H <bam>` for the `@PG` line. The extract script does this preflight automatically and warns on missing `-Y`.
2. **Build the calls TSV**: one row per candidate breakpoint with `event_id, patient, host_chrom, host_pos, tumor_bam, normal_bam`. Include caller-side fields like `svlen_bp`, `provirus_class` (intact / defective), `caller_vaf` if you have them — they feed the rubric's defective-aware aligned-length thresholds and the per-patient VAF concordance metric.
3. **Run `extract`**: produces `<run>/data/per_integration/<event_id>.chimeric_reads.{tumor,normal}.tsv` and a per-call summary TSV.
4. **Run `validate`**: applies the chosen rubric and produces the verdict TSV.
5. **Run `report`**: emits Markdown ready to paste into Methods.

## Defaults

The defaults below are locked in per the design. Override only with documented reason.

| Argument | Default | Notes |
|---|---|---|
| `--target-contig` | required, no default | Skill validates the contig exists in the BAM header before extracting; fails fast on misconfiguration |
| `--flanking-bp` | 1000 | Half-window around the host position for `samtools view region` |
| `--concordance-window-bp` | 10 | The X in "fraction-within-X-bp-of-median" |
| `--rubric` | `viral_integration` | Other choices: `gene_fusion`, `mobile_element`, `generic_sv` |
| `--min-chimeric-reads-pass` | 8 | Below this, the call goes to needs_review |
| `--min-chimeric-reads-fail` | 5 | Below this, the call fails outright |
| `--max-caller-vs-consensus-pass-bp` | 50 | Caller-vs-chimeric-median offset above this triggers needs_review |
| `--max-caller-vs-consensus-fail-bp` | 1000 | Above this, the call fails |
| `--min-concordance-frac` | 0.7 | Minimum fraction-within-X-bp; bypassed when bimodality matches SVLEN |

Logs every run to `logs/run_<TS>.log` per the user's CLAUDE.md §Logging requirements.

## Gotchas the skill encodes

These are baked into the scripts. Read `references/best_practices.md` for the full table with rationale.

1. `mean` / `stdev` on per-read metrics — never used in verdict; rubric uses median + MAD + fraction-within-X
2. Soft-clip-side heuristic picks wrong end on ambiguous reads — bimodality check catches this
3. Caller VAF is per-call, not cohort-clonality — skill emits per-patient VAF concordance metric (max−min within patient) for downstream interpretation
4. `samtools view` with `-f 0x800` only catches half — skill defaults to primary-only (skip `0x100|0x800`) + SA-tag parsing; see `references/sa_tag_primer.md`
5. `minimap2 -L` vs `-Y` produces different SA tag content — skill validates SA tag schema before extraction; warns if `-Y` flag absent in BAM `@PG` header
6. T/N read-name overlap test must be PER CALL, not per sample — skill computes overlap per call, not per BAM pair
7. Hard-coding the target contig name — required `--target-contig` argument; skill validates the contig exists in the BAM header
8. mosdepth summary file naming convention — accepts `--mosdepth-summary <pattern>` with `{patient}` substitution; falls back to running mosdepth if absent
9. Repeat-overlap as a verdict trigger — demoted to informational by default; only fires as a flag when paired with low host mapQ (see rubrics)
10. BAM index staleness — extract script validates `.bai` mtime ≥ `.bam` mtime as a preflight check
11. Defective-provirus aligned-length expected to be small — aligned-length thresholds are conditional on `provirus_class`; defectives get separate rubric rows

## When NOT to fire

- The user is calling SVs / fusions / integrations from scratch — that's the caller's job (Severus, Manta, Sniffles2, Arriba, MELT). This skill is the validation layer.
- The user wants visual inspection only — that's `igv-reports` or `igv-screenshots`.
- The event is a small SNV/indel — chimeric-read forensics doesn't apply; use VAF + read support directly from the VCF.

## Reference materials

Read these as needed; they are not loaded into context by default.

- `references/best_practices.md` — full rationale for the working patterns + extended gotcha table + per-event-type rubric guidance
- `references/rubrics.md` — the named rubrics with thresholds + rationale per event biology
- `references/sa_tag_primer.md` — how to parse SA tags, soft-clip semantics, why `-Y` matters

## Examples

- `examples/htlv1_cohort_validation.sh` — full reproduction of the ATLL HTLV-1 cohort run
- `examples/fusion_call_validation.sh` — pattern for BCR-ABL / IGH translocation validation
- `examples/mobile_element_validation.sh` — pattern for L1/Alu insertion validation

## Related work

- Reference implementation that demonstrated the patterns: `/data1/greenbab/projects/ont/Project_17424/results/20260503_hg38plusHTLV1EBV_cohort_chimeric_read_evidence/`. The 9/9 PASS verdict on the ATLL cohort is the proof-of-concept — see `data/cohort_validation_report.tsv` in that run.
- Companion skills: `nfcore-module` (when the user wants to wrap chimeric-read validation as an nf-core module), `igv-reports` (visual inspection layer for spot-checks), `severus` rules in `~/.claude/rules/severus.md` (caller-side gotchas that explain why validation is needed).
