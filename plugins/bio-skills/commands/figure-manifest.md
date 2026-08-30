---
description: Record or check which script, commit and inputs produced each figure in a run
argument-hint: --figure PATH --script PATH --inputs ... | --check RUN_DIR
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/figure_manifest.py" $ARGUMENTS
```

Record a figure as soon as it is written — at that moment the script, inputs and
parameters are known; a week later they are guesswork.

```bash
--figure results/<run>/figures/pdf/volcano.pdf \
--script src/04_plot_volcano.R \
--inputs results/<run>/dmr.tsv sample_sheet.tsv \
--notes "BH q<0.05, |delta|>0.1"
```

`--check <run-dir>` lists figures on disk with no manifest row. Run it before
assembling a manuscript: an unindexed figure cannot be traced to the code that
made it, and that is exactly the question asked at revision time.

The recorded commit carries a `-dirty` suffix when the tree had uncommitted
changes — that means the commit does not fully describe the code that ran, and
saying so is the point.
