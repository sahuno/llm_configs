---
description: Verify a completed run actually succeeded — exit 0 is not evidence
argument-hint: [--job-id ID] [--log FILE] [--output FILE] [--expect-rows N]
---

Run the mechanical verification. Do **not** re-derive these checks by reading
the log yourself; the script encodes failure modes confirmed on real runs.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify_run.py" $ARGUMENTS
```

If the user gave no arguments, find the most recent log under `logs/` or
`results/*/logs/` and the newest output file, and ask before guessing a
`--expect-rows` value — a wrong expectation produces a false alarm.

## Reading the result

- **Any FAIL** — the run's output cannot be trusted. Say so plainly and do not
  proceed to interpretation, plotting, or downstream steps. Report which check
  failed and what it implies.
- **SKIP** — the check could not run (no job id, `sacct` absent, no expected row
  count). Absence of evidence is not evidence of success; say which checks were
  skipped rather than reporting a clean bill of health.
- **All PASS** — report it, and name what was actually verified.

## Why this exists

A long parallel job on SLURM can exit 0, write output, and print its completion
marker while having silently lost work: `mclapply` returns `NULL` for
OOM-killed forks, the parent continues, and a short result vector gets recycled
onto a longer index so values land on the wrong rows. On real data this inflated
a DMR count 10–20×, and nothing in the log looked wrong.

See the `analysis-gotchas` skill for the incident records behind each check.
