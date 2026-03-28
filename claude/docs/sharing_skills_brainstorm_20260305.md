# Brainstorm: Sharing Skills with Other Developers & Users

Date: 2026-03-05
Status: Draft — review and prioritize

---

## What we have to share

A **"Claude Code for Computational Biology" starter kit**:
- `CLAUDE.md` (v0.3.0) with domain-specific rules, hook annotations, quality gates
- 9 hooks enforcing genomics best practices (genome tagging, raw data protection, hardcoded contigs, etc.)
- `init_project.py` — parameterized project scaffolder (`--type analysis|pipeline|ml`, `--engine snakemake|nextflow`, `--genome`)
- Skills for common viz tasks (barplot-long-labels, igv-screenshots, heatmap-dimensions)
- SLURM/Snakemake profiles
- Reference genome config (`databases_config.yaml`)
- Validation scripts (`check_genome_consistency.py`, `check_sample_sheet.py`, `validate_config_params.py`)
- FAQ with HPC/container troubleshooting (LDAP fix, SSL/TLS fix, SLURM bind-mounts)

---

## Sharing channels (most to least effort)

### 1. The repo itself (already done, low effort)

`sahuno/llm_configs` is public on GitHub. But the name doesn't signal what it is.

**Actions**:
- [ ] Rename to something like `claude-bioinfo-toolkit` or `claude-code-compbio`
- [ ] Add a proper top-level README with screenshots/examples
- [ ] Add a "Quick Start" section: clone, symlink CLAUDE.md, copy hooks
- [ ] Add a LICENSE file

### 2. GitHub template repo (low effort, high discoverability)

Mark the repo as a [template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository). Other users can click "Use this template" to get their own copy with CLAUDE.md, hooks, and profiles pre-configured.

**Pros**: Zero friction for new users, works with GitHub's discovery features.
**Cons**: Users get a snapshot — no way to pull upstream updates.

### 3. Installable CLI (medium effort)

Package `init_project.py` as a pip-installable tool:

```bash
pip install claude-bioinfo
claude-bioinfo init --type analysis --genome hg38
```

This is the most shareable individual artifact — people don't need to understand the whole repo to use the scaffolder.

**Actions**:
- [ ] Add `pyproject.toml` with entry point
- [ ] Publish to PyPI
- [ ] Add `--install-hooks` flag that copies hook scripts to `~/.claude/hooks/`

### 4. Claude Code skills sharing (when available)

Claude Code skills (`claude/skills/*.md`) aren't formally shareable yet, but the format is just markdown files.

**Options**:
- Publish as a "skill pack" — a directory people drop into their `.claude/skills/`
- Contribute to a community skills registry if Anthropic creates one
- Share via GitHub as part of the template repo

### 5. Blog post / tutorial (medium effort, highest reach)

A post like *"How I use Claude Code for computational biology at MSKCC"* covering:
- The CLAUDE.md approach (teaching Claude your lab's conventions)
- Hooks as guardrails (genome tagging, raw data protection)
- init_project.py for reproducible project structure
- Before/after examples

**Where to post**:
- dev.to
- Biostars
- Twitter/X
- Claude Code GitHub Discussions
- bioRxiv (if framed as a methods note)

### 6. MCP server (higher effort, most powerful)

Package validation scripts as an MCP server:

```
mcp__bioinfo__check_genome_consistency
mcp__bioinfo__validate_sample_sheet
mcp__bioinfo__scaffold_project
```

Other Claude Code users could add the MCP server to their config and get the tools natively. This is the most "pluggable" approach.

**Actions**:
- [ ] Define MCP server with tool schemas
- [ ] Publish as npm/pip package
- [ ] Add to MCP server registry

---

## Target audiences

| Audience | What they need | Best channel |
|----------|----------------|--------------|
| Lab members (Greenbaum Lab) | Full toolkit, SLURM profiles | Repo + symlink instructions |
| Other comp bio labs at MSKCC | CLAUDE.md pattern + hooks | Blog post + template repo |
| General bioinformatics community | init_project.py + genome tagging hooks | pip package + blog |
| Claude Code power users (any domain) | The hooks/skills architecture pattern | Blog post on Claude Code GitHub Discussions |

---

## Recommended rollout order

1. **Now**: Rename repo + write a good README with quick start
2. **Soon**: Blog post — biggest leverage for reach
3. **Next**: Package init_project.py as pip-installable CLI
4. **Later**: MCP server for validation/scaffolding tools

---

## Also noticed: FAQ.md is outdated

The FAQ at `claude/docs/FAQ.md` still references the old directory structure:
- Line 121: `figures/`, `workflows/` at root level (should be `results/{date}_{genome}_{description}/figures/`)
- Line 302-308: Old `figures/{png,pdf,svg}/` structure
- Line 344-352: Old scaffold tree without `config.yaml`, `sample_sheet.tsv`, `logs/`, `softwares/`
- No mention of `init_project.py`
- No mention of `--type` or `--engine` project types
- No mention of new hooks (check_project_scaffold, ensure_results_figures)

**Action**: Sync FAQ.md with CLAUDE.md v0.3.0 after promoting.
