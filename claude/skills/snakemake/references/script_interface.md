# Script Interface Convention

Every pluggable script under `workflow/scripts/` follows this pattern to ensure
standalone testability, consistent logging, and proper integration with Snakemake.

## Template

```python
#!/usr/bin/env python3
"""
{script_name} — {one-line description}

Author: Samuel Ahuno (ekwame001@gmail.com)
Date: {date}

Usage:
    python3 {script_name}.py \\
        --input  <input_file> \\
        --output <output_file> \\
        --sample-id <sample_name> \\
        [--extra-arg value]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def log(msg):
    """Print timestamped message to stdout (captured by Snakemake &> {log})."""
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--input", required=True, help="...")
    parser.add_argument("--output", required=True, help="...")
    parser.add_argument("--sample-id", default="unknown", help="...")
    args = parser.parse_args()

    log(f"=== {Path(__file__).stem} ===")
    log(f"input:     {args.input}")
    log(f"output:    {args.output}")
    log(f"sample_id: {args.sample_id}")

    # ... processing ...

    # Handle gzip transparently
    import gzip
    opener = gzip.open if args.input.endswith(".gz") else open
    with opener(args.input, "rt") as fh:
        pass  # read data

    # ... save output ...

    log(f"=== DONE: {Path(__file__).stem} completed successfully ===")


if __name__ == "__main__":
    main()
```

## Key Conventions

1. **argparse with `--help`** for all arguments — scripts are testable standalone
2. **Timestamped log messages** to stdout (captured by Snakemake `&> {log}`)
3. **Completion marker**: ends with `"=== DONE: script_name completed successfully ==="` — if missing from log, the script crashed
4. **Gzip transparency**: `gzip.open if path.endswith(".gz") else open`
5. **Text mode for gzip**: use `"rt"` (not `"rb"`) for text processing
6. **Input validation**: check that input files exist before processing
7. **pd.read_csv gotcha**: pandas auto-converts `"NA"` strings to NaN — use `dropna()` for filtering, never `!= "NA"` string comparison

## Referencing Scripts from Snakefile

```python
params:
    script=os.path.join(workflow.basedir, "scripts", "my_script.py"),
shell:
    """
    python3 {params.script} --input {input.data} --output {output.result}
    """
```

The `workflow.basedir` reference ensures the script is found regardless of where
Snakemake is invoked from.

## When to Externalize vs Inline

| Keep Inline | Externalize |
|------------|-------------|
| `awk '{print "chr"$0}'` | Multi-step Python processing |
| `bgzip && tabix` | `if/for/while` logic |
| `samtools index` | Variable manipulation |
| `wc -l < file` | Anything benefiting from standalone testing |

Rule of thumb: if you can't understand the shell block in 10 seconds, externalize it.
