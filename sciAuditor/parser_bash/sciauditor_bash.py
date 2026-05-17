#!/usr/bin/env python3
# sciAuditor bash front-end (Layer A, static)
# Author: Samuel Ahuno / sciAuditor
# Date: 2026-05-14
# Purpose: Read a bash analysis or launcher script and emit a v0.2
#   inferred YAML matching sciAuditor/02_inference_design.md §4.
#   In round 1 the bash front-end has a thinner surface than R/Python:
#   path-extraction, variable assignments, mkdir/cd/export side effects,
#   and (critically) detection of any Rscript/python invocation so the
#   companion R parser can compose a pair_unit block.

import argparse
import os
import re
import sys
from datetime import datetime

import yaml


ASSIGNMENT_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$')
VAR_REF_RE    = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)')
INVOKER_HINTS = ("Rscript", "python3", "python", "snakemake", "nextflow")
ABSOLUTE_PATH_RE = re.compile(r'^[/~]')

# casetrack append extractor — used to populate casetrack_appends[] for
# the shared aggregator/casetrack_check.py module. Same regex shape works
# across bash / python / R source because the literal tokens ('casetrack',
# 'append', '--analysis', '--results') appear identically in all three.
CASETRACK_APPEND_RE = re.compile(
    r"\bcasetrack\b[\s'\",)\]]{1,40}\bappend\b(?P<rest>[\s\S]{0,500}?)(?:\n\n|\Z|;;)",
    re.IGNORECASE,
)
CT_ANALYSIS_RE    = re.compile(r"--analysis[=\s,\"'\]]+([^\s'\",)\]]+)")
CT_RESULTS_RE     = re.compile(r"--results[=\s,\"'\]]+([^\s'\",)\]]+)")
CT_PROJECT_DIR_RE = re.compile(r"--project[_-]dir[=\s,\"'\]]+([^\s'\",)\]]+)")


def extract_casetrack_appends(source: str, *, assigns: dict | None = None) -> list[dict]:
    """Scan source text for `casetrack append ...` invocations.
    Returns a list of {analysis, results, project_dir, site} dicts.
    Bash-specific: if `assigns` is provided, resolve $VAR / ${VAR} in
    extracted values."""
    out = []
    for m in CASETRACK_APPEND_RE.finditer(source):
        rest = m.group("rest")
        am = CT_ANALYSIS_RE.search(rest)
        rm = CT_RESULTS_RE.search(rest)
        pm = CT_PROJECT_DIR_RE.search(rest)
        if not am and not rm:
            continue
        def _resolve(v):
            if v is None or assigns is None:
                return v
            return resolve_var_refs(v, assigns)
        out.append({
            "analysis":    _resolve(am.group(1)) if am else None,
            "results":     _resolve(rm.group(1)) if rm else None,
            "project_dir": _resolve(pm.group(1)) if pm else None,
            "site":        source.count("\n", 0, m.start()) + 1,
        })
    return out


def resolve_var_refs(text, assigns):
    """Substitute ${VAR} / $VAR with values from `assigns` (recursive, capped)."""
    def repl(m):
        name = m.group(1) or m.group(2)
        v = assigns.get(name)
        return str(v["value"]) if v is not None else m.group(0)
    prev = None
    out = text
    # Bound the resolution depth in case of self-reference cycles
    for _ in range(5):
        prev = out
        out = VAR_REF_RE.sub(repl, out)
        if out == prev:
            break
    return out


def coerce(value):
    """Best-effort cast: int / float / bool / leave-as-string."""
    if re.match(r'^-?\d+$', value):
        return int(value)
    if re.match(r'^-?\d+\.\d+$', value):
        return float(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


def parse_assignments(raw_lines):
    """First pass: simple `NAME=value` and `NAME="value"` bindings.
    Multi-line / backtick / $(...) forms are recorded as opaque."""
    assigns = {}
    for i, ln in enumerate(raw_lines, start=1):
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = ASSIGNMENT_RE.match(stripped)
        if not m:
            continue
        name, rhs = m.groups()
        rhs = re.sub(r'\s+#.*$', '', rhs).rstrip()  # strip trailing comment
        rhs = strip_quotes(rhs)
        resolved = resolve_var_refs(rhs, assigns)
        kind = "absolute" if ABSOLUTE_PATH_RE.match(resolved) else "relative"
        assigns[name] = {
            "value":        coerce(resolved),
            "raw":          rhs,
            "site":         i,
            "default_kind": kind,
        }
    return assigns


def parse_side_effects(raw_lines):
    """mkdir / cd / export / set / source / Sys.setenv equivalents."""
    out = []
    for i, ln in enumerate(raw_lines, start=1):
        s = ln.strip()
        if s.startswith("#"):
            continue
        if re.match(r'^mkdir\b', s):
            paths = re.findall(r'"[^"]*"|\S+', s[6:])
            paths = [strip_quotes(p) for p in paths if not p.startswith("-")]
            out.append({"site": i, "kind": "mkdir", "paths": paths})
        elif re.match(r'^cd\b', s):
            arg = strip_quotes(s[3:].strip())
            out.append({"site": i, "kind": "cd", "detail": arg})
        elif re.match(r'^export\b', s):
            out.append({"site": i, "kind": "env_set", "detail": s})
        elif re.match(r'^set\s+-', s):
            out.append({"site": i, "kind": "set_flag", "detail": s})
        elif re.match(r'^(source|\.)\s', s):
            arg = re.sub(r'^(source|\.)\s+', '', s)
            out.append({"site": i, "kind": "source", "detail": strip_quotes(arg)})
    return out


def join_continuations(raw_lines):
    """Glue lines ending in '\\' into single logical lines.
    Returns (joined_lines, start_line_per_joined) parallel lists."""
    joined, starts = [], []
    buf, buf_start = "", None
    for i, ln in enumerate(raw_lines, start=1):
        if buf_start is None:
            buf_start = i
        if ln.rstrip("\n").endswith("\\"):
            buf += ln.rstrip("\n")[:-1] + " "
        else:
            buf += ln.rstrip("\n")
            joined.append(buf)
            starts.append(buf_start)
            buf, buf_start = "", None
    if buf:
        joined.append(buf)
        starts.append(buf_start or len(raw_lines))
    return joined, starts


FLAG_RE = re.compile(
    r'(--[A-Za-z][\w.-]*|-[A-Za-z])\s+("[^"]*"|\'[^\']*\'|\$\{[A-Za-z_]\w*\}|\$[A-Za-z_]\w*|\S+)'
)


def detect_invocation(joined_lines, starts, assigns):
    """Look for the first Rscript/python invocation. Returns dict or None."""
    for ln, start in zip(joined_lines, starts):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        # Tokenise just enough: first token = invoker, second = script
        toks = re.findall(r'"[^"]*"|\S+', s)
        if len(toks) < 2:
            continue
        invoker_raw = strip_quotes(toks[0])
        invoker = resolve_var_refs(invoker_raw, assigns)
        is_r = invoker.endswith("Rscript") or "Rscript" in invoker
        is_py = bool(re.search(r'(^|/)(python|python3)$', invoker))
        if not (is_r or is_py):
            continue
        script_raw = strip_quotes(toks[1])
        script = resolve_var_refs(script_raw, assigns)
        # Parse --flag value pairs from the remainder
        rest = " ".join(toks[2:])
        flags = []
        for m in FLAG_RE.finditer(rest):
            flag, raw_val = m.group(1), m.group(2)
            unquoted = strip_quotes(raw_val)
            vm = re.match(r'^\$\{([A-Za-z_]\w*)\}$|^\$([A-Za-z_]\w*)$', unquoted)
            if vm:
                flags.append({
                    "flag": flag,
                    "value_var": vm.group(1) or vm.group(2),
                    "value_resolved": resolve_var_refs(unquoted, assigns),
                })
            else:
                flags.append({"flag": flag, "value": unquoted})
        return {
            "site":      start,
            "invoker":   invoker,
            "language":  "R" if is_r else "python",
            "script":    script,
            "flags":     flags,
        }
    return None


# CLAUDE.md §2 — names that clash with builtins; case-insensitive in bash
FORBIDDEN_NAMES = {"counts", "results", "mean", "median", "sum", "conditions"}
CONTIG_RE       = re.compile(r"""["']chr([0-9]+|[XYM]|MT)["']""")
GENOME_TOKEN_RE = re.compile(
    r"\b(mm10|mm39|GRCm39|hg38|GRCh38|hg19|GRCh37|t2t|chm13)\b")
GENOMIC_EXT_RE  = re.compile(
    r"\.(bam|bed|bedmethyl|vcf|fa|fasta|gtf|gff|pod5)(\.gz)?$|/reference/|/genome/")


def _is_comment(line: str) -> bool:
    return line.strip().startswith("#")


def compliance_checks(raw_lines, assigns, side_effects, invocation):
    """Bash-flavored compliance check set. 7 rules total: 2 BLOCKER, 3 WARNING, 2 NOTE."""
    head_comments = [ln for ln in raw_lines[:10] if _is_comment(ln)]
    has_author  = any(re.search(r"(?i)(^|[^a-z])(author|name)\s*:", h) for h in head_comments)
    has_date    = any(re.search(r"(?i)date|\d{4}-\d{2}-\d{2}", h) for h in head_comments)
    has_purpose = any(re.search(r"(?i)purpose|description", h) for h in head_comments)
    header_pass = has_author and (has_date or has_purpose)
    abs_vars    = [v for v in assigns.values() if v["default_kind"] == "absolute"]

    checks = []
    def push(rule, status, evidence_sites=None, note=None):
        checks.append({"rule": rule, "status": status,
                       "evidence_sites": evidence_sites or [], "note": note})

    # script-header-metadata (NOTE)
    push("script-header-metadata",
         "pass" if header_pass else "fail",
         evidence_sites=[1] if head_comments else [],
         note=(None if header_pass else
               "missing Author/Date/Purpose in first 10 comment lines"))

    # relative-paths-only (WARNING)
    push("relative-paths-only",
         "fail" if abs_vars else "pass",
         evidence_sites=[v["site"] for v in abs_vars],
         note=("{} variables resolve to absolute paths".format(len(abs_vars))
               if abs_vars else None))

    # forbidden-variable-names (WARNING) — case-insensitive against CLAUDE.md list
    forbid_hits = [(name, info["site"]) for name, info in assigns.items()
                   if name.lower() in FORBIDDEN_NAMES]
    if forbid_hits:
        push("forbidden-variable-names", "fail",
             evidence_sites=[s for _, s in forbid_hits],
             note=("collisions: " + ",".join(sorted({n for n, _ in forbid_hits}))))
    else:
        push("forbidden-variable-names", "pass")

    # ===== BLOCKERs =====

    # raw-data-write: any mkdir / redirect / cp / mv into data/raw/ or /raw/
    raw_hits = []
    raw_path_re = re.compile(r"(?:^|/)(?:data/)?raw/")
    # 1) side-effect paths (mkdir, etc.)
    for se in side_effects:
        for p in (se.get("paths") or []):
            if isinstance(p, str) and raw_path_re.search(p):
                raw_hits.append((se["site"], "mkdir " + p))
    # 2) redirect patterns and cp/mv targets in non-comment code
    write_redirect_re = re.compile(
        r"""(?:>>?\s*["']?[^|&\n]*?(?:^|/)(?:data/)?raw/|"""
        r"""mkdir\s[^\n]*?(?:^|/)(?:data/)?raw/|"""
        r"""(?:cp|mv|rsync|touch|chmod)\s[^\n]+?(?:^|/)(?:data/)?raw/)""",
        re.IGNORECASE)
    for i, ln in enumerate(raw_lines, start=1):
        if _is_comment(ln): continue
        code = re.sub(r"\s*#[^\"']*$", "", ln)
        if write_redirect_re.search(code):
            raw_hits.append((i, code.strip()[:80]))
    if raw_hits:
        push("raw-data-write", "fail",
             evidence_sites=[s for s, _ in raw_hits],
             note=("{} occurrence(s) write under data/raw/".format(len(raw_hits))))
    else:
        push("raw-data-write", "pass")

    # hardcoded-contig (BLOCKER): regex on non-comment code lines
    contig_lines = []
    for i, ln in enumerate(raw_lines, start=1):
        if _is_comment(ln): continue
        code = re.sub(r"\s*#[^\"']*$", "", ln)
        if CONTIG_RE.search(code):
            contig_lines.append(i)
    if contig_lines:
        push("hardcoded-contig", "fail",
             evidence_sites=contig_lines,
             note=("{} line(s) contain hardcoded contig literals".format(len(contig_lines))))
    else:
        push("hardcoded-contig", "pass")

    # ===== WARNINGs / NOTEs =====

    # logging-dual-capture (NOTE): bash idiom is `exec > >(tee -a "$LOG") 2>&1`
    full_text = "".join(raw_lines)
    has_tee_exec = bool(re.search(r"exec\s+>\s*>\s*\(\s*tee\b", full_text))
    has_tee_2gt1 = bool(re.search(r"\btee\s+(-a\s+)?[^\n|&]+\s*2>&1", full_text))
    if has_tee_exec or has_tee_2gt1:
        push("logging-dual-capture", "pass")
    else:
        push("logging-dual-capture", "fail",
             note="no `exec > >(tee -a $LOG) 2>&1` dual-capture idiom detected")

    # set-strict-mode (NOTE): `set -euo pipefail` (or any subset of -e/-u/-o pipefail)
    head_text = "".join(raw_lines[:30])
    has_strict = bool(re.search(r"^\s*set\s+-(?:[eu]+o?\s*(?:pipefail)?|euo\s+pipefail|o\s+pipefail)",
                                head_text, re.MULTILINE))
    if has_strict:
        push("set-strict-mode", "pass")
    else:
        push("set-strict-mode", "fail",
             note="`set -euo pipefail` (or equivalent) absent in first 30 lines")

    # genome-build-tag (WARNING): genomic file paths present but no build token
    var_strings = [str(v["value"]) for v in assigns.values()
                   if isinstance(v["value"], str)]
    has_genomic = any(GENOMIC_EXT_RE.search(s) for s in var_strings)
    has_tag     = any(GENOME_TOKEN_RE.search(s) for s in var_strings)
    if has_genomic and not has_tag:
        push("genome-build-tag", "fail",
             note=("genomic file path(s) detected in variables but no "
                   "build token (mm10/hg38/...) present"))
    else:
        push("genome-build-tag", "pass" if has_genomic else "n/a")

    return checks


SEVERITY_MAP = {
    "raw-data-write":           "BLOCKER",
    "hardcoded-contig":         "BLOCKER",
    "relative-paths-only":      "WARNING",
    "forbidden-variable-names": "WARNING",
    "genome-build-tag":         "WARNING",
    "logging-dual-capture":     "NOTE",
    "script-header-metadata":   "NOTE",
    "set-strict-mode":          "NOTE",
}

# Category assignment for the scored report. Mirrors parser_r / parser_py.
RULE_CATEGORIES = {
    "script-header-metadata":   "reproducibility",
    "logging-dual-capture":     "reproducibility",
    "set-strict-mode":          "reproducibility",
    "relative-paths-only":      "io",
    "raw-data-write":           "io",
    "forbidden-variable-names": "variables",
    "genome-build-tag":         "genomics",
    "hardcoded-contig":         "genomics",
}


def findings_from_checks(checks):
    out = []
    for c in checks:
        if c["status"] == "fail":
            sev = SEVERITY_MAP.get(c["rule"], "NOTE")
            out.append({"severity": sev, "rule": c["rule"],
                        "sites": c["evidence_sites"], "note": c["note"]})
        elif c["status"] == "pass":
            out.append({"severity": "OK", "rule": c["rule"],
                        "note": "compliance check passed: " + c["rule"]})
        # n/a checks don't produce findings
    return out


def grade_pct(p):
    if p is None: return "N/A"
    if p >= 0.90: return "A"
    if p >= 0.80: return "B"
    if p >= 0.70: return "C"
    if p >= 0.60: return "D"
    return "F"


def emit_report(root, report_dir):
    """Bash version of the scored audit report. Same format as parser_r /
    parser_py emit_report() — Headline / By category / Findings / Inventory.
    Skips Models / Dataframes / Pair-binding (bash doesn't populate them)."""
    os.makedirs(report_dir, exist_ok=True)

    cat_pass, cat_fail = {}, {}
    for chk in root["compliance_checks"]:
        cat = RULE_CATEGORIES.get(chk["rule"], "misc")
        if chk["status"] == "pass":
            cat_pass[cat] = cat_pass.get(cat, 0) + 1
        elif chk["status"] == "fail":
            cat_fail[cat] = cat_fail.get(cat, 0) + 1
    cats = sorted(set(cat_pass) | set(cat_fail))
    total_pass = sum(cat_pass.values())
    total_fail = sum(cat_fail.values())
    denom = total_pass + total_fail
    headline_pct = (total_pass / denom) if denom else None
    headline_grade = grade_pct(headline_pct)

    L = []
    L.append("# sciAuditor — Audit Report")
    L.append("")
    L.append("- **Analysis**: `{}`".format(root["script"]["path"]))
    L.append("- **Inferred at**: {}".format(root["script"]["inferred_at"]))
    L.append("- **Schema**: v{} · Layer A (static)".format(root["schema_version"]))
    L.append("")
    L.append("## Headline")
    L.append("")
    L.append("| Score | Grade |")
    L.append("|---|---|")
    if denom:
        L.append("| {} / {} ({:.0f}%) | **{}** |".format(
            total_pass, denom, headline_pct * 100, headline_grade))
    else:
        L.append("| 0 / 0 (—) | **N/A** |")
    L.append("")
    L.append("## By category")
    L.append("")
    L.append("| Category | Pass | Fail | %  | Grade |")
    L.append("|---|---:|---:|---:|---:|")
    for cat in cats:
        p = cat_pass.get(cat, 0); f_ = cat_fail.get(cat, 0)
        pct = (p / (p + f_)) if (p + f_) else None
        pct_str = "{:.0f}%".format(pct * 100) if pct is not None else "—"
        L.append("| {} | {} | {} | {} | {} |".format(
            cat, p, f_, pct_str, grade_pct(pct)))

    # Findings grouped by severity
    L.append(""); L.append("## Findings"); L.append("")
    for sev in ("BLOCKER", "WARNING", "NOTE", "OK"):
        hits = [x for x in root["audit_findings_preview"]
                if x["severity"] == sev]
        if not hits: continue
        L.append("### {} ({})".format(sev, len(hits)))
        L.append("")
        for h in hits:
            sites = h.get("sites") or h.get("evidence_sites") or []
            sites_str = " (L" + ", L".join(str(s) for s in sites) + ")" if sites else ""
            note = h.get("note") or ""
            L.append("- **{}**{} — {}".format(h["rule"], sites_str, note))
        L.append("")

    # Inventory — bash-specific (no inputs/outputs/models/dataframes)
    invocation = root.get("invocation")
    L.append("## Inventory")
    L.append("")
    L.append("- Shell variables: **{}**".format(
        len((root.get("config_interface") or {}).get("options") or [])))
    L.append("- Side effects: **{}**".format(len(root.get("side_effects") or [])))
    if invocation:
        L.append("- Invokes `{}` on `{}` (L{}) with {} `--flag $VAR` pair(s)".format(
            invocation.get("language"), invocation.get("script"),
            invocation.get("site"), len(invocation.get("flags") or [])))
    else:
        L.append("- Invocation: _no Rscript/python call detected (standalone shell)_")
    L.append("- Genome build declared: **{}**".format(
        root.get("genome_build_declared") or "_not declared_"))

    report_path = os.path.join(report_dir, "audit_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(L) + "\n")

    # findings.tsv
    tsv_path = os.path.join(report_dir, "audit_findings.tsv")
    with open(tsv_path, "w") as f:
        f.write("severity\trule\tsites\tnote\n")
        for fin in root["audit_findings_preview"]:
            sites = fin.get("sites") or fin.get("evidence_sites") or []
            sites_str = ",".join(str(s) for s in sites)
            note = (fin.get("note") or "").replace("\t", " ")
            f.write("{}\t{}\t{}\t{}\n".format(
                fin["severity"], fin["rule"], sites_str, note))

    return {
        "report":         report_path,
        "findings_tsv":   tsv_path,
        "headline_score": "{}/{} {}".format(total_pass, denom, headline_grade),
    }


def assemble(path, raw_lines):
    assigns = parse_assignments(raw_lines)
    side_effects = parse_side_effects(raw_lines)
    joined, starts = join_continuations(raw_lines)
    invocation = detect_invocation(joined, starts, assigns)
    checks = compliance_checks(raw_lines, assigns, side_effects, invocation)
    findings = findings_from_checks(checks)
    casetrack_appends = extract_casetrack_appends("".join(raw_lines), assigns=assigns)

    options = [
        {"name": name, "default": v["value"],
         "default_kind": v["default_kind"], "site": v["site"]}
        for name, v in assigns.items()
    ]

    # genome_build_declared: scan every resolved variable value for a build token
    var_strings = [str(v["value"]) for v in assigns.values()
                   if isinstance(v["value"], str)]
    declared = None
    for s in var_strings:
        m = GENOME_TOKEN_RE.search(s)
        if m:
            declared = m.group(1); break

    root = {
        "schema_version": "0.2",
        "analysis_unit": {"id": os.path.splitext(os.path.basename(path))[0],
                          "kind": "single"},
        "script": {
            "path":        path,
            "language":    "bash",
            "git_rev":     "<runtime>",
            "inferred_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "layers_used": ["static"],
        },
        "runtime_context": {
            "cwd_at_invocation": "<runtime>",
            "resolved_cwd":      "<runtime>",
            "host":              "<runtime>",
            "user":              "<runtime>",
        },
        "config_interface": {
            "framework": "shell_variables",
            "options":   options,
        },
        "inputs":  [],
        "outputs": [],
        "invocation":  invocation,
        "side_effects": side_effects,
        "environment": {"shell": "bash", "packages": None},
        "genome_build_declared": declared,
        "casetrack_appends":      casetrack_appends,
        "compliance_checks":      checks,
        "audit_findings_preview": findings,
        "unresolved": [{
            "kind": "round_2_bash_scope",
            "note": "round 2 bash: var assignments, side_effects, invocation, "
                    "7 compliance checks (2 BLOCKER / 3 WARNING / 2 NOTE); "
                    "no inputs/outputs/models/dataframes (launcher pattern)"
        }],
    }
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True, help="bash script to analyse")
    ap.add_argument("--output", "-o", default="-",
                    help="output YAML path, '-' for stdout")
    ap.add_argument("--report_dir", default=None,
                    help="emit audit_report.md + audit_findings.tsv into this dir")
    args = ap.parse_args()

    with open(args.input) as f:
        raw_lines = f.readlines()
    root = assemble(args.input, raw_lines)

    if args.output == "-":
        yaml.dump(root, sys.stdout, default_flow_style=False)
    else:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w") as f:
            yaml.dump(root, f, default_flow_style=False)
        sys.stderr.write(
            "[sciauditor_bash] wrote {} ({} vars, {} side_effects, "
            "{} invocation)\n".format(
                args.output, len(root["config_interface"]["options"]),
                len(root["side_effects"]),
                1 if root["invocation"] else 0))

    if args.report_dir:
        res = emit_report(root, args.report_dir)
        sys.stderr.write(
            "[sciauditor_bash] report: {}  findings_tsv: {}  headline: {}\n".format(
                res["report"], res["findings_tsv"], res["headline_score"]))


if __name__ == "__main__":
    main()
