# Proposed Hooks for init_project.py

Date: 2026-03-02
Status: Draft — review before implementing

---

## 1. Auto-scaffold on session start (highest impact)

**Hook type**: `UserPromptSubmit`
**Trigger**: Every new user prompt
**Condition**: No `config.yaml` or `data/` directory in cwd

When Claude starts in a directory with no project structure, warn immediately.

```json
{
  "hook": "UserPromptSubmit",
  "script": "[ ! -f config.yaml ] && [ ! -d data ] && echo 'WARNING: No project structure detected. Run: python init_project.py --type analysis --genome <build>'"
}
```

**Why**: CLAUDE.md §1.5 says "scaffold the directory structure automatically" but nothing enforces it today. A session-start hook closes the gap between the rule and reality. Every session either starts in an initialized project or gets reminded immediately.

**Catches problems at**: Session start
**Saves**: Prevents entire sessions of ad-hoc directory structure

---

## 2. Auto-create results dir per run

**Hook type**: `PostToolUse`
**Tool**: `Bash`
**Trigger**: Any `mkdir` that touches `results/`

After any mkdir in `results/`, validate it follows the `results/{date}_{description}/figures/{png,pdf,svg}` pattern. Auto-create the `figures/{png,pdf,svg}` subdirs if they're missing.

```json
{
  "hook": "PostToolUse",
  "tool": "Bash",
  "script": "new_results_dir.sh"
}
```

`new_results_dir.sh` would:
1. Detect if the Bash command created a new dir under `results/`
2. Check if `figures/{png,pdf,svg}` exist inside it
3. If not, create them automatically

**Why**: You'll create dozens of results dirs across a project. Forgetting `figures/{png,pdf,svg}` once means figures land in the wrong place and you waste time reorganizing.

**Catches problems at**: Every new analysis run
**Saves**: ~5 min each time, prevents scattered figures

---

## 3. Genome build tag validator on file write

**Hook type**: `PostToolUse`
**Tool**: `Write`
**Trigger**: Any file write of a genomic output type

After Claude writes any genomic output file, check that the filename contains a valid genome build tag and lives under `data/processed/{genome}/`.

```json
{
  "hook": "PostToolUse",
  "tool": "Write",
  "script": "validate_genome_tag.sh"
}
```

`validate_genome_tag.sh` would check:
1. Does the filename match `*.{bed,bam,vcf,vcf.gz,bedgraph,bedMethyl,bigwig,bw,bigbed,narrowPeak,broadPeak,gtf,gff,cram}`?
2. If yes, does it contain a valid genome tag (`mm10`, `mm39`, `GRCm39`, `hg38`, `GRCh38`, `hg19`, `GRCh37`, `t2t`, `chm13`)?
3. Is it under `data/processed/{genome}/`?
4. If either check fails, emit a warning

**Why**: Enforces CLAUDE.md §2 genome build tagging. A missing tag is silent until months later when you can't tell which build a file belongs to. Catching it at write time costs nothing; fixing it later costs hours.

**Catches problems at**: Every genomic file write
**Saves**: Prevents ambiguous files that haunt you months later

---

## Impact summary

| # | Hook | Catches problems at | Effort to implement |
|---|------|---------------------|---------------------|
| 1 | Auto-scaffold | Session start | Low (one-liner check) |
| 2 | Results dir creation | Every new run | Medium (parse bash commands) |
| 3 | Genome tag validation | Every file write | Medium (filename regex matching) |

## Open questions

- [ ] Should hook 1 auto-run init_project.py or just warn?
- [ ] Should hook 2 also enforce the `{date}_{description}` naming pattern?
- [ ] Should hook 3 block the write or just warn?
- [ ] Where should the hook scripts live? `claude/hooks/`?
