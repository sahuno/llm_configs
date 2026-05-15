#!/usr/bin/env python3
"""sciAuditor — multi-script aggregator.

Walks a project directory, dispatches each analysis script to the right
language parser (parser_r/parser_py/parser_bash), auto-detects bash
launcher↔analysis pairs, and produces a cohort-level audit report
that scores the whole project alongside per-script reports.

Outputs under --output-dir:
    cohort_audit_report.md         project-wide summary
    cohort_findings.tsv            every finding + script_path column
    per_script/<basename>/         each script's individual report set

Author: Samuel Ahuno / sciAuditor
Date:   2026-05-14
"""

from __future__ import annotations

import argparse
import fnmatch
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
PARSER_R    = HERE.parent / "parser_r"    / "sciauditor_r.R"
PARSER_PY   = HERE.parent / "parser_py"   / "sciauditor_py.py"
PARSER_BASH = HERE.parent / "parser_bash" / "sciauditor_bash.py"

# Lab defaults — both ship Python ≥3.12 and the R parser needs r-env's yaml+optparse
DEFAULT_RSCRIPT = "/home/ahunos/miniforge3/envs/r-env/bin/Rscript"
DEFAULT_PYTHON  = "/home/ahunos/miniforge3/envs/snakemake/bin/python3"


def discover_scripts(project_dir: Path) -> list[Path]:
    """Find every analysis script in the project directory (recursive)."""
    out = []
    for ext in ("*.R", "*.r", "*.py", "*.sh"):
        out.extend(sorted(project_dir.rglob(ext)))
    return out


def apply_filters(scripts: list[Path], project_dir: Path,
                  include_globs: list[str],
                  ignore_globs:  list[str]) -> list[Path]:
    """Apply --include and --ignore glob filters against paths relative to
    project_dir. Include-first (if any include patterns specified the script
    must match at least one), then ignore (drop if it matches any).
    Matches both the relative path AND every individual path segment so a
    user can write `--ignore archived` to drop anything under archived/."""
    def matches_any(rel_str: str, patterns: list[str]) -> bool:
        if not patterns:
            return False
        segments = rel_str.split("/")
        for p in patterns:
            if fnmatch.fnmatch(rel_str, p):
                return True
            if any(fnmatch.fnmatch(seg, p) for seg in segments):
                return True
        return False

    out = []
    for s in scripts:
        try:
            rel = str(s.relative_to(project_dir))
        except ValueError:
            rel = str(s)
        if include_globs and not matches_any(rel, include_globs):
            continue
        if matches_any(rel, ignore_globs):
            continue
        out.append(s)
    return out


def detect_pairs(scripts: list[Path], python_bin: str) -> dict[Path, Path]:
    """For every bash script, parse it via sciauditor_bash and check
    `invocation.script`. If it points to another script in the project,
    record the pair. Returns {analysis_path: launcher_path}."""
    pairs = {}
    analyses_by_name = {s.resolve(): s for s in scripts
                         if s.suffix.lower() in (".r", ".py")}
    for sh in scripts:
        if sh.suffix.lower() != ".sh":
            continue
        try:
            launcher_yaml = run_bash_parser(sh, python_bin)
        except Exception as e:
            sys.stderr.write(f"[aggregate] WARN: bash parse failed on {sh}: {e}\n")
            continue
        inv = (launcher_yaml or {}).get("invocation")
        if not inv:
            continue
        script_str = inv.get("script") or ""
        if not script_str:
            continue
        candidate = Path(script_str).resolve()
        if candidate in analyses_by_name:
            pairs[candidate] = sh
    return pairs


def run_bash_parser(launcher: Path, python_bin: str) -> dict | None:
    """Run sciauditor_bash on `launcher` and return its YAML as a dict."""
    res = subprocess.run(
        [python_bin, str(PARSER_BASH), "--input", str(launcher), "--output", "-"],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        return None
    return yaml.safe_load(res.stdout)


def run_parser(script: Path, out_dir: Path, *, language: str,
               rscript_bin: str, python_bin: str,
               pair_launcher: Path | None = None) -> dict:
    """Dispatch to the right per-language parser. Returns
    {"inferred_yaml": Path, "report_md": Path, "findings_tsv": Path,
     "headline": str, "errored": bool, "stderr": str}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    inferred = out_dir / "analysis.inferred.yaml"
    report_md_dir = out_dir  # report writes directly into out_dir
    common = ["--input", str(script),
              "--output", str(inferred),
              "--report_dir", str(report_md_dir)]
    if language == "R":
        cmd = [rscript_bin, str(PARSER_R)] + common
        if pair_launcher:
            cmd += ["--pair_launcher", str(pair_launcher)]
    elif language == "python":
        cmd = [python_bin, str(PARSER_PY)] + common
        # Python parser doesn't accept --pair_launcher yet; surface a note
    elif language == "bash":
        # bash parser doesn't ship --report_dir; just emit YAML
        cmd = [python_bin, str(PARSER_BASH),
               "--input", str(script), "--output", str(inferred)]
    else:
        return {"errored": True, "stderr": f"unknown language {language}"}

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "inferred_yaml": inferred if inferred.exists() else None,
        "report_md":     report_md_dir / "audit_report.md"
                          if (report_md_dir / "audit_report.md").exists() else None,
        "findings_tsv":  report_md_dir / "audit_findings.tsv"
                          if (report_md_dir / "audit_findings.tsv").exists() else None,
        "errored":       res.returncode != 0,
        "stderr":        res.stderr,
        "stdout":        res.stdout,
    }


def headline_from_report(report_md: Path) -> tuple[str, str]:
    """Parse `# Headline` table from an audit_report.md.
    Returns (score, grade) or ('—', '—')."""
    if report_md is None or not report_md.exists():
        return ("—", "—")
    txt = report_md.read_text()
    m = re.search(r"\|\s*(\d+\s*/\s*\d+\s*\([^)]+\))\s*\|\s*\*\*(\w+)\*\*\s*\|", txt)
    if m:
        return (m.group(1).strip(), m.group(2).strip())
    return ("—", "—")


def severity_counts(findings_tsv: Path) -> dict:
    """Return {BLOCKER: N, WARNING: N, NOTE: N, OK: N}."""
    counts = {"BLOCKER": 0, "WARNING": 0, "NOTE": 0, "OK": 0}
    if findings_tsv is None or not findings_tsv.exists():
        return counts
    with findings_tsv.open() as f:
        next(f, None)  # header
        for line in f:
            sev = line.split("\t", 1)[0].strip()
            if sev in counts:
                counts[sev] += 1
    return counts


def language_for(path: Path) -> str:
    s = path.suffix.lower()
    return {".r": "R", ".py": "python", ".sh": "bash"}.get(s, "unknown")


GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4, "N/A": 5, "—": 5}


def audit_one_script(work: dict) -> dict:
    """Worker function: parse one script, return its per_script_row and the
    rows for cohort_findings.tsv. Self-contained / picklable so it can run
    in a multiprocessing.Pool."""
    s             = Path(work["script"])
    project_dir   = Path(work["project_dir"])
    sub_out       = Path(work["sub_out"])
    lang          = work["language"]
    rscript_bin   = work["rscript_bin"]
    python_bin    = work["python_bin"]
    pair_launcher = Path(work["pair_launcher"]) if work["pair_launcher"] else None

    res = run_parser(s, sub_out,
                     language=lang,
                     rscript_bin=rscript_bin,
                     python_bin=python_bin,
                     pair_launcher=pair_launcher if lang == "R" else None)
    score, grade = headline_from_report(res["report_md"])
    counts = severity_counts(res["findings_tsv"])
    row = {
        "script":   str(s.relative_to(project_dir)),
        "language": lang,
        "paired":   "✓" if pair_launcher else "",
        "errored":  res["errored"],
        "score":    score,
        "grade":    grade,
        **counts,
    }
    findings = []
    if res["findings_tsv"] is not None and res["findings_tsv"].exists():
        with res["findings_tsv"].open() as f:
            next(f, None)
            for line in f:
                parts = line.rstrip("\n").split("\t", 3)
                if len(parts) < 4:
                    parts += [""] * (4 - len(parts))
                sev, rule, sites, note = parts
                findings.append({
                    "script_path": str(s.relative_to(project_dir)),
                    "language":    lang,
                    "severity":    sev,
                    "rule":        rule,
                    "sites":       sites,
                    "note":        note,
                })
    return {"row": row, "findings": findings}


def aggregate(project_dir: Path, output_dir: Path,
              rscript_bin: str, python_bin: str,
              skip_consumed_launchers: bool = True,
              jobs: int = 1,
              include_globs: list[str] | None = None,
              ignore_globs:  list[str] | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    per_dir = output_dir / "per_script"
    per_dir.mkdir(parents=True, exist_ok=True)

    scripts = discover_scripts(project_dir)
    n_total = len(scripts)
    if include_globs or ignore_globs:
        scripts = apply_filters(scripts, project_dir,
                                include_globs or [], ignore_globs or [])
        n_filtered = n_total - len(scripts)
        if n_filtered:
            print(f"[sciauditor_aggregate] filtered out {n_filtered}/{n_total} "
                  f"script(s) via --include/--ignore", flush=True)
    pairs   = detect_pairs(scripts, python_bin)
    consumed_launchers = set(pairs.values())

    # Build the work list (cheap, sequential)
    work_items = []
    for s in scripts:
        if skip_consumed_launchers and s in consumed_launchers:
            continue
        lang = language_for(s)
        if lang == "unknown":
            continue
        try:
            rel = s.relative_to(project_dir)
        except ValueError:
            rel = Path(s.name)
        subdir_id = str(rel).replace("/", "__").replace(" ", "_")
        sub_out = per_dir / subdir_id
        pair_launcher = None
        for analysis, launcher in pairs.items():
            if analysis == s.resolve():
                pair_launcher = launcher; break
        work_items.append({
            "script":        str(s),
            "project_dir":   str(project_dir),
            "sub_out":       str(sub_out),
            "language":      lang,
            "rscript_bin":   rscript_bin,
            "python_bin":    python_bin,
            "pair_launcher": str(pair_launcher) if pair_launcher else None,
        })

    per_script_rows = []
    all_findings   = []
    n = len(work_items)
    t0 = time.time()
    if jobs > 1 and n > 1:
        print(f"[sciauditor_aggregate] auditing {n} scripts with {jobs} workers ...",
              flush=True)
        # Spawn ensures children re-import the module cleanly (no fork-state pickling issues)
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=jobs) as pool:
            for i, result in enumerate(
                    pool.imap_unordered(audit_one_script, work_items), start=1):
                per_script_rows.append(result["row"])
                all_findings.extend(result["findings"])
                print(f"  [{i}/{n}] {result['row']['script']}  "
                      f"{result['row']['grade']}", flush=True)
    else:
        print(f"[sciauditor_aggregate] auditing {n} scripts sequentially ...",
              flush=True)
        for i, work in enumerate(work_items, start=1):
            result = audit_one_script(work)
            per_script_rows.append(result["row"])
            all_findings.extend(result["findings"])
            print(f"  [{i}/{n}] {result['row']['script']}  "
                  f"{result['row']['grade']}", flush=True)
    wall_s = time.time() - t0
    print(f"[sciauditor_aggregate] parse phase done in {wall_s:.1f}s", flush=True)

    # ----- emit cohort_findings.tsv -----
    findings_path = output_dir / "cohort_findings.tsv"
    with findings_path.open("w") as f:
        f.write("script_path\tlanguage\tseverity\trule\tsites\tnote\n")
        for fd in all_findings:
            f.write("\t".join(fd[c] for c in
                              ("script_path", "language", "severity",
                               "rule", "sites", "note")) + "\n")

    # ----- emit cohort_audit_report.md -----
    md = []
    md.append("# sciAuditor — Cohort Audit Report")
    md.append("")
    md.append(f"- **Project dir**: `{project_dir}`")
    md.append(f"- **Scripts audited**: {len(per_script_rows)}")
    md.append(f"- **Inferred at**: {datetime.now().astimezone().isoformat(timespec='seconds')}")
    md.append("")

    # ----- Project-wide headline -----
    total_blocker = sum(r["BLOCKER"] for r in per_script_rows)
    total_warning = sum(r["WARNING"] for r in per_script_rows)
    total_note    = sum(r["NOTE"]    for r in per_script_rows)
    total_ok      = sum(r["OK"]      for r in per_script_rows)
    errors        = sum(1 for r in per_script_rows if r["errored"])
    grade_count = {}
    for r in per_script_rows:
        grade_count[r["grade"]] = grade_count.get(r["grade"], 0) + 1
    md.append("## Headline")
    md.append("")
    md.append("| Findings | BLOCKER | WARNING | NOTE | OK | Parser errors |")
    md.append("|---|---:|---:|---:|---:|---:|")
    md.append(f"| Project total | {total_blocker} | {total_warning} | {total_note} | {total_ok} | {errors} |")
    md.append("")
    md.append("**Grade distribution:**")
    md.append("")
    md.append("| Grade | Scripts |")
    md.append("|---|---:|")
    for g in ("A", "B", "C", "D", "F", "N/A", "—"):
        if g in grade_count:
            md.append(f"| {g} | {grade_count[g]} |")
    md.append("")

    # ----- Per-script table -----
    md.append("## Per-script")
    md.append("")
    md.append("| Script | Lang | Pair | Score | Grade | BLOCKER | WARNING | NOTE |")
    md.append("|---|---|:-:|---|:-:|---:|---:|---:|")
    # Sort: worst grade first, then BLOCKER count
    per_script_rows_sorted = sorted(
        per_script_rows,
        key=lambda r: (GRADE_ORDER.get(r["grade"], 9), -r["BLOCKER"], r["script"]),
        reverse=False,
    )
    # ↑ ascending by grade (best first) — flip if you want worst first
    for r in per_script_rows_sorted:
        rel_dir = per_dir.name + "/" + str(r["script"]).replace("/", "__").replace(" ", "_")
        link = f"[{r['script']}]({rel_dir}/audit_report.md)" if not r["errored"] \
               else f"~~{r['script']}~~ (parser error)"
        md.append(f"| {link} | {r['language']} | {r['paired']} | {r['score']} | "
                  f"**{r['grade']}** | {r['BLOCKER']} | {r['WARNING']} | {r['NOTE']} |")
    md.append("")

    # ----- Findings rolled up by rule -----
    rule_counts = {}
    for fd in all_findings:
        if fd["severity"] in ("OK",):
            continue
        key = (fd["severity"], fd["rule"])
        rule_counts[key] = rule_counts.get(key, 0) + 1
    if rule_counts:
        md.append("## Findings rolled up by rule")
        md.append("")
        md.append("| Severity | Rule | Scripts affected |")
        md.append("|---|---|---:|")
        for (sev, rule), n in sorted(rule_counts.items(),
                                     key=lambda kv: ({"BLOCKER":0,"WARNING":1,"NOTE":2,"OK":3}
                                                     .get(kv[0][0],9), -kv[1])):
            md.append(f"| {sev} | {rule} | {n} |")
        md.append("")

    report_path = output_dir / "cohort_audit_report.md"
    report_path.write_text("\n".join(md) + "\n")

    return {
        "report":   report_path,
        "findings": findings_path,
        "n_scripts": len(per_script_rows),
        "n_pairs":   sum(1 for r in per_script_rows if r["paired"]),
        "n_errors":  errors,
        "totals":    {"BLOCKER": total_blocker, "WARNING": total_warning,
                       "NOTE": total_note, "OK": total_ok},
    }


SEVERITY_GATE_ORDER = ["BLOCKER", "WARNING", "NOTE"]


def compute_gate_status(totals: dict, fail_on: str) -> tuple[bool, int, str]:
    """Returns (gate_failed, total_at_or_above, reason). When fail_on='none',
    always passes."""
    if fail_on == "none":
        return (False, 0, "gate disabled (--fail-on none)")
    if fail_on not in SEVERITY_GATE_ORDER:
        return (False, 0, f"unknown gate level '{fail_on}'")
    idx = SEVERITY_GATE_ORDER.index(fail_on)
    triggered = SEVERITY_GATE_ORDER[: idx + 1]  # gate level + everything stricter
    count = sum(totals.get(s, 0) for s in triggered)
    if count > 0:
        return (True, count,
                f"{count} finding(s) at >= {fail_on} ({'/'.join(triggered)})")
    return (False, 0, f"no findings at >= {fail_on}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", "-p", required=True,
                    help="root directory to audit recursively")
    ap.add_argument("--output-dir",  "-o", required=True,
                    help="where to write cohort_audit_report.md and per_script/")
    ap.add_argument("--rscript", default=DEFAULT_RSCRIPT,
                    help=f"Rscript binary [default: {DEFAULT_RSCRIPT}]")
    ap.add_argument("--python",  default=DEFAULT_PYTHON,
                    help=f"python3 binary [default: {DEFAULT_PYTHON}]")
    ap.add_argument("--fail-on", choices=["BLOCKER", "WARNING", "NOTE", "none"],
                    default="none",
                    help="exit 1 if cohort has any findings at or above this "
                         "severity (CI gate). 'none' (default) always exits 0.")
    ap.add_argument("--jobs", "-j", type=int,
                    default=min(os.cpu_count() or 1, 8),
                    help="number of parallel worker processes "
                         "[default: min(cpu_count, 8)]; 1 disables parallelism")
    ap.add_argument("--include", action="append", default=[], metavar="GLOB",
                    help="audit only paths matching this glob (relative to "
                         "--project-dir, or any path segment); repeatable")
    ap.add_argument("--ignore",  action="append", default=[], metavar="GLOB",
                    help="exclude paths matching this glob (relative to "
                         "--project-dir, or any path segment); repeatable; "
                         "applied after --include")
    args = ap.parse_args()

    pd  = Path(args.project_dir).resolve()
    out = Path(args.output_dir).resolve()
    if not pd.exists():
        sys.exit(f"project dir not found: {pd}")

    print(f"[sciauditor_aggregate] scanning {pd} (jobs={args.jobs}) ...")
    res = aggregate(pd, out, args.rscript, args.python,
                    jobs=args.jobs,
                    include_globs=args.include,
                    ignore_globs=args.ignore)
    print(f"[sciauditor_aggregate] {res['n_scripts']} scripts audited "
          f"({res['n_pairs']} paired, {res['n_errors']} parser errors)")
    print(f"[sciauditor_aggregate]   totals: BLOCKER={res['totals']['BLOCKER']} "
          f"WARNING={res['totals']['WARNING']} NOTE={res['totals']['NOTE']} "
          f"OK={res['totals']['OK']}")
    print(f"[sciauditor_aggregate]   report: {res['report']}")
    print(f"[sciauditor_aggregate]   findings: {res['findings']}")

    # CI gate
    failed, _, reason = compute_gate_status(res["totals"], args.fail_on)
    status = "FAIL" if failed else "PASS"
    sys.stderr.write(f"[sciauditor_aggregate] GATE: {status} ({reason})\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
