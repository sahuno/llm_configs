# claude/ — personal configuration

What remains here is **not** shipped as a plugin. It is the author's own Claude
Code setup, kept in the repo for reference and for syncing between machines.

If you are looking for the installable pieces, they moved:

| Was | Now | Install with |
|---|---|---|
| `claude/skills/` | `plugins/bio-skills/skills/` | `/plugin install bio-skills@sahuno` |
| `claude/agents/` | `plugins/bio-skills/agents/` | same |
| `claude/scripts/` | `plugins/bio-skills/scripts/` | same |
| `claude/hooks/*.sh` | `plugins/bio-guardrails/hooks/` | `/plugin install bio-guardrails@sahuno` |
| `claude/profiles/` | `plugins/hpc-site/profiles/` | `/plugin install hpc-site@sahuno` |
| `claude/rules/` | distributed into the skills that own them | — |

See the [repo README](../README.md) for the marketplace install.

## Contents

| Path | What it is |
|---|---|
| `CLAUDE.md` | The author's memory file. Personal — identity, lab conventions, domain playbooks. Not portable; read it for ideas, don't copy it wholesale. |
| `settings.json` | The author's Claude Code settings. Since the hooks moved to `bio-guardrails`, this holds only personal preferences (thinking mode, notification bell). |
| `docs/` | FAQ and reference notes |
| `examples/` | Worked examples (methylation pipeline, RNA-seq) |
| `prompts/` | Reusable prompt templates |
| `commands/` | Slash-command stubs for saving responses (superseded by the builtin `/copy`) |
| `mcps/` | MCP server notes |
| `inDevelopment/` | Drafts and brainstorms, not wired into anything |
| `tests/` | A test Snakemake workflow used to exercise the SLURM setup |
| `hooks/hooks.yaml` | **Dead.** A legacy hook format, wired to nothing, referencing a path that no longer exists. Kept only until confirmed removable. |

## About CLAUDE.md

Two things in it are worth borrowing even though the file as a whole is
personal:

- **§2 Universal Rules** — data integrity, seeds, naming, genome-build tagging,
  and a detailed logging/audit-trail spec for R, Python, and Bash. The hooks in
  `bio-guardrails` enforce the mechanical parts.
- **§0 Site configuration** — the `$SITE_CONFIG` indirection that keeps genome
  and container paths out of every other file.

It previously `@`-imported 15 tool-gotcha files by absolute `/data1/...` path.
Those failed silently off-cluster and cost ~15k tokens per session on it. They
are now skills that load on demand — see §2A.
