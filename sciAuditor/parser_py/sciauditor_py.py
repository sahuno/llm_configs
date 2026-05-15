#!/usr/bin/env python3
"""sciAuditor Python front-end (Layer A, static).

Read a Python analysis script and emit a v0.2 inferred YAML matching
sciAuditor/02_inference_design.md §4. Round-1 surface mirrors the R
parser's scope: config_interface (argparse), inputs (pandas reads +
open()), outputs (pandas writes), side_effects, stochastic_ops +
seed_policy, environment.packages, and the same compliance checks
(including the three BLOCKERs: raw-data-write, header-preserved,
hardcoded-contig).

Author: Samuel Ahuno / sciAuditor
Date:   2026-05-14
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from datetime import datetime

import yaml


# ---------------------------------------------------------------------------
# Pattern catalogues
# ---------------------------------------------------------------------------
READ_FNS = (
    "pd.read_csv", "pd.read_table", "pd.read_tsv", "pd.read_parquet",
    "pd.read_excel", "pd.read_pickle", "pd.read_hdf", "pd.read_json",
    "pd.read_feather", "pd.read_stata",
    "pandas.read_csv", "pandas.read_table", "pandas.read_parquet",
    "open", "gzip.open",
    "polars.read_csv", "pl.read_csv",
    "np.load", "numpy.load",
    "yaml.safe_load", "yaml.load", "json.load", "json.loads",
)
WRITE_FNS = (
    "to_csv", "to_tsv", "to_parquet", "to_excel", "to_pickle",
    "to_hdf", "to_json", "to_feather", "to_stata", "to_string",
    "savefig",
)
STOCHASTIC_FNS = (
    "random.random", "random.randint", "random.choice", "random.shuffle",
    "random.sample", "random.uniform", "random.normalvariate",
    "np.random.rand", "np.random.randn", "np.random.normal",
    "np.random.uniform", "np.random.randint", "np.random.choice",
    "np.random.shuffle", "np.random.permutation",
    "numpy.random.rand", "numpy.random.randn",
    # sklearn / scipy classes with stochastic fits
    "KMeans", "MiniBatchKMeans", "DBSCAN", "GaussianMixture",
    "TSNE", "UMAP", "RandomForestClassifier", "RandomForestRegressor",
    "train_test_split",
)
SEED_SETTER_FNS = ("random.seed", "np.random.seed", "numpy.random.seed",
                   "torch.manual_seed")
FORBIDDEN_NAMES = ("counts", "results", "mean", "median", "sum", "conditions")
CONTIG_RE = re.compile(r"""["']chr([0-9]+|[XYM]|MT)["']""")
ABSOLUTE_PATH_RE = re.compile(r"^[/~]")
# Standard-library modules — used to split env.packages
STDLIB = {
    "abc", "argparse", "ast", "collections", "contextlib", "copy", "csv",
    "datetime", "enum", "errno", "functools", "gzip", "hashlib", "io",
    "itertools", "json", "logging", "math", "multiprocessing", "operator",
    "os", "pathlib", "pickle", "random", "re", "shutil", "signal",
    "socket", "string", "struct", "subprocess", "sys", "tempfile",
    "threading", "time", "traceback", "typing", "unittest", "uuid",
    "warnings", "weakref", "xml", "zipfile",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def call_name(node: ast.Call) -> str | None:
    """Return a dotted-string name for `node.func`, or None if not extractable."""
    f = node.func
    parts = []
    while True:
        if isinstance(f, ast.Attribute):
            parts.append(f.attr)
            f = f.value
        elif isinstance(f, ast.Name):
            parts.append(f.id)
            break
        else:
            return None
    return ".".join(reversed(parts))


def const_value(node):
    """Best-effort literal extraction. Returns None if not a literal."""
    if isinstance(node, ast.Constant):     # 3.8+ unifies Str / Num / NameConstant
        return node.value
    # 3.6 / 3.7 backstop (those node classes are gone in 3.14):
    for cls_name, attr in (("Str", "s"), ("Num", "n"), ("NameConstant", "value")):
        cls = getattr(ast, cls_name, None)
        if cls is not None and isinstance(node, cls):
            return getattr(node, attr)
    return None


def expr_text(node, max_len: int = 200) -> str:
    """Round-trip an AST node to source text via ast.unparse (3.9+) or
    a fallback via str(ast.dump(...)). Capped for readability."""
    try:
        s = ast.unparse(node)  # type: ignore[attr-defined]
    except AttributeError:
        s = ast.dump(node)
    s = " ".join(s.split())
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def get_kw(node: ast.Call, name: str):
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def get_arg(node: ast.Call, pos: int):
    return node.args[pos] if pos < len(node.args) else None


def path_template(node, assigns: dict) -> tuple[str, str]:
    """Map an AST node representing a path argument to (template, confidence)."""
    if node is None:
        return "?", "low"
    v = const_value(node)
    if isinstance(v, str):
        return v, "high"
    if isinstance(node, ast.Name):
        nm = node.id
        if nm in assigns:
            return assigns[nm], "high"
        return "{" + nm + "}", "medium"
    if isinstance(node, ast.Attribute):
        return "{" + expr_text(node, 60) + "}", "high"
    if isinstance(node, ast.JoinedStr):  # f-string
        parts = []
        for v in node.values:
            cv = const_value(v)
            if isinstance(cv, str):
                parts.append(cv)
            elif isinstance(v, ast.FormattedValue):
                parts.append("{" + expr_text(v.value, 40) + "}")
            else:
                parts.append("?")
        return "".join(parts), "medium"
    if isinstance(node, ast.Call) and call_name(node) == "Path":
        if node.args:
            inner, conf = path_template(node.args[0], assigns)
            return inner, conf
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div,)):
        # Path("...") / "subpath"
        left, lc = path_template(node.left, assigns)
        right, rc = path_template(node.right, assigns)
        return f"{left}/{right}", "medium"
    return expr_text(node, 80), "low"


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------
def collect_simple_assigns(tree: ast.Module) -> dict:
    """Map name -> literal string for simple `NAME = "literal"` at top level."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                v = const_value(node.value)
                if isinstance(v, str):
                    out[tgt.id] = v
    return out


def walk_calls(tree: ast.Module):
    """Yield every (Call node, top-level enclosing statement line) in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node, getattr(node, "lineno", None)


def collect_packages(tree: ast.Module) -> list:
    out, seen = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                if base not in seen:
                    seen.add(base); out.append(base)
        elif isinstance(node, ast.ImportFrom):
            base = (node.module or "").split(".")[0]
            if base and base not in seen:
                seen.add(base); out.append(base)
    return out


def collect_config_interface(tree: ast.Module) -> dict:
    """argparse `add_argument(...)` calls into v0.2 config_interface block."""
    options = []
    for node, line in walk_calls(tree):
        if call_name(node) is None or not call_name(node).endswith("add_argument"):
            continue
        # First positional arg is the flag(s)
        if not node.args:
            continue
        first = node.args[0]
        flag = const_value(first)
        if not isinstance(flag, str):
            continue
        # Long form preferred if multiple flag args
        for extra in node.args[1:]:
            ev = const_value(extra)
            if isinstance(ev, str) and ev.startswith("--"):
                flag = ev
                break
        type_kw    = get_kw(node, "type")
        default_kw = get_kw(node, "default")
        help_kw    = get_kw(node, "help")
        required_kw = get_kw(node, "required")
        type_text = expr_text(type_kw, 40) if type_kw is not None else None
        default_val = const_value(default_kw) if default_kw is not None else None
        default_kind = None
        if isinstance(default_val, str) and default_val:
            default_kind = "absolute" if ABSOLUTE_PATH_RE.match(default_val) else "relative"
        options.append({
            "name":         flag,
            "type":         type_text,
            "default":      default_val,
            "default_kind": default_kind,
            "required":     bool(const_value(required_kw)) if required_kw is not None else None,
            "help":         const_value(help_kw),
            "site":         line,
        })
    return {"framework": "argparse" if options else "none", "options": options}


def collect_inputs(tree: ast.Module, assigns: dict) -> list:
    out = []
    for node, line in walk_calls(tree):
        nm = call_name(node)
        if nm is None or nm not in READ_FNS:
            continue
        p_arg = get_kw(node, "filepath_or_buffer") or get_kw(node, "path") \
                or get_kw(node, "file") or get_arg(node, 0)
        tmpl, conf = path_template(p_arg, assigns)
        header_kw = get_kw(node, "header")
        header_val = const_value(header_kw) if header_kw is not None else None
        header_dropped = header_val is None and header_kw is not None
        # pandas: header=None means "no header"; bool-like behaviour
        if isinstance(header_val, (int, type(None))) and header_val is None and header_kw is not None:
            header_dropped = True
        out.append({
            "id":            "input_{:02d}".format(len(out) + 1),
            "path_template": tmpl,
            "kind":          "tabular" if nm.startswith(("pd.", "pandas.")) else "file",
            "format":        guess_format_from_fn(nm, tmpl),
            "read_call":     {"fn": nm, "site": line},
            "header_dropped": header_dropped,
            "resolution_confidence": conf,
        })
    return out


def collect_outputs(tree: ast.Module, assigns: dict) -> list:
    out = []
    for node, line in walk_calls(tree):
        nm = call_name(node)
        if nm is None:
            continue
        # Method calls like df.to_csv — call_name returns the dotted path
        last = nm.rsplit(".", 1)[-1]
        if last not in WRITE_FNS:
            continue
        p_arg = get_kw(node, "path_or_buf") or get_kw(node, "path") \
                or get_kw(node, "fname") or get_arg(node, 0)
        tmpl, conf = path_template(p_arg, assigns)
        sep_kw = get_kw(node, "sep")
        sep_val = const_value(sep_kw) if sep_kw is not None else None
        index_kw = get_kw(node, "index")
        index_val = const_value(index_kw) if index_kw is not None else None
        out.append({
            "id":            "output_{:02d}".format(len(out) + 1),
            "path_template": tmpl,
            "kind":          "tabular" if last in ("to_csv", "to_tsv", "to_parquet") else "artifact",
            "format":        guess_format_from_fn(nm, tmpl),
            "write_call":    {"fn": nm, "site": line},
            "write_mode":    "overwrite",
            "write_params":  {"sep": sep_val, "index": index_val},
            "resolution_confidence": conf,
        })
    return out


def guess_format_from_fn(fn: str, path: str) -> str:
    last = fn.rsplit(".", 1)[-1]
    if last in ("read_csv", "to_csv"):
        return "csv" if not (path and path.endswith((".tsv", ".tab"))) else "tsv"
    if last in ("read_table", "to_tsv"):  return "tsv"
    if last in ("read_parquet", "to_parquet"): return "parquet"
    if last in ("read_excel", "to_excel"):     return "xlsx"
    if last in ("savefig",):                   return "multi"
    if last in ("load",):                      return "npy"
    if "yaml" in fn:                            return "yaml"
    if "json" in fn:                            return "json"
    if path and "." in path:
        return path.rsplit(".", 1)[-1].lower()
    return "unknown"


def collect_side_effects(tree: ast.Module) -> list:
    out = []
    for node, line in walk_calls(tree):
        nm = call_name(node)
        if nm is None: continue
        if nm in ("os.makedirs", "os.mkdir") or nm.endswith(".mkdir"):
            p_arg = get_arg(node, 0)
            tmpl, _ = path_template(p_arg, {})
            out.append({"site": line, "kind": "mkdir", "paths": [tmpl]})
        elif nm == "os.chdir":
            out.append({"site": line, "kind": "setwd",
                        "detail": expr_text(node, 120)})
        elif nm == "os.environ.update" or nm.endswith("setenv"):
            out.append({"site": line, "kind": "env_set",
                        "detail": expr_text(node, 120)})
        elif nm.endswith(".setLevel") or nm.endswith(".basicConfig"):
            out.append({"site": line, "kind": "logging_config",
                        "detail": expr_text(node, 120)})
    return out


def collect_stochastic_ops(tree: ast.Module) -> list:
    seed_pairs = []
    stoch = []
    for node, line in walk_calls(tree):
        nm = call_name(node)
        if nm is None: continue
        if nm in SEED_SETTER_FNS:
            v = get_arg(node, 0)
            val = const_value(v)
            seed_pairs.append({"line": line,
                               "value": int(val) if isinstance(val, int) else None})
        elif nm in STOCHASTIC_FNS or nm.rsplit(".", 1)[-1] in STOCHASTIC_FNS:
            # Check for `random_state=` kwarg (treat as inline seed)
            rs = get_kw(node, "random_state")
            inline_seed = const_value(rs) if rs is not None else None
            stoch.append({"site": line, "fn": nm,
                          "inline_random_state": inline_seed})
    # Mark each stochastic op with whether a set_seed call precedes it
    seed_lines = sorted(p["line"] for p in seed_pairs if p["line"] is not None)
    for s in stoch:
        before = [l for l in seed_lines if l <= (s["site"] or 0)]
        s["seed_set"] = bool(before) or (s["inline_random_state"] is not None)
        s["seed_set_evidence_site"] = before[-1] if before else None
        s["seed_value"] = next(
            (p["value"] for p in reversed(seed_pairs)
             if p["line"] is not None and p["line"] <= (s["site"] or 0)),
            s["inline_random_state"],
        )
    return stoch, seed_pairs


def collect_hardcoded_data(tree: ast.Module, raw_lines: list) -> list:
    out = []
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        rhs = node.value
        # `NAME = [<literals>]` or `(...)` or `{...}`
        if isinstance(rhs, (ast.List, ast.Tuple, ast.Set)):
            literals = [const_value(elt) for elt in rhs.elts]
            literals = [v for v in literals if isinstance(v, str)]
            if len(literals) >= 5:
                kind = classify_strings(literals)
                cits = extract_citations_near(node.lineno, raw_lines)
                out.append({
                    "id":        tgt.id,
                    "site":      str(node.lineno),
                    "kind":      kind,
                    "count":     len(literals),
                    "values":    literals if len(literals) <= 20 else None,
                    "citations": cits or None,
                })
    return out


def classify_strings(values):
    if all(re.match(r"^chr([0-9]+|[XYM]+|MT)$", v) for v in values):
        return "contig_list"
    sep_share = sum(bool(re.search(r"[.\-_]", v)) for v in values) / len(values)
    num_share = sum(bool(re.search(r"\d", v)) for v in values) / len(values)
    if sep_share >= 0.6 and num_share > 0:
        return "sample_id_list"
    gene_like = sum(bool(re.match(r"^[A-Za-z][A-Za-z0-9.\-]{1,11}$", v)) for v in values) / len(values)
    if gene_like >= 0.85:
        return "curated_geneset"
    return "string_list"


def extract_citations_near(line_start, raw_lines, lookback=10):
    if line_start is None or line_start <= 1: return []
    s = max(0, line_start - 1 - lookback)
    block = raw_lines[s : line_start - 1]
    hits = []
    for ln in block:
        if re.search(r"\bPMID|pubmed", ln, re.IGNORECASE):
            hits += ["PMID:" + n for n in re.findall(r"\d{6,}", ln)]
        hits += ["DOI:" + d for d in re.findall(r"10\.\d+/[^\s,;]+", ln)]
    seen, uniq = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return uniq


# ---------------------------------------------------------------------------
# Compliance checks (mirrors R parser's set)
# ---------------------------------------------------------------------------
def compliance_checks(tree, raw_lines, config_iface, stoch_ops, inputs, outputs):
    checks = []
    def push(rule, status, evidence_sites=None, note=None):
        checks.append({"rule": rule, "status": status,
                       "evidence_sites": evidence_sites or [], "note": note})

    # Header check looks at both #-prefixed comments in the first 15 lines
    # AND the module docstring (Python convention puts metadata in the docstring).
    head_text = "\n".join(raw_lines[:15])
    docstring = ast.get_docstring(tree) or ""
    haystack = head_text + "\n" + docstring
    has_author  = bool(re.search(r"(?i)\b(author|name)\s*:", haystack))
    has_date    = bool(re.search(r"(?i)(date\s*:|\d{4}-\d{2}-\d{2})", haystack))
    has_purpose = bool(re.search(r"(?i)\b(purpose|description)\s*:", haystack)) or bool(docstring)
    header_pass = has_author and (has_date or has_purpose)
    push("script-header-metadata",
         "pass" if header_pass else "fail",
         evidence_sites=[1],
         note=None if header_pass else "missing Author/Name + Date/Purpose in script header or docstring")

    # relative-paths-only — any argparse default that resolves absolute
    abs_opts = [o for o in config_iface["options"]
                if o.get("default_kind") == "absolute"]
    push("relative-paths-only",
         "fail" if abs_opts else "pass",
         evidence_sites=[o["site"] for o in abs_opts],
         note="{} CLI defaults are absolute paths".format(len(abs_opts)) if abs_opts else None)

    # forbidden-variable-names
    forbid_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in FORBIDDEN_NAMES:
                    forbid_hits.append({"name": tgt.id, "site": tgt.lineno})
    push("forbidden-variable-names",
         "fail" if forbid_hits else "pass",
         evidence_sites=[h["site"] for h in forbid_hits],
         note=("collisions: " + ",".join(sorted({h["name"] for h in forbid_hits})))
              if forbid_hits else None)

    # seed-coverage
    if not stoch_ops:
        push("seed-coverage", "n/a", note="no stochastic ops detected")
    else:
        unseeded = [s for s in stoch_ops if not s.get("seed_set")]
        if unseeded:
            push("seed-coverage", "fail",
                 evidence_sites=[s["site"] for s in unseeded],
                 note="{}/{} stochastic ops have no reaching seed".format(
                     len(unseeded), len(stoch_ops)))
        else:
            push("seed-coverage", "pass",
                 evidence_sites=[s["site"] for s in stoch_ops])

    # logging-dual-capture: presence of logging.FileHandler + StreamHandler
    has_filehandler   = any(call_name(n) and call_name(n).endswith("FileHandler")
                            for n, _ in walk_calls(tree))
    has_streamhandler = any(call_name(n) and call_name(n).endswith("StreamHandler")
                            for n, _ in walk_calls(tree))
    if has_filehandler and has_streamhandler:
        push("logging-dual-capture", "pass")
    elif has_filehandler or has_streamhandler:
        push("logging-dual-capture", "fail",
             note="partial: need both FileHandler and StreamHandler")
    else:
        push("logging-dual-capture", "fail",
             note="no FileHandler+StreamHandler logging detected")

    # ===== BLOCKERs =====

    # raw-data-write
    raw_writes = [o for o in outputs
                  if re.search(r"(^|/)data/raw/|(^|/)raw/", o["path_template"] or "")]
    if raw_writes:
        push("raw-data-write", "fail",
             evidence_sites=[o["write_call"]["site"] for o in raw_writes],
             note="{} output(s) resolve under data/raw/; raw data is immutable".format(len(raw_writes)))
    else:
        push("raw-data-write", "pass")

    # header-preserved (pandas: header=None / explicit drop)
    header_dropped = [i for i in inputs if i.get("header_dropped")]
    if header_dropped:
        push("header-preserved", "fail",
             evidence_sites=[i["read_call"]["site"] for i in header_dropped],
             note="{} read call(s) drop headers explicitly (header=None)".format(len(header_dropped)))
    else:
        push("header-preserved", "pass")

    # hardcoded-contig (regex on non-comment lines)
    hits = []
    for i, ln in enumerate(raw_lines, start=1):
        s = ln.strip()
        if s.startswith("#"): continue
        # Strip trailing comment
        code = re.sub(r"#[^\"']*$", "", ln)
        if CONTIG_RE.search(code):
            hits.append(i)
    if hits:
        push("hardcoded-contig", "fail",
             evidence_sites=hits,
             note="{} line(s) contain hardcoded contig literals".format(len(hits)))
    else:
        push("hardcoded-contig", "pass")

    return checks


SEVERITY_MAP = {
    "raw-data-write":           "BLOCKER",
    "header-preserved":         "BLOCKER",
    "hardcoded-contig":         "BLOCKER",
    "relative-paths-only":      "WARNING",
    "forbidden-variable-names": "WARNING",
    "seed-coverage":            "WARNING",
    "genome-build-tag":         "WARNING",
    "logging-dual-capture":     "NOTE",
    "script-header-metadata":   "NOTE",
}

# Category assignment for the scored report (mirrors parser_r RULE_CATEGORIES)
RULE_CATEGORIES = {
    "script-header-metadata":   "reproducibility",
    "logging-dual-capture":     "reproducibility",
    "seed-coverage":            "reproducibility",
    "seed-policy":              "reproducibility",
    "relative-paths-only":      "io",
    "raw-data-write":           "io",
    "header-preserved":         "io",
    "forbidden-variable-names": "variables",
    "genome-build-tag":         "genomics",
    "hardcoded-contig":         "genomics",
}


def grade_pct(p):
    if p is None:
        return "N/A"
    if p >= 0.90: return "A"
    if p >= 0.80: return "B"
    if p >= 0.70: return "C"
    if p >= 0.60: return "D"
    return "F"


def emit_report(root, report_dir):
    """Emit audit_report.md + audit_findings.tsv. Mirrors parser_r's
    emit_report() byte-for-byte where possible so multi-language audits
    look identical."""
    os.makedirs(report_dir, exist_ok=True)

    # Per-category pass/fail counts (compliance_checks)
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
        if not hits:
            continue
        L.append("### {} ({})".format(sev, len(hits)))
        L.append("")
        for h in hits:
            sites = h.get("sites") or h.get("evidence_sites") or []
            sites_str = " (L" + ", L".join(str(s) for s in sites) + ")" if sites else ""
            note = h.get("note") or ""
            L.append("- **{}**{} — {}".format(h["rule"], sites_str, note))
        L.append("")

    # Inventory
    sp  = root.get("seed_policy") or {}
    cov = sp.get("coverage") or {}
    hc  = root.get("hardcoded_data") or []
    L.append("## Inventory")
    L.append("")
    L.append("- Inputs: **{}**".format(len(root["inputs"])))
    L.append("- Outputs: **{}**".format(len(root["outputs"])))
    L.append("- Models: **{}**".format(len(root.get("models") or [])))
    L.append("- Dataframes: **{}**".format(len(root.get("dataframes") or [])))
    L.append("- Stochastic ops: **{}** ({} seeded, {} unseeded)".format(
        len(root.get("stochastic_ops") or []),
        cov.get("seeded", 0), cov.get("unseeded", 0)))
    L.append("- Hardcoded blocks: **{}**".format(len(hc)))
    L.append("- Organism inferred: **{}**".format(
        root.get("organism_inferred") or "not detected"))
    L.append("- Genome build declared: **{}**".format(
        root.get("genome_build_declared") or "_not declared_"))

    # Models section
    if root.get("models"):
        L.append(""); L.append("## Models"); L.append("")
        for m in root["models"]:
            L.append("- `{}` (L{}) — `{}` design `{}`".format(
                m.get("id"), m.get("site") or "?",
                m.get("fn"), m.get("formula") or "?"))
            if m.get("contrasts"):
                cn = ", ".join("`{}`".format(c["id"]) for c in m["contrasts"])
                L.append("  - contrasts: " + cn)

    # Pair binding section
    pu = root.get("pair_unit")
    if pu:
        bindings = pu.get("binding") or []
        L.append(""); L.append("## Pair binding"); L.append("")
        L.append("- **Launcher**: `{}`".format(pu["launcher"]["path"]))
        L.append("- **Analysis**: `{}`".format(pu["analysis"]["path"]))
        L.append("- **Effective cwd at analysis**: `{}`".format(
            pu.get("effective_cwd_at_analysis") or "_not detected_"))
        L.append("")
        L.append("**Bindings ({}):**".format(len(bindings)))
        L.append("")
        L.append("| Launcher var | Analysis flag | Resolved value | Sites |")
        L.append("|---|---|---|---|")
        for b in bindings:
            val = str(b.get("value_resolved", ""))
            if len(val) > 60:
                val = val[:57] + "..."
            L.append("| `{}` | `{}` | `{}` | {} |".format(
                b.get("launcher_var", "?"), b.get("analysis_flag", "?"),
                val, b.get("site", "?")))

    report_path = os.path.join(report_dir, "audit_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(L) + "\n")

    # findings.tsv for CI
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


def findings_from_compliance(checks):
    out = []
    for c in checks:
        if c["status"] == "fail":
            sev = SEVERITY_MAP.get(c["rule"], "NOTE")
            out.append({"severity": sev, "rule": c["rule"],
                        "sites": c["evidence_sites"], "note": c["note"]})
        elif c["status"] == "pass":
            out.append({"severity": "OK", "rule": c["rule"],
                        "note": c.get("note") or ("compliance check passed: " + c["rule"])})
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def assemble(path, raw_lines, tree):
    assigns = collect_simple_assigns(tree)
    packages = collect_packages(tree)
    config_iface = collect_config_interface(tree)
    inputs = collect_inputs(tree, assigns)
    outputs = collect_outputs(tree, assigns)
    side_effects = collect_side_effects(tree)
    stoch_ops, seed_pairs = collect_stochastic_ops(tree)
    hardcoded = collect_hardcoded_data(tree, raw_lines)
    checks = compliance_checks(tree, raw_lines, config_iface, stoch_ops, inputs, outputs)
    findings = findings_from_compliance(checks)

    # seed_policy summary
    if not stoch_ops:
        seed_policy = {"declared_value": None,
                       "coverage": {"stochastic_ops": 0, "seeded": 0, "unseeded": 0},
                       "severity": "n/a"}
    else:
        seeded = sum(1 for s in stoch_ops if s.get("seed_set"))
        seed_vals = sorted({s.get("seed_value") for s in stoch_ops
                            if s.get("seed_value") is not None})
        declared = seed_vals[0] if len(seed_vals) == 1 else None
        divergent = declared is not None and declared != 42
        seed_policy = {
            "declared_value":               declared,
            "multiple_values_observed":     seed_vals if len(seed_vals) > 1 else None,
            "coverage":                      {"stochastic_ops": len(stoch_ops),
                                              "seeded": seeded,
                                              "unseeded": len(stoch_ops) - seeded},
            "divergence_from_claude_default": divergent,
            "severity":                      "WARNING" if seeded < len(stoch_ops)
                                              else ("NOTE" if divergent else "OK"),
            "note": ("seed={} used across {} stochastic ops; CLAUDE.md default is 42".format(
                declared, len(stoch_ops))) if divergent else None,
        }

    # organism / genome inference (Python lacks the org.*.eg.db hook;
    # do a coarse check via path tokens)
    all_paths = [i["path_template"] or "" for i in inputs] + \
                [o["path_template"] or "" for o in outputs]
    gb_tokens = ("mm10", "mm39", "GRCm39", "hg38", "GRCh38", "hg19",
                 "GRCh37", "t2t", "chm13")
    declared = next((t for t in gb_tokens if any(t in p for p in all_paths)), None)

    # genome-build-tag finding is only emitted if we suspect genomic data
    # AND no tag is declared. Python parser uses a much weaker heuristic
    # than R (no org.*.eg.db package signal). For round 1: emit a NOTE
    # only when at least one path contains "bedmethyl" / "bed" / ".bam" /
    # ".vcf" but no genome tag.
    genomic_paths = [p for p in all_paths
                     if re.search(r"\.(bed|bedmethyl|bam|vcf|gff|gtf)(\.gz)?$", p)]
    if not declared and genomic_paths:
        checks.append({"rule": "genome-build-tag", "status": "fail",
                       "evidence_sites": [],
                       "note": "no genome build token in inputs/outputs; "
                                "{} apparently-genomic file(s) detected".format(
                                    len(genomic_paths))})
        findings.append({"severity": "WARNING", "rule": "genome-build-tag",
                         "sites": [],
                         "note": "no genome build token in inputs/outputs"})

    # Seed-policy auto-finding
    if seed_policy["severity"] in ("NOTE", "WARNING"):
        findings.append({"severity": seed_policy["severity"],
                         "rule": "seed-policy",
                         "note": seed_policy.get("note") or "see seed_policy block"})

    root = {
        "schema_version": "0.2",
        "analysis_unit":  {"id": os.path.splitext(os.path.basename(path))[0],
                           "kind": "single"},
        "pair_unit":      None,
        "script": {
            "path":        path,
            "language":    "python",
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
        "config_interface": config_iface,
        "inputs":           inputs,
        "outputs":          outputs,
        "package_resources": None,
        "env_vars_read":    [],
        "env_vars_written": [],
        "dataframes":       [],
        "transformations":  [],
        "models":           [],
        "figures":          [],
        "stochastic_ops":   stoch_ops,
        "seed_policy":      seed_policy,
        "functions_defined": None,
        "hardcoded_data":   hardcoded or None,
        "external_binaries": [],
        "driver_pattern":   None,
        "validation":       None,
        "side_effects":     side_effects,
        "environment": {"python_packages": packages, "container": None},
        "organism_inferred":      None,
        "genome_build_declared":  declared,
        "compliance_checks":      checks,
        "audit_findings_preview": findings,
        "unresolved": [{
            "kind": "round_1_python_scope",
            "note": "round 1 python: argparse, pandas I/O, side_effects, seed_policy, "
                    "hardcoded_data, five compliance checks (incl. 3 BLOCKERs). "
                    "dataframes[]/transformations[]/models[]/figures[]/functions_defined[] "
                    "deferred."
        }],
    }
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--output", "-o", default="-")
    ap.add_argument("--report_dir", default=None,
                    help="emit audit_report.md + audit_findings.tsv into this dir")
    args = ap.parse_args()

    with open(args.input) as f:
        raw_lines = f.readlines()
    tree = ast.parse("".join(raw_lines), filename=args.input)
    root = assemble(args.input, raw_lines, tree)

    if args.output == "-":
        yaml.dump(root, sys.stdout, default_flow_style=False, sort_keys=False)
    else:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w") as f:
            yaml.dump(root, f, default_flow_style=False, sort_keys=False)
        sys.stderr.write(
            "[sciauditor_py] wrote {} ({} inputs, {} outputs, {} findings)\n".format(
                args.output, len(root["inputs"]), len(root["outputs"]),
                len(root["audit_findings_preview"])))

    if args.report_dir:
        res = emit_report(root, args.report_dir)
        sys.stderr.write(
            "[sciauditor_py] report: {}  findings_tsv: {}  headline: {}\n".format(
                res["report"], res["findings_tsv"], res["headline_score"]))


if __name__ == "__main__":
    main()
