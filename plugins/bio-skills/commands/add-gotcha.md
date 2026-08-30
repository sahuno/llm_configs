---
description: Record a tool failure mode from this session as a durable gotcha record
argument-hint: [tool name, or leave blank to infer from the session]
---

Capture what just broke, while the details are still cheap. **Draft this from
the current session transcript** — the moment of failure is the only time the
version, the exact error, and the fix are all in front of you. A week later
they cost an hour to reconstruct, which is why these were previously written by
hand and often not written at all.

## Where it goes

Pick the skill that owns the tool:

| Tool area | Skill |
|---|---|
| DSS, parallel R, small-n CV, `fread`, Clair3, Severus, statistics | `analysis-gotchas` |
| Snakemake + SLURM executor | `snakemake` → `references/gotchas.md` |
| IGV / igver / modkit visualisation | `igv-screenshots` → `references/gotchas.md` |
| Apptainer builds, env leaks | `singularity-build` |
| Cluster partitions, slurm-mcp, benchmarking, local LLM serving | `mskcc-hpc` (hpc-site plugin) |

If none fits, add a new `references/` file to the closest skill rather than
inventing a skill for one record.

## Write all three places

A record that only lands in one place is invisible. Do every step:

**1. The reference file** — `<skill>/references/<tool>.md`, with frontmatter:

```yaml
---
tool: <name as invoked>
version_observed: "<exact version, or 'unrecorded' if truly unknown>"
date: <YYYY-MM-DD the failure was confirmed>
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  <one command that returns differently when the bug is present>
---
```

Then the body: **symptom** (what the user sees, including that it may look like
success), **cause** (mechanism, precisely — down to the function or flag),
**fix** (the exact invocation), **verification** (how to confirm the fix took).

Record the version even when it feels obvious. An entry without one cannot be
checked against an upstream release, and `gotcha_audit.py` will flag it.

**2. The owning SKILL.md routing table** — add a row so the skill knows when to
reach for the new file. Without this the record exists but never loads.

**3. The skill's `description` frontmatter** — only if the new record introduces
a trigger the description does not already cover. Keep the description
*categorical* ("silent failure modes; consult before trusting any long job that
exited 0"), not an enumeration of tool names — an enumerated list is the trigger
mechanism and it stops working past roughly 50 entries.

## The bar

**A gotcha without a detection command is an opinion.** If you cannot write a
command that behaves differently when the bug is present, the record is not
finished — say so rather than filing it. `detect_cmd` may be empty only for a
process rule with nothing to probe.

Prefer failure modes that are *silent*: the job exits 0, writes output, and is
wrong. Those are what this collection is for. A tool that crashes loudly does
not need a record; the error message is the record.

## After writing

Run `python3 "${CLAUDE_PLUGIN_ROOT}/../../tools/gotcha_audit.py"` to confirm the
frontmatter is complete, and report the new record's path.
