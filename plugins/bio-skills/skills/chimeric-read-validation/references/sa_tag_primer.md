# SA tag primer — chimeric-read parsing

This document explains how to parse SA (Supplementary Alignment) tags
correctly for chimeric-read validation, why it matters, and the failure
modes the skill is built to avoid.

---

## What is an SA tag?

When a read maps to two (or more) places in the reference — its primary
alignment + one or more chimeric/supplementary alignments — minimap2 (and
bwa-mem) write the chimeric mappings into an `SA:Z:` auxiliary tag on the
**primary** record.

Format:

```
SA:Z:rname,pos,strand,CIGAR,mapQ,NM;rname,pos,strand,CIGAR,mapQ,NM;...
```

Each semicolon-separated entry is one supplementary mapping. Fields are
comma-separated within an entry, in this fixed order:

1. `rname` — reference name (contig)
2. `pos` — 1-based reference position
3. `strand` — `+` or `-`
4. `CIGAR` — alignment CIGAR
5. `mapQ` — mapping quality
6. `NM` — edit distance

For chimeric-read validation, the primary record sits on the host genome
and at least one SA entry sits on the target contig (HTLV1, EBV,
fusion-partner gene region, mobile element, etc.).

---

## How the skill uses it

For each candidate breakpoint at `host_chrom:host_pos`, the extract
script does:

```
samtools view <bam> host_chrom:(host_pos-1000)-(host_pos+1000)
```

For each line returned, it:

1. **Filters to primary alignments only** (skip flag bits `0x100`
   secondary, `0x800` supplementary). The supplementary records are the
   *partner* ends of the same chimeras and would double-count if not
   filtered.
2. **Parses the SA tag.** If no SA tag, the read isn't chimeric — skip.
3. **Filters SA entries to the target contig.** The skill is interested
   in reads where the supplementary mapping sits on the target — viral
   contig, fusion partner, mobile element consensus.
4. **Computes the inferred host breakpoint** from the primary alignment's
   CIGAR + soft-clip lengths. The breakpoint sits at the soft-clip
   boundary; pick whichever clip is larger.
5. **Reports the largest target-contig SA hit** (by reference-bases
   consumed) — this is the most informative supplementary alignment.

---

## Why `samtools view -f 0x800` (supplementary-only) is the wrong query

A natural-looking but **wrong** query for chimeric reads is:

```
samtools view -f 0x800 <bam> <region>
```

This returns only supplementary records. But:

1. Supplementary records are the *partner* end of a chimera. If the
   primary is on the host and the supplementary is on the target, then
   `samtools view -f 0x800 <region>` filtered to the host region returns
   only the supplementary records that happen to also fall in the host
   region — usually zero or near-zero.
2. The supplementary records on the *target* contig are what you'd want
   if you queried the target region — but those don't carry the host
   breakpoint position you need.

The correct query is: **primary records on the host region whose SA tag
points to the target contig**. That's what the extract script does.

---

## Why `minimap2 -Y` matters

Without the `-Y` flag, minimap2 emits supplementary alignments as
**hard-clipped** rather than soft-clipped. This affects the SA tag in two
ways:

1. The CIGAR in the SA tag uses `H` (hard-clip) instead of `S`
   (soft-clip). Length-consuming behavior is the same for reference-side
   computation, but…
2. The supplementary record itself has no sequence. Tools that try to
   re-extract the soft-clipped portion of the chimera's host primary
   alignment from the supplementary record (instead of from the primary
   record) get nothing.

For this skill it doesn't matter much — we read the soft-clip length from
the **primary** record's CIGAR, not the supplementary. But many downstream
tools (visualization, polishing, re-alignment) assume `-Y`. The skill's
preflight check warns when the BAM `@PG` line shows minimap2 was run
without `-Y`.

To check at any time:

```
samtools view -H <bam> | grep '@PG.*minimap2'
```

You should see `-Y` in the command line that produced the BAM. If you
don't, the BAM is still usable for breakpoint extraction but you may run
into trouble with downstream consumers.

---

## Soft-clip semantics — picking the right end

For each chimeric primary alignment, the host breakpoint sits at the
soft-clip boundary. The CIGAR has the form:

```
S{left_clip}M{...}S{right_clip}
```

Either or both `S` operations may be absent. The skill's heuristic:

```
if right_clip >= left_clip:
    breakpoint = pos + ref_bases_consumed - 1
else:
    breakpoint = pos
```

That is, "pick whichever clip is larger" — the larger clip is the part
of the read that maps to the partner contig, so the breakpoint is at the
boundary on that side.

**Failure mode.** When both clips are near-equal, the heuristic can pick
the wrong end. This produces a few-bp error per read and shifts the
inferred breakpoint median.

**Fix.** The validation script's bimodality check splits chimeric reads
by which clip side is dominant, and reports cluster medians from each
side separately. When the two cluster medians are separated by ~SVLEN
(within 50 bp or 10% of SVLEN), the call is bimodal-matching and passes
review even when the global concordance fraction looks poor.

---

## Worked example (one ATLL chimeric read)

Take a read from p17424_1's chr9:34913979 integration:

```
read_name = abc123
flag = 0      (primary, forward strand)
rname = chr9
pos = 34913720
mapq = 60
cigar = 269S5731M
SA = HTLV1,1,+,5731H6300S,60,12;
```

Parsed:

- `left_clip = 269 bp, right_clip = 0 bp` — left clip dominant.
- `ref_consumed by 269S5731M` = 5731 bp (only `M` consumes reference).
- Heuristic: `right_clip < left_clip` → `breakpoint = pos = 34913720`?
  Actually no — the inferred breakpoint here is `pos + ref_consumed - 1
  = 34913720 + 5731 - 1 = 34919450`. But the chimeric-read median in
  the ATLL run was 34913988.
  - This particular toy example shows the danger: a single read with
    the larger clip on the LEFT looks like its breakpoint is at the
    LEFT boundary (`pos`), but the heuristic also depends on whether
    `right_clip >= left_clip` (it isn't here, so we'd return `pos =
    34913720`, NOT `pos + ref_consumed - 1`). The actual ATLL chr9
    integration consensus position 34913988 came from reads with
    different clip patterns; the example is illustrative, not literal.
- The HTLV1 SA entry: starts at HTLV1:1 with CIGAR `5731H6300S` — so
  this read has 5731 bases hard-clipped on the HTLV1 side (the host-side
  M's), then 6300 bases soft-clipped on the HTLV1 side. Wait — that's
  6300 bases of soft-clip on the HTLV1 side, but the HTLV1 contig is
  only 8507 bp. Most likely this is an artifact of the toy CIGAR; in a
  real run the HTLV1 supplementary CIGAR would have a meaningful M run
  representing the integrated proviral sequence the read covers.

The point of the worked example is to illustrate the structure, not to
reproduce a literal ATLL row. Look at
`results/<run>/data/per_integration/<event_id>.chimeric_reads.tumor.tsv`
for real values.

---

## Checking your understanding

If your validation report has all calls failing with "<5 chimeric reads"
but you expected the calls to validate, possible explanations in order
of likelihood:

1. **Wrong target contig.** The contig name in the BAM header
   doesn't exactly match what you passed to `--target-contig`. Run
   `samtools view -H <bam> | grep @SQ | grep -i <approximate_name>` to
   find the exact contig name. The extract script's preflight should
   catch this and fail fast.
2. **No `-Y` flag in alignment.** If supplementary CIGARs are
   hard-clipped instead of soft-clipped, the SA tag is still parseable
   but downstream tools may misbehave. Check `@PG` for `-Y`.
3. **Window too small.** The `--flanking-bp` default is 1000. If the
   caller's reported `host_pos` is more than 1 kb from the actual
   chimeric-read consensus, increase the flanking window.
4. **Stale `.bai` index.** `samtools view region` silently returns wrong
   reads. Re-index with `samtools index <bam>`. The extract script
   warns when `.bai` mtime is older than `.bam` mtime.
