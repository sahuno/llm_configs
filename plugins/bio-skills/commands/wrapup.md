---
description: Append this session's work to the project progress file so the next session can resume without re-discovery
argument-hint: [project slug — defaults to the current project]
---

Write the session's state to `~/projects/<project>.md`. The slug comes from
`$ARGUMENTS`, else the project `CLAUDE.md`, else the directory name.

**Append, never overwrite.** Prepend a dated heading so the newest entry is
readable first, and leave earlier entries intact — the history of what was tried
and abandoned is the reason this file is worth keeping.

## The schema (CLAUDE.md §1 — all five, every time)

```markdown
## 2026-08-29

**What was done**
- Specific completed steps. Not "worked on DMRs" — "ran DSS DMLtest on 12
  samples, chr19 only, ncores bound to SLURM_CPUS_PER_TASK".

**Key file paths**
- Absolute paths to what was created or modified.

**Commands that worked**
```bash
# copy-paste ready, with the arguments actually used
```

**Known issues / blockers**
- What failed and why. An empty section here is usually a lie; if the session
  really hit nothing, say "none encountered" explicitly.

**Exact next steps**
1. Numbered, actionable, specific enough to start cold.
```

## Rules

- **Write what happened, not what was intended.** If a step was abandoned, say
  so and why — that is the most valuable line in the file.
- **Unverified results are marked unverified.** If a run has not been through
  `/verify-run`, do not record its numbers as findings.
- **Next steps must be startable without this conversation.** "Continue the
  analysis" is useless. Name the script, the input, and the expected output.
- Also update the project `CLAUDE.md`'s **Status** line — one or two sentences.
  That is what a future session reads first.

Report the path written and the next-steps list.
