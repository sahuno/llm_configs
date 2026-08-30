---
name: artifact-provenance-audit
description: Establish that every saved data artifact in a project has a runnable producer, and that the analysis repo executes from a clean workspace. Use this before a handoff, a paper submission or a repo release, and whenever someone asks "can this be rerun from scratch", "where did this table come from", "which script writes this file", or reports that a notebook fails on a fresh checkout because it reads inputs nothing in the repo creates. Scans scripts and notebooks for write calls versus read calls, cross-checks against the artifact store's lineage records, classifies each artifact by producer status, and routes orphans into an existing script instead of spawning one script per orphan. Ships helpers scan_producers, discover_io_helpers, stage_script_artifacts, match_artifacts_to_producers, lineage_producers and diff_against_saved.
---

# Artifact provenance audit

A project accumulates saved tables faster than it accumulates the code that
writes them. The failure is quiet: everything runs today because the objects are
already in a live kernel, and the gap only surfaces months later when someone
clones the repo, or a reviewer asks for the script behind a supplementary table.
This skill finds that gap while the kernel is still warm and the author still
remembers.

Run it when a project is about to leave your hands. It is not a per-artifact
ritual — auditing one file you just wrote tells you nothing.

## Two producer records, and why one is not enough

**Store-side.** The artifact store records the cell that produced each version:
`host.lineage[vid]["code"]`, with the dependency DAG in
`host.lineage.graph(vid)`. This is automatic and complete.

**Repo-side.** A script or notebook cell, committed, that writes the file from
inputs it can itself reconstruct.

These come apart, and the gap between them is the whole point of the audit. An
artifact written by an interactive cell has perfect store-side lineage and still
cannot be rebuilt by anyone holding the repo — the cell referenced a variable
that lived in a kernel that no longer exists. In one real audit of 71 artifacts,
18 had exactly that shape. Store lineage tells you the artifact is *explained*;
only the repo tells you it is *reproducible*.

So: never close this audit on lineage alone.

## Step 1 — enumerate what exists

`host.artifacts(project_id=...)` in the `python` kernel. Include intermediates if
the question is "does the repo run"; exclude them if the question is "is every
deliverable attributable".

## Step 2 — scan for writers, not readers, and in both places

**Both places.** In this runtime the analysis code is frequently saved as
artifacts rather than committed to the repo. A repo-only scan then reports
*every* artifact as an orphan, which is loud and useless. Stage the code out of
the store first and scan both roots:

```python
staged = stage_script_artifacts("staged_scripts")
scan = scan_producers([REPO, "staged_scripts"], extra_write=[...], extra_read=[...])
```

**House wrappers.** Many repos route all I/O through a local helper —
`save_figure(fig, stem)`, `read_data_tsv(name)` — and a scan built on a fixed
call list finds literally nothing in them. Run `discover_io_helpers(root)` first,
read the list, and pass the genuine wrappers via `extra_write` / `extra_read`.
Do not pass the whole list: discovery flags any function whose body reaches a
write call, so entry points and generic plotting functions come back too, and
auto-including them turns a colour string into a filename. Ten seconds of
judgement here is worth more than a better heuristic.

**Then read the direction column.** The read/write distinction is the
diagnostic, not a detail. A cell that reads five tables **nothing in the repo
writes** is the exact signature of a pipeline that cannot start from a clean
workspace, and a scan that only greps for `to_csv` reports that cell as healthy.
Look at reads whose targets have no writer anywhere: those are the entry points
that will fail on a fresh clone.

`match_artifacts_to_producers(filenames, scan)` joins the two sides and returns
`n_writers`, `n_readers`, `writers`, `readers`, `repo_orphan` and
`blocks_reproduction`.

**`repo_orphan` on its own is not a finding.** In a real 71-artifact audit, 69
were repo-orphans and only 20 should ever have had a script — the rest were
hand-assembled records, external fetches, and outputs of a separate packaged
pipeline. That is what steps 4 and 5 are for.

## Step 3 — cross-check the store, and respect extraction lag

`lineage_producers(version_ids)` returns per-version `has_code`, `n_inputs`,
`n_edges` and `extraction_pending`.

**The false positive that will otherwise dominate your table:** dependency edges
are extracted asynchronously, seconds to minutes after a save. A `graph()` call
returning zero edges with `extraction_pending=True` means *not extracted yet* —
it does not mean orphan. Filing those as orphans produces an audit that is
mostly noise on a project whose last save was recent. Re-read `host.lineage[vid]`
to make a stuck mapping converge (retries are paced, so leave a gap), then call
`graph()` again, and only classify rows where `extraction_pending` is false.

One runtime constraint shapes the design: `host.query()` over the
`artifact_dependencies` table is available in the `repl` tool only, while
`host.lineage` and `host.artifacts` work in the `python` kernel where your
DataFrame lives. Build the audit on the `python`-side accessors; reach for
`host.query` only for a whole-project aggregate, and hand it across via a file.

## Step 4 — classify, with a triage column

One row per artifact:

| column | meaning |
|---|---|
| `filename`, `vid`, `bytes` | identity |
| `bucket` | which family it belongs to — a separate pipeline, a hand-assembled record, an external fetch, one section's outputs |
| `producer` | the script, notebook section, or `interactive <lang> cell` |
| `producer_kind` | `script` / `notebook` / `interactive` / `external` / `unknown` |
| `needs_script` | there is no runnable producer and there should be |
| `home` | the existing script this orphan should be routed into (step 5) |
| `home_rationale` | why that script and not a new one |
| `blocks_reproduction` | **the triage column** |
| `status` | how it was closed, with evidence |

`blocks_reproduction` is what keeps the audit finite. A hand-assembled methods
table with no producer is fine — nothing downstream reads it. An orphan that a
later step *reads* is a hard stop. Sort by it, fix those, and let the rest be
documented rather than rebuilt. An audit that treats all 71 rows as equally
urgent gets abandoned.

## Step 5 — route orphans into an existing script

When an orphan needs a producer, add it to **the script whose inputs are already
in memory at the point the table would be written** — not a new script per
orphan.

The reason is concrete. A standalone script for an orphaned interaction table
has to re-fit both models before it can write a single row, and the fitted
objects were already sitting in the script where the interaction terms were
first defined. A user put it plainly during one of these audits: *why can't we
add it to the script where the interactions started being defined?* One script
gained six lines; the alternative was a second file that duplicated an hour of
fitting to recover a table the first script already held.

So the routing question is not "what is this table about" but "where does the
data for it already exist". Record the answer in `home_rationale`.

## Step 6 — the notebook is the source of truth

When a notebook is flattened to a runner script for execution, **regenerate the
runner in the same step that runs it.** Running a stale flattened copy is a true
silent failure: it exits 0 and renders the pre-edit source, so the output looks
fresh and reflects code you have already changed. Nothing in the exit status or
the rendered document reveals it. One command, regenerate-then-run, never two.

## Step 7 — code recovered from lineage is a reconstruction

Lineage-extracted code is what was reconstructed for that artifact, not
necessarily the original producer. Two recovered producers in one audit carried
comments admitting they could not reach an input and had disabled a step — they
would have run, produced a plausible table, and silently differed.

Before trusting recovered code, run it and diff:
`diff_against_saved(reproduced_df, saved_path, key_cols=[...])` reports
per-column exact matches, near matches, and mismatches. Only a column-level
match licenses "this script reproduces the artifact"; a matching row count does
not.

## Done looks like

Every artifact has a `producer_kind`; every row with `blocks_reproduction=True`
has a `status` recording how it was closed and what evidence closed it; and the
repo has been run once from an empty workspace. Save the table as an artifact —
it is the document a reviewer or a successor actually needs.

## Known false positives — do not chase these

- `extraction_pending=True` rows (step 3).
- Artifacts fetched from an external source: the "producer" is a documented URL
  plus a checksum, not a script. Record the fetch, do not write a generator.
- Files written by a separate packaged pipeline that lives outside this repo —
  attribute to the package and version, and stop there.
- Superseded one-offs. Archive them; do not build producers for artifacts no
  current analysis reads.
