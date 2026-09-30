---
description: Append this session's work to the project ledger (PROGRESS.md) so the next session can resume without re-discovery
argument-hint: [path to PROGRESS.md — defaults to the nearest one up to the git root]
---

Write the session's state as one dated entry in the project ledger,
`PROGRESS.md` at the project root. The ledger lives in the repository, so it
travels with the code between machines and to anyone else who works on it; a
file under `~/projects/` would split one project's history across hosts.

**Append, never overwrite.** New entries go at the top of `## Log`, newest
first, and earlier entries stay intact — the history of what was tried and
abandoned is the reason this file is worth keeping.

## How to write it

Use `ledger-append`, which finds the nearest `PROGRESS.md` (or the file in
`$ARGUMENTS`), prepends the entry under `## Log`, and updates the header:

```bash
ledger-append --who "Claude" \
  --summary "one line: what this session achieved" \
  --done "specific completed steps" \
  --paths "absolute paths created or modified" \
  --commands "copy-paste ready commands, with the arguments actually used" \
  --issues "what failed and why, or 'none encountered'" \
  --next "1. ... 2. ..." \
  --next-action "the very next thing to do, one sentence"
```

Check the entry with `--dry-run` first when unsure. If the project has no
ledger yet, add `--create --project <name>`. If `ledger-append` is not
installed, edit `PROGRESS.md` by hand with the same five fields and header
changes.

## The five fields — all five, every time

- **Done** — specific completed steps. Not "worked on DMRs" — "ran DSS DMLtest
  on 12 samples, chr19 only, ncores bound to SLURM_CPUS_PER_TASK".
- **Key paths** — absolute paths to what was created or modified.
- **Commands that worked** — copy-paste ready, with the arguments actually used.
- **Known issues / blockers** — what failed and why. An empty section here is
  usually a lie; if the session really hit nothing, say "none encountered".
- **Exact next steps** — numbered, actionable, specific enough to start cold.

## Rules

- **Write what happened, not what was intended.** If a step was abandoned, say
  so and why — that is the most valuable line in the file.
- **Unverified results are marked unverified.** If a run has not been through
  `/verify-run`, do not record its numbers as findings.
- **Next steps must be startable without this conversation.** "Continue the
  analysis" is useless. Name the script, the input, and the expected output.
- **Keep the header current.** `next_action` and `updated` are what the ledger
  hook shows first at the next session start. A question only the user can
  answer goes under `## Open unknowns` with a decide-by date.

Report the ledger path written and the next-steps list.
