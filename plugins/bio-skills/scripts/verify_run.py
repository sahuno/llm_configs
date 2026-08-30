#!/usr/bin/env python3
"""Verify that a completed run actually succeeded.

Author: Samuel Ahuno
Purpose: Exit code 0 is not evidence of success. This checks the specific ways
         long parallel jobs on SLURM fail while still writing output and
         printing a completion marker.

Why a script and not a prompt: every check here is mechanical and has a right
answer. A prompt would re-derive them each time and skip one under load. The
failure modes encoded below were each confirmed on real runs — see the
`analysis-gotchas` skill for the incident records.

Usage
-----
    verify_run.py --log run.log
    verify_run.py --job-id 11635449 --log run.log --output results/dmr.tsv
    verify_run.py --log run.log --expect-rows 18203

Exit codes: 0 all checks passed | 1 at least one FAIL | 2 usage error
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = RESET = ""


@dataclass
class Result:
    name: str
    status: str          # PASS | FAIL | SKIP
    detail: str = ""

    def render(self) -> str:
        colour = {"PASS": GREEN, "FAIL": RED, "SKIP": DIM}[self.status]
        line = f"  {colour}{self.status:<4}{RESET}  {self.name}"
        return f"{line}\n        {DIM}{self.detail}{RESET}" if self.detail else line


def check_slurm_state(job_id: str) -> list[Result]:
    """sacct State must not be OUT_OF_MEMORY, FAILED, TIMEOUT or CANCELLED.

    A job the scheduler killed can still have written partial output and, for
    forked workers, a parent that exited 0.
    """
    if not job_id:
        return [Result("SLURM job state", "SKIP", "no --job-id given")]
    if not shutil.which("sacct"):
        return [Result("SLURM job state", "SKIP", "sacct not on PATH")]
    try:
        out = subprocess.run(
            ["sacct", "-j", job_id, "--noheader", "--parsable2",
             "--format=JobID,State,MaxRSS,ExitCode"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return [Result("SLURM job state", "SKIP", f"sacct failed: {exc}")]
    if not out:
        return [Result("SLURM job state", "SKIP", f"sacct returned nothing for {job_id}")]

    bad = {"OUT_OF_MEMORY", "FAILED", "TIMEOUT", "CANCELLED", "NODE_FAIL", "PREEMPTED"}
    results = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        step, state, maxrss, exitcode = parts[0], parts[1].split()[0], parts[2], parts[3]
        if state in bad:
            results.append(Result(f"SLURM state [{step}]", "FAIL",
                                  f"State={state} ExitCode={exitcode} MaxRSS={maxrss} — "
                                  "do not trust this run's output"))
        else:
            results.append(Result(f"SLURM state [{step}]", "PASS",
                                  f"State={state} MaxRSS={maxrss}"))
    return results or [Result("SLURM job state", "SKIP", "no parseable sacct rows")]


def check_log(log: Path) -> list[Result]:
    """Scan the log for the signatures of a silent partial failure."""
    if not log:
        return [Result("log scan", "SKIP", "no --log given")]
    if not log.exists():
        return [Result("log scan", "FAIL", f"{log} does not exist")]
    text = log.read_text(errors="replace")
    results = []

    # 1. OOM-killed forks. mclapply returns NULL for them; the parent continues.
    oom = len(re.findall(r"oom[_ ]kill", text, re.I))
    results.append(
        Result("no OOM kill events", "PASS", "0 occurrences") if oom == 0 else
        Result("no OOM kill events", "FAIL",
               f"{oom} occurrence(s) — forks were killed; results may be silently incomplete")
    )

    # 2. R recycling warning. The tell for DSS-style wrong-value assignment.
    recycle = re.findall(r"number of items to replace is not a multiple|longer object length", text, re.I)
    results.append(
        Result("no R recycling warning", "PASS") if not recycle else
        Result("no R recycling warning", "FAIL",
               f"{len(recycle)} warning(s) — a short result vector was recycled onto a longer index; "
               "values are assigned to the wrong rows")
    )

    # 3. Explicit error/traceback markers.
    errs = re.findall(r"^\s*(Error|Traceback|Fatal|Segmentation fault)", text, re.I | re.M)
    results.append(
        Result("no error markers", "PASS") if not errs else
        Result("no error markers", "FAIL", f"{len(errs)}: {', '.join(sorted(set(errs))[:4])}")
    )

    # 4. Completion marker. Its absence means the script did not reach the end.
    if re.search(r"===\s*DONE\s*===|Workflow finished|Nothing to be done|steps \(100%\) done", text, re.I):
        results.append(Result("completion marker present", "PASS"))
    else:
        results.append(Result("completion marker present", "FAIL",
                              "no '=== DONE ===' or engine completion line — the run did not reach the end"))

    # 5. Filter accounting. Advisory: their absence is a logging gap, not a failure.
    drops = re.findall(r"(\d[\d,]*)\s*(?:->|→)\s*(\d[\d,]*)", text)
    if drops:
        worst = max(drops, key=lambda d: int(d[0].replace(",", "")) - int(d[1].replace(",", "")))
        results.append(Result("filter steps logged with before/after counts", "PASS",
                              f"{len(drops)} logged; largest drop {worst[0]} -> {worst[1]}"))
    else:
        results.append(Result("filter steps logged with before/after counts", "SKIP",
                              "none found — cannot confirm what was dropped"))
    return results


def check_output(path: Path, expect_rows: int | None) -> list[Result]:
    """Output must exist, be non-empty, and match an expected row count if given."""
    if not path:
        return [Result("output file", "SKIP", "no --output given")]
    if not path.exists():
        return [Result("output file", "FAIL", f"{path} does not exist")]
    size = path.stat().st_size
    if size == 0:
        return [Result("output file", "FAIL", f"{path} is empty")]
    results = [Result("output exists and is non-empty", "PASS", f"{size:,} bytes")]
    if expect_rows is not None:
        with path.open(errors="replace") as fh:
            n = sum(1 for line in fh if not line.startswith("#"))
        results.append(
            Result("output row count", "PASS", f"{n:,} rows") if n == expect_rows else
            Result("output row count", "FAIL",
                   f"{n:,} rows, expected {expect_rows:,} — a silent drop looks exactly like this")
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify a run actually succeeded. Exit 0 is not evidence.")
    ap.add_argument("--job-id", help="SLURM job id to query with sacct")
    ap.add_argument("--log", type=Path, help="run log to scan")
    ap.add_argument("--output", type=Path, help="expected output file")
    ap.add_argument("--expect-rows", type=int, help="expected non-comment row count in --output")
    ap.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    args = ap.parse_args()

    if not any([args.job_id, args.log, args.output]):
        ap.error("give at least one of --job-id, --log, --output")

    results = (check_slurm_state(args.job_id or "")
               + check_log(args.log)
               + check_output(args.output, args.expect_rows))

    print(f"\n{'Verifying run':<40}")
    print("─" * 60)
    for r in results:
        print(r.render())
    print("─" * 60)

    failed = [r for r in results if r.status == "FAIL"]
    skipped = [r for r in results if r.status == "SKIP"]
    print(f"  {len(results) - len(failed) - len(skipped)} passed, "
          f"{len(failed)} failed, {len(skipped)} skipped\n")
    if failed:
        print(f"{RED}Do not trust this run's output until these are resolved.{RESET}\n")
        return 1
    if skipped:
        print(f"{YELLOW}Passed, but {len(skipped)} check(s) could not run — "
              f"absence of evidence is not evidence of success.{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
