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
| `lab-figure-format` | Lab figure formatting, with `operon_arial.mplstyle` |

The first two are close cousins of work in `plugins/bio-skills` — the
`repro-auditor` agent asks the same question as `artifact-provenance-audit`, and
`pinned-reference-snapshot` is the reference-data analogue of the version
pinning that `gotcha_audit.py` enforces on incident records. Worth keeping the
wording aligned when either changes.
