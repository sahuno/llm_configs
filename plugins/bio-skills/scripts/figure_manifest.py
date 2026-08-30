#!/usr/bin/env python3
"""Record which script, commit and inputs produced a figure.

Author: Samuel Ahuno

CLAUDE.md §9 asks for "a figure index per script". This is that index, made
mechanical. Six months on, the question asked of every manuscript figure is
"which version of which script made this, from what input?" — and the answer is
usually reconstructed by guesswork.

Appends one row per figure to ``results/<run>/figure_index.tsv``:

    figure  script  git_commit  inputs  date  notes

Usage
-----
    figure_manifest.py --figure results/20260829_hg38_dmr/figures/pdf/volcano.pdf \\
                       --script src/04_plot_volcano.R \\
                       --inputs results/.../dmr.tsv sample_sheet.tsv \\
                       --notes "BH q<0.05, |delta|>0.1"

    figure_manifest.py --list results/20260829_hg38_dmr      # show the index
    figure_manifest.py --check results/20260829_hg38_dmr     # find unindexed figures
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

HEADER = ["figure", "script", "git_commit", "inputs", "date", "notes"]
FIG_EXT = {".png", ".pdf", ".svg", ".tiff", ".eps"}


def git_commit(path: Path) -> str:
    """Short commit of the repo containing `path`, with a dirty marker."""
    try:
        cwd = path.parent if path.parent.exists() else Path.cwd()
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, timeout=10)
        if rev.returncode != 0:
            return "not-a-git-repo"
        sha = rev.stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                               capture_output=True, text=True, timeout=10).stdout.strip()
        # A dirty tree means the recorded commit does not fully describe the code
        # that ran. Saying so is the point.
        return f"{sha}-dirty" if dirty else sha
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def run_dir_of(figure: Path) -> Path:
    """The results/<run>/ directory a figure lives under."""
    for parent in figure.resolve().parents:
        if parent.name == "figures":
            return parent.parent
    return figure.resolve().parent


def index_path(run_dir: Path) -> Path:
    return run_dir / "figure_index.tsv"


def append(figure: Path, script: Path | None, inputs: list[str], notes: str) -> int:
    if not figure.exists():
        print(f"error: {figure} does not exist", file=sys.stderr)
        return 1
    idx = index_path(run_dir_of(figure))
    idx.parent.mkdir(parents=True, exist_ok=True)
    new = not idx.exists()
    row = [
        str(figure),
        str(script) if script else "UNRECORDED",
        git_commit(script if script else figure),
        ";".join(inputs) if inputs else "UNRECORDED",
        dt.date.today().isoformat(),
        notes or "",
    ]
    with idx.open("a") as fh:
        if new:
            fh.write("#" + "\t".join(HEADER) + "\n")
        fh.write("\t".join(r.replace("\t", " ") for r in row) + "\n")
    print(f"recorded {figure.name} -> {idx}")
    if row[1] == "UNRECORDED" or row[3] == "UNRECORDED":
        print("  note: script or inputs unrecorded — this row cannot answer "
              "'what produced this figure?'", file=sys.stderr)
    return 0


def show(run_dir: Path) -> int:
    idx = index_path(run_dir)
    if not idx.exists():
        print(f"no figure index at {idx}", file=sys.stderr)
        return 1
    print(idx.read_text())
    return 0


def check(run_dir: Path) -> int:
    """Report figures on disk with no manifest row."""
    idx = index_path(run_dir)
    recorded = set()
    if idx.exists():
        for line in idx.read_text().splitlines():
            if line and not line.startswith("#"):
                recorded.add(line.split("\t")[0])
    found = [p for p in run_dir.rglob("*") if p.suffix.lower() in FIG_EXT]
    missing = [p for p in found if str(p) not in recorded]
    print(f"{len(found)} figure(s), {len(found) - len(missing)} indexed")
    for m in missing:
        print(f"  UNINDEXED  {m}")
    if missing:
        print("\nAn unindexed figure cannot be traced to the code that made it.",
              file=sys.stderr)
    return 1 if missing else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--figure", type=Path)
    ap.add_argument("--script", type=Path)
    ap.add_argument("--inputs", nargs="*", default=[])
    ap.add_argument("--notes", default="")
    ap.add_argument("--list", type=Path, metavar="RUN_DIR")
    ap.add_argument("--check", type=Path, metavar="RUN_DIR")
    ap.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    args = ap.parse_args()

    if args.list:
        return show(args.list)
    if args.check:
        return check(args.check)
    if args.figure:
        return append(args.figure, args.script, args.inputs, args.notes)
    ap.error("give --figure, --list or --check")


if __name__ == "__main__":
    sys.exit(main())
