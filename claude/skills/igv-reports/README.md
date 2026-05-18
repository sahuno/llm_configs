# igv-reports skill — moved

This skill has moved to its own repository:

**https://github.com/sahuno/igv-reports-skill**

## Why

The skill grew its own driver (`build_igvreports.py`), cohort/samplesheet
mode, three verifiers, a hermetic test suite, and CI. It deserves a
standalone repo where outsiders can clone it without pulling the entire
`llm_configs` monorepo, and where its versioning is independent.

## Migration

If you previously symlinked this path into `~/.claude/skills/`, update
the symlink to point at a clone of the new repo:

```bash
git clone https://github.com/sahuno/igv-reports-skill.git ~/code/igv-reports-skill
rm ~/.claude/skills/igv-reports
ln -s ~/code/igv-reports-skill ~/.claude/skills/igv-reports
```

Full history (10+ commits including all verifier work and the portability
patches) is preserved in the new repo via `git-filter-repo`.
