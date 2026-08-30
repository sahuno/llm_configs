# Overlap between Claude Science skills and this repo

**Date:** 2026-08-29
**Scope:** the three hand-authored skills in `science-skills/` against their
counterparts in `plugins/`, `tools/` and `claude/CLAUDE.md`.

Two products, one author, same instincts — so the risk is not that the ideas
differ, it is that they drift apart without anyone deciding they should. Every
claim below cites a file and line so it can be checked rather than believed.

**Summary:** one genuine conflict (now fixed), one real gap the science skill
exposes in this repo (now partly fixed), one clean complement needing only a
pointer.

---

## A. `artifact-provenance-audit` ↔ the `repro-auditor` agent

**Verdict: complementary. Do not merge. One seam worth closing.**

Both ask "could this be rerun". They answer different fractions of it, and one
of them does its fraction far better.

| | `artifact-provenance-audit` (science) | `repro-auditor` (this repo) |
|---|---|---|
| Method | Mechanical — scans source for write-calls vs read-calls, matches artifacts to producers | Prompt — an agent reads the repo and reports |
| Tooling | 7 helpers in `kernel.py`: `scan_producers`, `discover_io_helpers`, `match_artifacts_to_producers`, `lineage_producers`, `diff_against_saved`, `stage_script_artifacts`, `source_lines` | none |
| Covers | One question deeply: does every saved artifact have a runnable producer | Six areas: entry point, input resolution, environment pinning, determinism, tracing numbers, doc-vs-code drift |
| Assumes | An artifact store with lineage records, and a live kernel | A git repo and a cluster |

**Where they touch.** `repro-auditor.md:30` — area 5, "The numbers" — says:

> Pick two or three specific figures from the README, docs, or manuscript and try
> to trace each back to the script and output file that produced it.

That is `artifact-provenance-audit` Step 2–4, done by hand and by sampling.
The science skill does it exhaustively and mechanically.

**Why not merge them.** The science skill depends on an artifact store with
lineage records (`lineage_producers`) and on a warm kernel; neither exists in
this repo's world. And it does not touch five of `repro-auditor`'s six areas.
Merging would either drag a dependency across products or throw away coverage.

**Action taken.** `repro-auditor` area 5 now names the mechanical technique and
adopts its vocabulary — *producer*, *orphan artifact* — so the two describe the
same object the same way. Sampling remains the fallback when no artifact store
exists.

**To verify:** `plugins/bio-skills/agents/repro-auditor.md`, area 5.

---

## B. `pinned-reference-snapshot` ↔ `tools/gotcha_audit.py`

**Verdict: same discipline, different objects — and it exposes a real gap here.**

Both enforce one rule: *record the version, or the thing changes underneath you
and nothing tells you.*

- `gotcha_audit.py` enforces it on **tool-behaviour observations** — every
  incident record must carry `version_observed`, and the audit flags the 7 of 15
  that never captured one.
- `pinned-reference-snapshot` enforces it on **reference data** — vendor the
  resource, checksum it, verify at load, and write a change ledger when the pin
  moves.

These are not duplicates. They are the same idea applied to the two kinds of
thing an analysis depends on.

### The gap it exposes

`plugins/hpc-site/profiles/sites/mskcc-greenbaum/databases.yaml` is the genome
registry every skill reads reference paths from. It points at **8 distinct
versioned resources**:

```
gencode.v19   gencode.v47   gencode.vM25   gencode.vM37
rmsk405       RepLibrary20140131            v2.0 (T2T)    v5.2 (Liftoff)
```

and records **zero version fields and zero checksums**. Every version exists
only inside a filename.

That is exactly the failure `pinned-reference-snapshot` was written to prevent.
A path can be repointed, a symlink moved, a file regenerated in place under the
same name — and no analysis reading that registry would notice. The failure mode
matches the ones already catalogued in `analysis-gotchas`: silent, plausible,
and only visible when numbers move between reruns of unchanged code.

**Action taken.** `version:` fields added to the registry where the version is
derivable from the path, plus a `checksum:` slot and a header stating the rule.

**Not done — needs the cluster.** Checksums cannot be computed here; the files
are on `/data1`. Until they are filled, the registry records *which* release is
meant but cannot detect a file changing under a fixed name. Filling them is one
pass of `sha256sum` on the HPC, and `pinned-reference-snapshot`'s
`sha256_file` / `write_pin_manifest` / `verify_pin` helpers already implement
exactly this pattern — worth reusing rather than reinventing.

**To verify:** `plugins/hpc-site/profiles/sites/mskcc-greenbaum/databases.yaml`
header and `version:` fields; `science-skills/pinned-reference-snapshot/SKILL.md`
Steps 1–2.

---

## C. `lab-figure-format` ↔ `CLAUDE.md` §7 and the `figure-editor` agent

**Verdict: a genuine conflict, and this repo was the one that was wrong.**

Three authorities disagreed about the point size of text in a final manuscript
figure at single-column width:

| Source | Says | Reference |
|---|---|---|
| `figure-editor` agent | **5–8 pt**, lettering ≈ 2 mm | `plugins/bio-skills/agents/figure-editor.md:10` |
| `CLAUDE.md` §7 | **5–7 pt** | `claude/CLAUDE.md` §7 and the Nature block |
| `lab-figure-format` | **8 pt** single-panel, 7 pt legend, 6 pt ticks | `science-skills/lab-figure-format/SKILL.md`, `operon_arial.mplstyle` |

They agree on column width — `lab-figure-format` says 3.50 in, §7 says 90 mm;
3.50 in = 88.9 mm. Not a conflict.

**The conflict is mine.** PR #5 fixed a real contradiction (§7 previously
demanded 20 pt at final size, which is ~3.5× too large on a 90 mm column) and
cited the `figure-editor` agent as the authority. But it wrote **5–7 pt** while
the agent says **5–8 pt** — narrowing the range while claiming to defer to it,
and in the process excluding the 8 pt that the lab house style actually uses.

**Action taken.** `CLAUDE.md` §7 now says 5–8 pt, matching the agent, and names
`lab-figure-format`'s ladder as the lab's specific choice within that range —
which is what it is, not a competing claim.

**To verify:** `claude/CLAUDE.md` §7 and its Nature block; compare against
`figure-editor.md:10`.

---

## Keeping these aligned

There is no mechanism that would have caught any of this — the two products
share an author and nothing else. Three options, in increasing cost:

1. **Re-run this audit when either side changes a shared concept.** Cheapest,
   and depends entirely on remembering.
2. **Cross-reference explicitly**, as done for A and C, so a reader of one is
   told the other exists. Done.
3. **Extract the shared vocabulary** — *producer*, *orphan artifact*, *pin*,
   *version_observed* — into one glossary both cite. Worth doing only if a
   fourth overlap appears; two data points is not a pattern.

The narrower lesson is the useful one: **the conflict was not between products,
it was introduced by a fix.** #5 corrected a real error and created a smaller one
by tightening a range it had no reason to tighten. Worth remembering when the
next contradiction gets resolved by picking a number.
