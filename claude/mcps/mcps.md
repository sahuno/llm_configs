---
description: Frequently-used MCP servers for Samuel Ahuno's work
author: Samuel Ahuno
---

# Frequently-used MCPs

To load this list in a Claude Code session as a slash command (`/mcps`),
symlink or copy this file to `~/.claude/commands/mcps.md`:

```bash
ln -s /Users/ahunos/personal/PersonalizeClaude/llm_configs/claude/mcps/mcps.md ~/.claude/commands/mcps.md
```

Inspect / manage with: `claude mcp list`, `claude mcp add`, `claude mcp remove`.

---

## Computational biology

### enrichr-mcp-server
- Repo: https://github.com/tianqitang1/enrichr-mcp-server
- Install: `claude mcp add enrichr-mcp-server -- npx -y enrichr-mcp-server`
- Use for: gene-set enrichment (GO, KEGG, MSigDB) without leaving the session.

### IGV screenshot (igver)
- Repo: https://github.com/sahuno/igver
- Not an MCP server — invoked via singularity (see CLAUDE.md §3E).
- Use for: batch non-interactive IGV screenshots over BAM lists and regions files.

### PubMed (hosted)
- URL: https://pubmed.mcp.claude.com/mcp
- Install: `claude mcp add --transport http pubmed https://pubmed.mcp.claude.com/mcp`
- Use for: literature lookup, article metadata, citation resolution.

### Hugging Face (hosted)
- URL: https://huggingface.co/mcp
- Install: `claude mcp add --transport http huggingface https://huggingface.co/mcp`
- Auth: set `HF_TOKEN` (https://hf.co/settings/mcp) to lift rate limits.
- Use for: model/dataset/paper/space search, repo details, doc search.

---

## Databases

### Neon (Postgres)
- URL: https://mcp.neon.tech/mcp
- Install: `claude mcp add --transport http neon https://mcp.neon.tech/mcp`
- Use for: branch DBs, run SQL, explain plans, schema diffs, slow-query tuning.

---

## Productivity / inbox

### Gmail (hosted)
- URL: https://gmail.mcp.claude.com/mcp
- Install: `claude mcp add --transport http gmail https://gmail.mcp.claude.com/mcp`
- Auth: OAuth (run `mcp__claude_ai_Gmail__authenticate` once).
- Use for: draft/read/send email from inside a session.

### Google Calendar (hosted)
- URL: https://gcal.mcp.claude.com/mcp
- Install: `claude mcp add --transport http gcal https://gcal.mcp.claude.com/mcp`
- Auth: OAuth.
- Use for: schedule lookups, event creation, meeting prep.

---

## Deployment

### Vercel (hosted)
- URL: https://mcp.vercel.com
- Install: `claude mcp add --transport http vercel https://mcp.vercel.com`
- Use for: list/deploy projects, fetch build & runtime logs, toolbar threads.

---

## Quick load-all (paste block)

```bash
claude mcp add --transport http pubmed       https://pubmed.mcp.claude.com/mcp
claude mcp add --transport http huggingface  https://huggingface.co/mcp
claude mcp add --transport http neon         https://mcp.neon.tech/mcp
claude mcp add --transport http gmail        https://gmail.mcp.claude.com/mcp
claude mcp add --transport http gcal         https://gcal.mcp.claude.com/mcp
claude mcp add --transport http vercel       https://mcp.vercel.com
claude mcp add enrichr-mcp-server -- npx -y enrichr-mcp-server
```
