---
description: Check the gotcha records for staleness, missing versions, and missing detection commands
argument-hint: [--stale DAYS]
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/../../tools/gotcha_audit.py" $ARGUMENTS
```

Report what it finds, then act on it:

- **`version unrecorded`** — the record cannot be checked against an upstream
  release. Next time that tool is touched, capture the version and fill it in.
- **Old records** (`--stale 180`) — check whether the upstream tool has moved a
  major version. If the bug is fixed, set `status: fixed-upstream` and keep the
  record; it explains why code still carries the workaround. Do not delete it.
- **Missing `detect_cmd`** — a gotcha without a detection command is an opinion.
  Either write one or mark the record as a process rule.

At roughly 50 records, split `analysis-gotchas` by category — parallel-R,
callers, file-format, statistics — rather than growing one routing table past
what a description can trigger on.
