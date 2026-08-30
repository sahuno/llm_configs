---
description: Scaffold a genomics project directory (config, sample sheet, immutable raw/, genome-tagged processed/, workflow dirs)
argument-hint: [--name NAME] [--type analysis|pipeline|ml] [--engine snakemake|nextflow] [--genome hg38|mm10|mm39|GRCh37|t2t]
---

Scaffold a new genomics project using this plugin's `init_project.py`.

Run it with the arguments the user supplied. With no `--name`, it scaffolds in
the current directory using the directory name as the project name:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_project.py" $ARGUMENTS
```

If the user gave no arguments at all, ask which project type and genome build
they want before running — those two choices determine the whole layout and are
awkward to change afterwards.

After it runs, **fill in the generated `CLAUDE.md`** — its Aims and Status
sections are placeholders. That file is what lets future sessions skip the
"what are we working on" question entirely, so leaving it as TODO wastes the
main benefit of scaffolding.

Then report the created tree and point out the two conventions the guardrail
hooks enforce, so the user isn't surprised by a later block:

- `data/raw/` is immutable. Writes there are blocked once it holds data.
- Files under `data/processed/` must carry a genome-build tag in the filename
  (`{sample}.{build}.{description}.{ext}`).
