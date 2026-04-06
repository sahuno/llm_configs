# CLAUDE.md Restructure Brainstorm
Date: 2026-04-04
Status: Draft — for review

---

## Problem Statement

`claude/CLAUDE.md` is 496 lines across 10 sections.
Claude Code **only auto-loads the first ~200 lines** of CLAUDE.md at session start.

**Current auto-loaded content (lines 1–200)**:
- §1 Session Initialization (lines 8–56, ~50 lines)
- §2 Universal Rules (lines 59–199, ~140 lines)

**Content that only loads when context expands (lines 200–496)**:
- §3 Bioinformatics Analysis Playbook (77 lines)
- §4 Software Development Playbook (44 lines)
- §5 AI Engineering Playbook (16 lines)
- §6 Environment Reference (59 lines)
- §7 Figures and Visualization (40 lines)
- §8 Statistics Defaults (9 lines)
- §9 Error Recovery (16 lines)
- §10 Quality Gates (20 lines)

**Implication**: The 300 lines below the fold are only in context when the model
needs them organically — which is actually fine for some content (domain specifics),
but bad for content that should always be consulted (quality gates, genome tagging rules).

---

## Section Classification

### Tier 1 — Always in CLAUDE.md (≤ 200 lines total)

These must remain in the main file because they govern every session:

| Section | Current Lines | Action | Rationale |
|---------|--------------|--------|-----------|
| §1 Session Initialization | 50 | Keep as-is | Session boot protocol — must run every time |
| §2 Universal Rules (core) | 140 | Trim to ~80 lines | Genome tagging, forbidden vars, naming — always applies |
| §10 Quality Gates | 20 | Collapse to checklist only | Final check before declaring done — should always be visible |

**Target for Tier 1**: ~150–160 lines (leaves buffer before the 200-line cut)

### Tier 2 — Convert to Skills (trigger on demand)

These are rich domain playbooks. They're only needed in specific contexts and are
a natural fit for the skills system (skills are loaded when the task matches):

| Section | Lines | Proposed Skill | Status |
|---------|-------|---------------|--------|
| §3A ONT Methylation Pipeline | ~30 | `ont-methylation` | New — create |
| §3B Variant Calling | ~15 | `variant-calling` | New — create |
| §3C RNA-seq / DGE | ~20 | `rnaseq-dge` | New — create |
| §3D scRNA-seq | ~15 | `scrna-seq` | New — create |
| §3E IGV Visualization | ~10 | `igv-screenshots` | **Already exists** |
| §4 Pipeline Dev (Snakemake) | ~40 | `snakemake` | **Already exists** |
| §5 AI Engineering | ~16 | `claude-api` / `ai-engineering` | Partial — `claude-api` skill exists |
| §6 Container builds | ~20 | `singularity-build` | **Already exists** |

**Key insight**: We already have skills for the biggest sections. The pattern is working —
we just need to apply it systematically to the remaining playbook sections.

### Tier 3 — Shrink to compact reference in CLAUDE.md

These sections have value as always-available reference but are over-specified today:

| Section | Current Lines | Target | Action |
|---------|--------------|--------|--------|
| §6 Environment Reference | 59 | ~15 lines | Keep only the SLURM resource table + 3 critical rules; move container build rules to singularity-build skill |
| §7 Figures and Visualization | 40 | ~10 lines | Keep only the "3 formats + Arial 20pt" rule; move ggplot2/matplotlib specifics to a `figures` skill or profiles |
| §8 Statistics Defaults | 9 | Keep | Already compact |
| §9 Error Recovery | 16 | ~8 lines | Keep only the 4-step pipeline failure protocol; domain-specific errors go in respective skills |

---

## Proposed CLAUDE.md v0.4.0 Structure

```
§1 Session Initialization           ~50 lines  (keep as-is)
§2 Universal Rules                  ~80 lines  (trim: remove prose for hook-enforced rules)
§3 Environment Reference (compact)  ~15 lines  (SLURM table + 3 rules only)
§4 Figures (compact)                ~10 lines  (3 formats + font rule only)
§5 Statistics Defaults               ~9 lines  (keep)
§6 Error Recovery (compact)          ~8 lines  (pipeline 4-step protocol only)
§7 Quality Gates                    ~20 lines  (keep — needs to be always visible)
§8 Skills Index                      ~15 lines  (NEW — list of available skills and when to invoke)
─────────────────────────────────────────────
TOTAL                               ~207 lines  ← target ≤ 200 after pruning
```

### New §8 Skills Index (proposed)

This is the key addition — a lookup table that makes the skills system discoverable
without Claude needing to infer when to use them:

```markdown
## 8. Skills Index — Domain Playbooks

Invoke with: /skill-name or use the Skill tool.

| Skill | Trigger Conditions |
|-------|--------------------|
| `snakemake` | Writing/debugging Snakemake rules, SLURM profiles, executor config |
| `singularity-build` | Building Apptainer/Singularity .sif images on MSKCC HPC |
| `igv-screenshots` | Batch IGV screenshots with igver |
| `ont-methylation` | ONT basecalling → alignment → modkit pileup → DMR calling |
| `rnaseq-dge` | fastp → STAR → featureCounts → DESeq2/pyDESeq2 |
| `scrna-seq` | CellRanger → Seurat/Scanpy QC → clustering → annotation |
| `variant-calling` | Clair3 (ONT SNV/SV) or GATK HaplotypeCaller (short-read) |
| `figures` | matplotlib/ggplot2 defaults, Nature figure specs, colorblind palettes |
```

---

## What to Build Next

### Priority 1 — Trim §2 Universal Rules
The biggest single win. Current §2 is ~140 lines because it over-specifies rules
that hooks already enforce. After hook annotations in v0.3.0, we can go further:
- Remove the 7-item hook-enforced list body text, replace with one-liners
- Target: ~80 lines for §2

### Priority 2 — New `ont-methylation` skill
Largest unaddressed playbook. ~30 lines of specialized content that's only needed
for ONT methylation runs. Pull §3A into a proper skill with:
- Pipeline chain with QC checkpoints
- Chemistry detection notes
- Container references

### Priority 3 — Merge `rnaseq-dge` + `scrna-seq` skills (or create combined)
These share common themes (QC thresholds, DEG calling). Either two small skills
or one combined `rna-analysis` skill with subcommands.

### Priority 4 — Skills Index section in CLAUDE.md
Add the lookup table above so future-Claude knows what skills exist
without needing to be told.

---

## What NOT to Extract

Some content must stay in CLAUDE.md regardless of length:

- **Session Initialization §1** — the boot protocol. If this is in a skill,
  Claude has to know to invoke the skill before it knows what session to start.
  Circular dependency.

- **Genome build tagging rules** — these apply to all file writes across every
  domain. Putting them in a skill means they only apply when the skill is active.

- **Forbidden variable names** — same argument; these can bite you in any script.

- **Quality Gates §10** — the pre-completion checklist. Must be in context at
  task completion time. A skill would require explicit invocation.

---

## Open Questions

1. **Skill auto-invocation**: Today, skills require either user `/skill` commands
   or Claude Code recognizing the trigger. Should we add a UserPromptSubmit hook
   that auto-loads relevant skills based on keywords in the prompt?
   (e.g., "snakemake" in prompt → load snakemake skill context)

2. **Profile files vs skills**: Some content (matplotlib defaults, ggplot2 theme)
   lives in `profiles/programming_language_profiles/`. These are already separate
   files. Should CLAUDE.md just point to them instead of duplicating?

3. **CLAUDE.md in repo vs ~/.claude/CLAUDE.md**: They're symlinked. Any structural
   change applies to both. Document this clearly in the new §8.
