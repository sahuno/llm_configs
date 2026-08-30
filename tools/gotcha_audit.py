#!/usr/bin/env python3
"""Audit the gotcha records for staleness and completeness.

Author: Samuel Ahuno

These records are the most expensive knowledge in the repo — each one cost a
failed run to acquire. They are also the most perishable: nearly every entry is
bound to a tool version ("modkit 0.6.1", "Snakemake 9", "Clair3 v2.0.1"). A
record whose tool has moved on is not merely stale, it is actively misleading,
because it reads as current.

Two rules enforced here:

  1. Every record carries frontmatter: tool, version_observed, date, status,
     detect_cmd.
  2. A gotcha without a detection command is an opinion. `detect_cmd` may be
     empty only for a process rule with nothing to probe, and that must be said
     explicitly in the field's comment.

Usage:
    gotcha_audit.py            # report; exit 1 if anything is missing
    gotcha_audit.py --stale N  # also flag records older than N days
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

REQUIRED = ["tool", "version_observed", "date", "status", "detect_cmd"]
VALID_STATUS = {"active", "fixed-upstream", "superseded"}
ROOT = pathlib.Path(__file__).resolve().parent.parent


def records() -> list[pathlib.Path]:
    """Every reference file that is a gotcha record."""
    out = []
    for skill in ROOT.glob("plugins/*/skills/*/references/*.md"):
        text = skill.read_text(errors="replace")
        # A record is one that carries (or should carry) the frontmatter.
        if text.startswith("---\n") and "version_observed" in text[:400]:
            out.append(skill)
        elif skill.name in {"gotchas.md", "env_leak.md"} or "analysis-gotchas" in str(skill) \
                or "mskcc-hpc" in str(skill):
            out.append(skill)
    return sorted(set(out))


def frontmatter(path: pathlib.Path) -> dict | None:
    text = path.read_text(errors="replace")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block, out, key = text[4:end], {}, None
    for line in block.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).split("#")[0].strip().strip('"|').strip()
        elif key and line.startswith("  "):
            out[key] = (out.get(key, "") + " " + line.strip()).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit gotcha records.")
    ap.add_argument("--stale", type=int, metavar="DAYS",
                    help="flag records whose observation date is older than DAYS")
    args = ap.parse_args()

    problems, rows = [], []
    for p in records():
        rel = p.relative_to(ROOT)
        fm = frontmatter(p)
        if fm is None:
            problems.append(f"{rel}: no frontmatter — run /add-gotcha or add it by hand")
            continue
        missing = [k for k in REQUIRED if k not in fm]
        if missing:
            problems.append(f"{rel}: missing {', '.join(missing)}")
        status = fm.get("status", "")
        if status and status not in VALID_STATUS:
            problems.append(f"{rel}: status '{status}' not one of {sorted(VALID_STATUS)}")
        if "detect_cmd" in fm and not fm["detect_cmd"] and fm.get("tool") != "process rule":
            problems.append(f"{rel}: empty detect_cmd — a gotcha without a detection "
                            f"command is an opinion")
        rows.append((rel, fm))

    print(f"\n{len(rows)} gotcha record(s)\n" + "─" * 78)
    unversioned = 0
    for rel, fm in rows:
        ver = fm.get("version_observed", "?")
        flag = ""
        if ver in {"unrecorded", "?"}:
            unversioned += 1
            flag = "  ← version unrecorded: cannot be audited for staleness"
        if args.stale and fm.get("date", "").count("-") == 2:
            try:
                age = (dt.date.today() - dt.date.fromisoformat(fm["date"])).days
                if age > args.stale:
                    flag += f"  ← {age}d old"
            except ValueError:
                pass
        print(f"  {fm.get('status','?'):<14} {fm.get('tool','?'):<22} "
              f"{ver:<12} {fm.get('date','?')}{flag}")
        print(f"  {'':14} {rel}")

    print("─" * 78)
    print(f"  {len(rows) - unversioned}/{len(rows)} carry a tool version")
    if unversioned:
        print(f"  {unversioned} cannot be checked against an upstream release — "
              f"record the version next time the tool is touched")
    if problems:
        print(f"\n  {len(problems)} problem(s):")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  all records complete\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
