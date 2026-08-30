---
description: Run the pre-completion quality gates before declaring any analysis done
---

Work through the completion checklist. Report each item as pass, fail, or not
applicable, with the evidence — a path, a count, a command's output. An item you
cannot verify is a fail, not a pass.

## Enforced automatically (confirm the hooks are active, do not re-check by hand)

The `bio-guardrails` plugin blocks raw-data writes, cross-genome mixing,
untagged genomic outputs and dangerous commands, and warns on hardcoded contigs,
invalid YAML and absolute paths. If those hooks are not installed, say so — the
rest of this list assumes they are.

## Verify by inspection

1. **Outputs exist and are non-empty.** List them with sizes.
2. **Random seeds set** for every stochastic step. Quote the line.
3. **Figures in all three formats** under `results/{run}/figures/{png,pdf,svg}/`.
4. **No forbidden variable names** (`conditions`, `counts`, `results`, `sum`,
   `median`, `mean`) — these shadow builtins.
5. **A timestamped log exists** in `logs/`, capturing data dimensions, before/after
   filter counts, and output confirmations, with both stdout and stderr.
6. **The run was verified, not just completed.** Run `/verify-run` against the
   job and log. A completion marker is not success.
7. **Progress file updated** at `~/projects/<project>.md` with what was done, key
   paths, working commands, blockers, and exact next steps.
8. **QC checkpoints reported** to the user, not merely passed silently.

Finish with a one-line verdict: ready, or the specific list of what is not.
