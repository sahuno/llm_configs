# Claude Science skills

Source of truth for skills authored for [Claude Science](https://claude.ai/science)
(the `operon` / `claude-science` daemon). The app loads them from
`~/.claude-science/orgs/<org-uuid>/skills/`; this directory is where they live
in version control.

## Why they are not edited in place

That app directory is runtime state, not a workspace. Alongside the skills it
holds a multi-hundred-megabyte SQLite database, OAuth tokens, an encryption key
and a daemon socket — so it cannot be version controlled as-is, and committing
it would leak credentials.

It is also rewritten by releases. Every vendor skill in it carries the same
mtime: the release drop. `claude-science update` self-updates and can roll back
to an arbitrary build. A skill you authored there exists in exactly one place —
the release bundle at `runtime/<version>/skills/` does not contain it — and is
one upgrade away from being replaced or removed.

## Sync

```bash
tools/sync_science_skills.sh status              # what differs, and which way
tools/sync_science_skills.sh pull                # app -> repo (refresh tracked)
tools/sync_science_skills.sh pull <skill>...     # app -> repo (adopt a new one)
tools/sync_science_skills.sh push                # repo -> app (restore)
```

Run `status` after every `claude-science update`. That is the moment this exists
for.

**Copies, not symlinks.** A release that rewrites the skills directory would
replace a symlink with a real directory, silently detaching the source of truth
at exactly the moment you needed it. A copy that drifts shows up in `status`; a
detached symlink does not.

**Tracking is opt-in.** `status` lists skills the release does not ship as
*candidates*, but that test is a hint, not proof of authorship — org-synced
product skills also fail it. Adopt one deliberately with `pull <name>`.

`.sync-org` (your org UUID) and `.catalog_stamp` (rewritten every sync) are
stripped on pull and gitignored. The app regenerates both.

## Tracked

| Skill | What it does |
|---|---|
| `artifact-provenance-audit` | Establishes that every saved artifact has a runnable producer and that the repo executes from a clean checkout |
| `pinned-reference-snapshot` | Pins an external reference resource to a vendored, checksummed snapshot so results cannot shift under a database release |
| `lab-figure-format` | The house style itself — typeface, widths, point ladders, multi-format export, with `operon_arial.mplstyle` |
| `print-plate-assembly` | Assembles finished panels onto a printable sheet with a manifest and legend — and is where the house style is imposed |

## Where the house style is enforced

Two skills make figures and neither is the authority. The vendor
`figure-composer` builds a multi-panel figure from data, and it fans panels out
to sub-agents that load `figure-style` alone — so panels come back in whatever
face and sizes matplotlib defaulted to. Treat its output as a **draft**.

`print-plate-assembly` re-renders every panel from its producing code before
placing it on the sheet, and Step 2 of that re-render pins the call order:

```python
exec(recovered_panel_code)   # the producer sets its own rcParams
apply_figure_style()         # figure-style: design
house_style()                # lab-figure-format: the house face and ladder
```

That makes the plate the **gate**: the last thing before a figure leaves the
project, and the one place the house typography is actually applied rather than
merely checked. `test_kernel.py` guards the pin — it fails if the call order is
edited out of `SKILL.md`, if it drifts before the `exec`, or if
`lab-figure-format` changes the ladder underneath it. CI runs it on every push.

There used to be a third skill here, `lab-figure-composer` — a fork of the
vendor `figure-composer` that carried the house style through the panel
fan-out. It was retired once the plate could enforce the same thing at a point
this repo owns outright, which costs no fork to maintain across releases. See
`git log -- science-skills/lab-figure-composer` and section C of the overlap
audit. The trade: the vendor's review pass now judges a draft rather than the
final look, and a mis-sized panel is silently resized where the fork raised.
`predict_print_size()` at Step 5 is what catches that now.

These overlap with work in `plugins/`, `tools/` and `CLAUDE.md`. That overlap is
audited with citations in [`../docs/skill-overlap-audit.md`](../docs/skill-overlap-audit.md):
one genuine conflict (resolved), one gap in this repo that
`pinned-reference-snapshot` exposed (partly closed — checksums still need the
cluster), and one clean complement. Re-read it when either side changes a shared
concept.
