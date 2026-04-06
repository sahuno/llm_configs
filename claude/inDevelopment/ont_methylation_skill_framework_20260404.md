# ONT Methylation Skill — Framework & Brainstorm
Date: 2026-04-04
Status: Pre-design — not yet implemented

Reference skill for structure: `claude/skills/snakemake/`
Skill-creator spec: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`

---

## What this skill enables Claude to do

Guide and execute any stage of the ONT methylation pipeline:
pod5 → basecall → align → pileup → DMR calling

This is our most common and complex wetlab-to-insight workflow. It has more silent
failure modes (chemistry mismatch, ref mismatch, multi-run merge order) than any
other pipeline we run. A skill should prevent all of them.

---

## Top 10 Items to Include

### 1. Canonical Pipeline Chain with Tool Versions

The single most referenced thing in any ONT session. Needs to be:
- The full sequence from pod5 to DMR
- Each step's input → output format
- Which container provides each tool

```
pod5
  └─ dorado basecall       → unaligned BAM (uBAM)
       └─ dorado align      → aligned BAM (sorted + indexed)
            └─ modkit pileup → bedMethyl per sample
                 └─ modkit dmr → DMR BED with statistics
```

**Why it matters**: Claude often jumps to suggesting bwa/minimap2 for alignment
or medaka for methylation. The chain above is our specific, validated stack.
Getting this right in the skill prevents constant correction.

**Where in skill**: SKILL.md body — the chain is consulted every time.

---

### 2. Chemistry Detection Protocol

ONT runs can mix 4kHz and 5kHz chemistries. A mismatch between chemistry and
dorado model produces silently wrong methylation calls — no error, just garbage.

This item should include:
- How to detect chemistry from pod5 metadata (`dorado summary` or pod5 inspect)
- The decision tree: 4kHz → which model family, 5kHz → which model family
- What to do when a run has mixed chemistries (split before basecalling)
- The rule: **never concatenate pod5 files across chemistries**

**Why it matters**: This is the most catastrophic silent failure mode in ONT work.
It should be the first thing Claude checks when a user describes an ONT dataset.

**Where in skill**: SKILL.md body (critical path item, not a reference).

---

### 3. Dorado Model Selection Guide

The model must match chemistry + flowcell + modification type. This is a lookup
table problem, not an inference problem — Claude should not guess.

This item should include:
- Model naming convention (`dna_r10.4.1_e8.2_400bps_sup@v4.3.0`)
- Which model for which flowcell (R9 vs R10, PromethION vs MinION)
- Our standard modification string: `5mCG_5hmCG@latest,6mA@latest`
- Where to find available models (`dorado download --list`)
- Confirmation step: always verify model with user before basecalling

**Why it matters**: Wrong model = wrong calls. No amount of downstream QC
catches this. Must be confirmed, not assumed.

**Where in skill**: `references/dorado_models.md` — a lookup table loaded
when the user asks about basecalling or model selection.

---

### 4. QC Checkpoint Thresholds (Per Stage)

Our CLAUDE.md mentions QC checkpoints but without specifics. This item is the
quantitative definition of "pass" at each stage:

| Stage | Metric | Pass Threshold | Action if Fail |
|-------|--------|----------------|----------------|
| Basecall | Read N50 | Depends on chemistry; flag if <5kb | Check chemistry match, pod5 integrity |
| Basecall | Pass rate | >80% | Investigate flow cell quality |
| Alignment | Mapping rate | >80% | Check ref genome vs chemistry |
| Alignment | Supplementary rate | <10% | Flag structural variation |
| modkit pileup | Coverage median | >10x per CpG | Flag low-coverage samples |
| modkit pileup | Chromosomes present | All expected | Check --cpg flag, ref match |
| DMR calling | DMR count | 10–100k | Sanity check thresholds |

This item also defines what "stop and report" means: generate a QC summary
markdown, paste it to the user, wait for instruction before continuing.

**Where in skill**: `references/qc_thresholds.md` + a bundled script.

---

### 5. Bundled Script: `check_ont_run.sh`

A single pre-flight script that:
1. Inspects pod5 files to detect chemistry
2. Confirms the correct dorado model is available
3. Verifies the reference genome path from databases_config.yaml
4. Reports: sample count, estimated data volume, expected runtime

Running this before any basecalling catches 80% of silent failure setups.

**Why bundle it**: Every ONT session starts with this same discovery work.
Without a script, Claude generates ad-hoc shell one-liners that vary per session.
A fixed script creates consistent, auditable pre-flight output.

**Where in skill**: `scripts/check_ont_run.sh`

---

### 6. Multi-Run Sample Handling Protocol

Some patients have multiple sequencing runs (flow cells). The merge order matters
and the wrong order creates artifacts:

- **Never** concatenate pod5 files across runs
- Basecall each run independently with its own dorado command
- Align each run independently
- Merge at the BAM level with `samtools merge` after sorting
- Keep a manifest: `run → BAM path → merged BAM path`
- Verify merged BAM coverage vs sum of individual BAMs

This is counter-intuitive (concatenating pod5 seems equivalent) but the
basecall model's context window spans read boundaries within a pod5 batch.

**Where in skill**: SKILL.md body — this is a guardrail, not reference content.

---

### 7. modkit Configuration Reference

modkit has many flags and the wrong combination produces valid-looking but wrong
output. This item is the canonical reference for our use case:

```bash
# Standard pileup command
modkit pileup \
  --ref {reference_fasta} \         # must match alignment reference EXACTLY
  --cpg \                           # CpG-only mode (our standard)
  --combine-strands \               # combine +/- strand for CpG
  --threads {threads} \
  --log-filepath {log} \
  {input_bam} {output_bedmethyl}
```

Key pitfalls:
- `--ref` must match the alignment reference exactly (same FASTA, same version)
- Omitting `--cpg` gives per-base output that's not compatible with downstream DMR tools
- `--combine-strands` is required for modkit dmr compatibility

**Where in skill**: `references/modkit_config.md`

---

### 8. DMR Calling Configuration (modkit dmr)

The step that produces the biological result — but also the step with the most
tunable parameters that change interpretation:

```bash
modkit dmr pair \
  --ref {reference_fasta} \
  --a-hemi {case_bedmethyl_list} \      # or --a for pooled
  --b-hemi {control_bedmethyl_list} \  # or --b for pooled
  --out-dir {dmr_output_dir} \
  --cpg \
  --min-valid-coverage {coverage} \    # default 5; increase for confidence
  --threads {threads}
```

This item includes:
- When to use `pair` vs `all` subcommand
- Coverage threshold guidance (5x minimum, 10x recommended)
- How to interpret the output columns (score, N_mod, N_diff, etc.)
- Post-DMR annotation: intersect with CpG islands, gene bodies, repeat elements

**Where in skill**: `references/modkit_dmr.md`

---

### 9. SLURM Resource Templates Per Step

Each step has a predictable resource profile. Having these as copy-paste templates
prevents Claude from guessing (and under-estimating for basecalling, over-estimating for pileup):

| Step | CPUs | Memory | GPU | Time |
|------|------|--------|-----|------|
| dorado basecall | 4 | 16G | 1x A100 required | ~1h per 10Gb pod5 |
| dorado align | 8 | 32G | No | ~30min per 10M reads |
| samtools sort/merge | 4 | 16G | No | ~15min per sample |
| modkit pileup | 8 | 16G | No | ~1h per sample |
| modkit dmr | 4 | 16G | No | ~30min per group comparison |

**Where in skill**: `references/slurm_resources.md`
(same format as §6 Environment Reference in CLAUDE.md, but ONT-specific and detailed)

---

### 10. "Done" Definition — Output Manifest Spec

The clearest sign of a mature pipeline is knowing exactly what "done" means.
This item defines the complete output of a successful ONT methylation run:

```
results/{date}_{genome}_{description}/
├── bedmethyl/
│   └── {sample}.{genome}.bedmethyl.gz         # per-sample, bgzipped + tabix
│       {sample}.{genome}.bedmethyl.gz.tbi
├── dmrs/
│   └── {comparison}.{genome}.dmrs.bed         # genome-tagged, header-prefixed
├── qc/
│   ├── basecall_summary.tsv                   # dorado summary output
│   ├── alignment_flagstat.tsv                 # per-sample flagstat
│   └── coverage_summary.tsv                  # modkit coverage per sample
├── figures/{png,pdf,svg}/
│   ├── methylation_distributions.png
│   └── dmr_summary.png
├── manifest.csv                               # sample → BAM → bedmethyl → DMR
└── run_metadata.yaml                          # date, genome, containers used
```

**Why it matters**: Without a "done" definition, Claude declares victory after
modkit pileup, leaving DMR calling, QC figures, and the manifest as afterthoughts.

**Where in skill**: SKILL.md body — checked at task completion.

---

## Proposed Skill Directory Structure

```
ont-methylation/
├── SKILL.md                          # Pipeline chain, chemistry detection,
│                                     # multi-run protocol, done definition
├── scripts/
│   ├── check_ont_run.sh              # Pre-flight: chemistry, model, ref validation
│   ├── validate_bedmethyl.sh         # Post-pileup QC: check chromosomes, coverage
│   └── summarize_qc.py               # Aggregate QC stats across samples → TSV
├── references/
│   ├── dorado_models.md              # Model selection lookup table
│   ├── modkit_config.md              # pileup + dmr command reference
│   ├── modkit_dmr.md                 # DMR calling guide + output interpretation
│   ├── qc_thresholds.md             # Numeric pass/fail thresholds per stage
│   └── slurm_resources.md           # Per-step SLURM resource templates
└── evals/
    └── evals.json                    # Test prompts for skill-creator eval loop
```

---

## What Goes in SKILL.md Body vs References

The skill-creator spec says SKILL.md should be <500 lines and use progressive
disclosure — references are loaded only when needed.

| Content | Location | Why |
|---------|----------|-----|
| Pipeline chain (10 lines) | SKILL.md body | Consulted every session |
| Chemistry detection protocol | SKILL.md body | Critical path — must not miss |
| Multi-run protocol | SKILL.md body | Guardrail — must always apply |
| "Done" definition | SKILL.md body | Completion check — must be in context |
| Dorado model table | `references/dorado_models.md` | Load only at basecalling stage |
| modkit pileup command | `references/modkit_config.md` | Load at pileup stage |
| modkit dmr guide | `references/modkit_dmr.md` | Load at DMR stage |
| QC thresholds | `references/qc_thresholds.md` | Load at each QC checkpoint |
| SLURM resources | `references/slurm_resources.md` | Load when writing job scripts |

---

## Trigger Conditions (for SKILL.md frontmatter description)

The skill should auto-trigger on:
- "ONT methylation", "ONT methyl", "nanopore methylation"
- "dorado basecall", "dorado align", "modkit pileup", "modkit dmr"
- "pod5", "bedMethyl", "5mCG", "CpG methylation from nanopore"
- "DMR calling", "differential methylation" (when context suggests ONT)
- "basecalling", "alignment" when prior context mentions pod5 or dorado
- Any mention of chemistry mismatch, 4kHz, 5kHz in an ONT context

Should NOT trigger on:
- Bisulfite methylation (WGBS, RRBS) — different pipeline entirely
- ONT variant calling without methylation
- Generic DMR calling from bisulfite data

---

## Open Design Questions

1. **Snakemake integration**: Should the skill produce standalone shell scripts
   or Snakemake rules? The snakemake skill already exists — maybe ont-methylation
   generates the pipeline structure, then hands off to snakemake skill for
   SLURM submission. Handoff point to define.

2. **Container references**: Should the skill read from
   `profiles/software_configs/softwares_containers_config.yaml` directly
   (via a script), or embed the container paths in references/? Embedded paths
   get stale; reading from config is always current.

3. **check_ont_run.sh scope**: Should the pre-flight script also validate the
   sample sheet format? Or keep it focused on pod5/chemistry/model only?
   Broader = more useful but more failure surface.

4. **Bisulfite fallback**: Should we include a one-section note on how to hand
   off to a different workflow when the user has WGBS instead of ONT data?
   Prevents the skill from silently applying ONT logic to the wrong data type.
