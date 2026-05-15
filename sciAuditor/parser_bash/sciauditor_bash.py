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


def compliance_checks(raw_lines, assigns):
    head_comments = [ln for ln in raw_lines[:10] if ln.strip().startswith("#")]
    has_author  = any(re.search(r'(?i)(^|[^a-z])(author|name)\s*:', h) for h in head_comments)
    has_date    = any(re.search(r'(?i)date|\d{4}-\d{2}-\d{2}', h) for h in head_comments)
    has_purpose = any(re.search(r'(?i)purpose|description', h) for h in head_comments)
    header_pass = has_author and (has_date or has_purpose)
    abs_vars    = [v for v in assigns.values() if v["default_kind"] == "absolute"]

    checks = [
        {
            "rule": "script-header-metadata",
            "status": "pass" if header_pass else "fail",
            "evidence_sites": [1] if head_comments else [],
            "note": None if header_pass else "missing Author/Date/Purpose in first 10 comments",
        },
        {
            "rule": "relative-paths-only",
            "status": "fail" if abs_vars else "pass",
            "evidence_sites": [v["site"] for v in abs_vars],
            "note": "{} variables resolve to absolute paths".format(len(abs_vars))
                    if abs_vars else None,
        },
    ]
    return checks


def findings_from_checks(checks):
    out = []
    for c in checks:
        if c["status"] == "fail":
            sev = {"script-header-metadata": "NOTE"}.get(c["rule"], "WARNING")
            out.append({"severity": sev, "rule": c["rule"],
                        "sites": c["evidence_sites"], "note": c["note"]})
        elif c["status"] == "pass":
            out.append({"severity": "OK", "rule": c["rule"],
                        "note": "compliance check passed: " + c["rule"]})
    return out


def assemble(path, raw_lines):
    assigns = parse_assignments(raw_lines)
    side_effects = parse_side_effects(raw_lines)
    joined, starts = join_continuations(raw_lines)
    invocation = detect_invocation(joined, starts, assigns)
    checks = compliance_checks(raw_lines, assigns)
    findings = findings_from_checks(checks)

    options = [
        {"name": name, "default": v["value"],
         "default_kind": v["default_kind"], "site": v["site"]}
        for name, v in assigns.items()
    ]

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
        "compliance_checks":      checks,
        "audit_findings_preview": findings,
        "unresolved": [{
            "kind": "round_1_bash_scope",
            "note": "round 1 bash: var assignments, mkdir/cd/export/set/source "
                    "side_effects, single-shot invocation detection, two "
                    "compliance checks"
        }],
    }
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True, help="bash script to analyse")
    ap.add_argument("--output", "-o", default="-",
                    help="output YAML path, '-' for stdout")
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


if __name__ == "__main__":
    main()
