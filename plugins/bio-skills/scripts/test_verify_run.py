#!/usr/bin/env python3
"""Tests for verify_run.py. Author: Samuel Ahuno

The load-bearing property: a run that exits 0, writes output and prints a
completion marker must still FAIL when it silently dropped work.
"""
import subprocess, sys, tempfile, pathlib

SCRIPT = pathlib.Path(__file__).parent / "verify_run.py"
PASS = FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ok   {name}")
    else:    FAIL += 1; print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")

def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env={"NO_COLOR": "1", "PATH": "/usr/bin:/bin"})

GOOD = "INFO: Filtering genes: 32415 -> 18203\n=== DONE ===\n"
OOM  = ("INFO: Filtering genes: 32415 -> 18203\n"
        "slurmstepd: error: Detected 3 oom_kill events in StepId=1.batch\n=== DONE ===\n")
RECYCLE = "Warning: number of items to replace is not a multiple of replacement length\n=== DONE ===\n"
NODONE = "INFO: started\nINFO: still going\n"
ERR = "Error in dmlTest(...) : subscript out of bounds\n=== DONE ===\n"

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    def log(name, body):
        p = d / name; p.write_text(body); return p
    def tsv(name, rows):
        p = d / name
        p.write_text("#chr\tstart\n" + "".join(f"chr1\t{i}\n" for i in range(rows)))
        return p

    r = run("--log", log("good.log", GOOD)); check("clean log passes", r.returncode == 0, r.stdout[-200:])
    r = run("--log", log("oom.log", OOM))
    check("OOM kill fails", r.returncode == 1)
    check("OOM failure is explained", "silently incomplete" in r.stdout)
    r = run("--log", log("recycle.log", RECYCLE))
    check("R recycling warning fails", r.returncode == 1)
    check("recycling explains wrong-row assignment", "wrong rows" in r.stdout)
    r = run("--log", log("nodone.log", NODONE))
    check("missing completion marker fails", r.returncode == 1)
    r = run("--log", log("err.log", ERR)); check("error marker fails", r.returncode == 1)

    # The core case: exits 0, writes output, prints DONE, but dropped rows.
    r = run("--log", log("g2.log", GOOD), "--output", tsv("short.tsv", 4021), "--expect-rows", 18203)
    check("row-count shortfall fails despite a clean log", r.returncode == 1)
    check("shortfall names the silent-drop shape", "silent drop looks exactly like this" in r.stdout)

    r = run("--log", log("g3.log", GOOD), "--output", tsv("full.tsv", 18203), "--expect-rows", 18203)
    check("matching row count passes", r.returncode == 0, r.stdout[-200:])
    r = run("--output", d / "missing.tsv"); check("missing output fails", r.returncode == 1)
    r = run("--output", tsv("empty.tsv", 0) if False else (d / "e.tsv").write_text("") or (d / "e.tsv"))
    check("empty output fails", r.returncode == 1)
    r = run(); check("no arguments is a usage error", r.returncode == 2)

print("─" * 46)
print(f"passed {PASS}   failed {FAIL}")
sys.exit(1 if FAIL else 0)
