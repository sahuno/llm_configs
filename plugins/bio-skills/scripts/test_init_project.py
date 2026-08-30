#!/usr/bin/env python3
"""Tests for init_project.py scaffolding. Author: Samuel Ahuno"""
import subprocess, sys, tempfile, pathlib

SCRIPT = pathlib.Path(__file__).parent / "init_project.py"
PASS = FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ok   {name}")
    else:    FAIL += 1; print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")

def scaffold(tmp, *args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=tmp,
                       capture_output=True, text=True)
    return r

with tempfile.TemporaryDirectory() as tmp:
    r = scaffold(tmp, "--name", "demo", "--type", "analysis", "--genome", "hg38")
    root = pathlib.Path(tmp) / "demo"
    check("exits 0", r.returncode == 0, r.stderr[:200])
    cm = root / "CLAUDE.md"
    check("writes a project CLAUDE.md", cm.exists())
    if cm.exists():
        body = cm.read_text()
        check("names the genome build", "hg38" in body)
        check("names the domain", "Bioinformatics Analysis" in body)
        check("points at the progress log", "~/projects/demo.md" in body)
        check("has an Aims section", "## Aims" in body)
        check("has a Status section", "## Status" in body)
    check("still writes README/config/sample_sheet",
          all((root / f).exists() for f in ("README.md", "config.yaml", "sample_sheet.tsv")))

with tempfile.TemporaryDirectory() as tmp:
    r = scaffold(tmp, "--name", "pipe", "--type", "pipeline",
                 "--engine", "snakemake", "--genome", "mm10")
    body = (pathlib.Path(tmp) / "pipe" / "CLAUDE.md").read_text()
    check("pipeline type records the engine", "snakemake" in body)
    check("pipeline type records its domain", "pipeline" in body.lower())

with tempfile.TemporaryDirectory() as tmp:
    scaffold(tmp, "--name", "nf", "--type", "pipeline", "--engine", "nextflow", "--genome", "hg38")
    cfg = pathlib.Path(tmp) / "nf" / "nextflow.config"
    check("nextflow engine scaffolds nextflow.config", cfg.exists())
    if cfg.exists():
        body = cfg.read_text()
        check("inherits the site profile", "includeConfig" in body and "SITE_CONFIG" in body)
        check("warns when SITE_CONFIG is unset", "WARNING: SITE_CONFIG unset" in body)
        check("documents -resume", "-resume" in body)
        check("keeps cluster facts out of the pipeline", "componc" not in body and "greenbab" not in body)

with tempfile.TemporaryDirectory() as tmp:
    scaffold(tmp, "--name", "sm", "--type", "pipeline", "--engine", "snakemake", "--genome", "hg38")
    check("snakemake engine gets no nextflow.config",
          not (pathlib.Path(tmp) / "sm" / "nextflow.config").exists())

print("─" * 42)
print(f"passed {PASS}   failed {FAIL}")
sys.exit(1 if FAIL else 0)
