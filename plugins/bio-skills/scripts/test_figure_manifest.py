#!/usr/bin/env python3
"""Tests for figure_manifest.py. Author: Samuel Ahuno"""
import subprocess, sys, tempfile, pathlib
S = pathlib.Path(__file__).parent / "figure_manifest.py"
PASS = FAIL = 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ok   {name}")
    else:    FAIL += 1; print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")
def run(*a):
    return subprocess.run([sys.executable, str(S), *map(str, a)], capture_output=True, text=True)

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    run_dir = d / "results" / "20260829_hg38_dmr"
    (run_dir / "figures" / "pdf").mkdir(parents=True)
    fig = run_dir / "figures" / "pdf" / "volcano.pdf"; fig.write_text("%PDF")
    src = d / "src"; src.mkdir(); script = src / "04_plot.R"; script.write_text("# plot")

    r = run("--figure", fig, "--script", script, "--inputs", "a.tsv", "b.tsv", "--notes", "BH q<0.05")
    check("records a figure", r.returncode == 0, r.stderr[:120])
    idx = run_dir / "figure_index.tsv"
    check("writes the index next to the run", idx.exists())
    body = idx.read_text() if idx.exists() else ""
    check("header present", body.startswith("#figure\tscript"))
    check("inputs joined", "a.tsv;b.tsv" in body)
    check("notes kept", "BH q<0.05" in body)

    r = run("--figure", fig, "--script", script)
    check("appends rather than overwrites", idx.read_text().count("volcano.pdf") == 2)
    check("missing inputs are flagged, not silently blank", "UNRECORDED" in idx.read_text())

    r = run("--check", run_dir)
    check("check passes when all figures indexed", r.returncode == 0, r.stdout[:120])

    orphan = run_dir / "figures" / "pdf" / "heatmap.pdf"; orphan.write_text("%PDF")
    r = run("--check", run_dir)
    check("check fails on an unindexed figure", r.returncode == 1)
    check("names the unindexed figure", "heatmap.pdf" in r.stdout)

    r = run("--figure", d / "nope.pdf"); check("missing figure errors", r.returncode == 1)
    r = run(); check("no args is a usage error", r.returncode == 2)

print("─" * 46); print(f"passed {PASS}   failed {FAIL}")
sys.exit(1 if FAIL else 0)
