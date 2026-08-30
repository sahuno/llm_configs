"""Helpers for artifact-provenance-audit. See SKILL.md."""
import os
import re
import json
import hashlib
import pandas as pd

WRITE_CALLS = ("to_csv", "to_parquet", "to_excel", "to_feather", "savefig", "np.save",
               "np.savez", "json.dump", "write.csv", "write_csv", "write.table",
               "write_tsv", "write.tsv", "saveRDS", "save_rds", "ggsave", "fwrite",
               "writeLines", "write_xlsx", "to_hdf", "savez")
READ_CALLS = ("read_csv", "read_parquet", "read_excel", "read_feather", "read_table",
              "read_tsv", "np.load", "json.load", "read.csv", "read.table", "read.delim",
              "readRDS", "read_rds", "fread", "read_xlsx", "read_hdf", "imread")
SCAN_EXTS = (".py", ".R", ".r", ".ipynb", ".qmd", ".Rmd", ".rmd", ".sh")
HELPER_STOPLIST = ("main", "plot", "run", "run_all", "figure", "draw", "show", "render")
PATHLIKE = r"""['"]([^'"\s]*\.[A-Za-z0-9]{1,8})['"]"""


def source_lines(path):
    """Yield (lineno, text) for a script or notebook, transparently."""
    if path.endswith(".ipynb"):
        try:
            nb = json.load(open(path, encoding="utf-8"))
        except Exception:
            return []
        out = []
        n = 0
        for ci, cell in enumerate(nb.get("cells", [])):
            for line in cell.get("source", []):
                n += 1
                out.append((n, line.rstrip("\n"), ci))
        return out
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return []
    return [(i + 1, ln, None) for i, ln in enumerate(text.splitlines())]


def discover_io_helpers(root, exts=None):
    """Find project-local wrappers around file I/O (save_figure, read_data_tsv, ...).

    A repo with a house save helper is invisible to a fixed call list — every
    script looks read-only. Returns {"write": [...], "read": [...]}.
    """
    import ast
    if exts is None:
        exts = (".py", ".R", ".r")
    out = {"write": set(), "read": set()}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))
                       and d not in ("node_modules", "renv", "venv")]
        for fn in filenames:
            if not fn.endswith(tuple(exts)):
                continue
            full = os.path.join(dirpath, fn)
            try:
                text = open(full, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if fn.endswith(".py"):
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    body = ast.dump(node)
                    for direction, calls in (("write", WRITE_CALLS), ("read", READ_CALLS)):
                        for call in calls:
                            if "'" + call.split(".")[-1] + "'" in body:
                                out[direction].add(node.name)
            else:
                lines = text.splitlines()
                starts = [(i, re.match(r"\s*([A-Za-z._][\w.]*)\s*(<-|=)\s*function", ln))
                          for i, ln in enumerate(lines)]
                starts = [(i, m.group(1)) for i, m in starts if m]
                for j, (i, name) in enumerate(starts):
                    stop = starts[j + 1][0] if j + 1 < len(starts) else len(lines)
                    block = "\n".join(lines[i:stop])
                    for direction, calls in (("write", WRITE_CALLS), ("read", READ_CALLS)):
                        for call in calls:
                            if call + "(" in block:
                                out[direction].add(name)
    return {"write": sorted(out["write"] - set(WRITE_CALLS) - set(HELPER_STOPLIST)),
            "read": sorted(out["read"] - set(READ_CALLS) - set(HELPER_STOPLIST) - out["write"])}


def scan_producers(root, exts=None, extra_write=None, extra_read=None, include_helpers=False):
    """Scan one or more repo roots for file I/O calls. direction is write|read.

    include_helpers auto-adds every discover_io_helpers hit, which over-fires on
    generic names — prefer running discover_io_helpers, reading the list, and
    passing the real wrappers via extra_write / extra_read.
    """
    if exts is None:
        exts = SCAN_EXTS
    roots = [root] if isinstance(root, str) else list(root)
    writes, reads = list(WRITE_CALLS), list(READ_CALLS)
    helpers = {"write": [], "read": []}
    if include_helpers:
        for rt in roots:
            found = discover_io_helpers(rt)
            helpers["write"] += found["write"]
            helpers["read"] += found["read"]
    writes += list(extra_write or []) + helpers["write"]
    reads += list(extra_read or []) + helpers["read"]
    house = set(helpers["write"]) | set(helpers["read"]) | set(extra_write or []) | set(extra_read or [])
    rows = []
    for rt in roots:
      for dirpath, dirnames, filenames in os.walk(rt):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))
                       and d not in ("node_modules", "renv", "venv")]
        for fn in filenames:
            if not fn.endswith(tuple(exts)):
                continue
            full = os.path.join(dirpath, fn)
            for lineno, line, cell in source_lines(full):
                stripped = line.lstrip()
                if stripped.startswith("#") or re.match(r"\s*(def|[A-Za-z._][\w.]*\s*<-\s*function)", line):
                    continue
                for direction, calls in (("write", writes), ("read", reads)):
                    for call in calls:
                        if call + "(" not in line:
                            continue
                        targets = re.findall(PATHLIKE, line)
                        if not targets and call in house:
                            targets = [t for t in re.findall(r"""['"]([A-Za-z0-9][\w.\-/]{2,})['"]""", line)]
                        for target in targets:
                            rows.append({"script": os.path.relpath(full, rt),
                                         "lineno": lineno, "cell": cell,
                                         "direction": direction, "call": call,
                                         "target": os.path.basename(target),
                                         "via_helper": call in house})
    return pd.DataFrame(rows, columns=["script", "lineno", "cell", "direction",
                                       "call", "target", "via_helper"])


def match_artifacts_to_producers(filenames, scan):
    """Join artifact filenames against a scan_producers frame."""
    rows = []
    for fn in filenames:
        base = os.path.basename(str(fn))
        hit = scan[scan["target"] == base] if len(scan) else scan
        w = hit[hit["direction"] == "write"] if len(hit) else hit
        r = hit[hit["direction"] == "read"] if len(hit) else hit
        rows.append({"filename": base,
                     "n_writers": len(w), "n_readers": len(r),
                     "writers": "; ".join(sorted(set(w["script"]))) if len(w) else "",
                     "readers": "; ".join(sorted(set(r["script"]))) if len(r) else "",
                     "repo_orphan": len(w) == 0,
                     "blocks_reproduction": len(w) == 0 and len(r) > 0})
    return pd.DataFrame(rows)


def lineage_producers(version_ids, nudge=False):
    """Store-side producer status per version_id. Respect extraction_pending."""
    rows = []
    for vid in version_ids:
        rec = {"vid": vid, "has_code": False, "n_inputs": 0, "n_edges": None,
               "extraction_pending": None, "error": ""}
        try:
            g = host.lineage.graph(vid)
            rec["n_edges"] = len(g.get("edges", []))
            rec["extraction_pending"] = bool(g.get("extraction_pending", False))
        except Exception as exc:
            rec["error"] = "graph: %s" % exc
        if nudge or rec["extraction_pending"] or rec["n_edges"] == 0:
            try:
                lin = host.lineage[vid]
                rec["has_code"] = bool((lin.get("code") or "").strip())
                rec["n_inputs"] = len(lin.get("inputs") or [])
                rec["extraction_pending"] = bool(lin.get("extraction_pending", False))
            except Exception as exc:
                rec["error"] = (rec["error"] + " lineage: %s" % exc).strip()
        rows.append(rec)
    return pd.DataFrame(rows)


def diff_against_saved(reproduced, saved_path, key_cols=None, tol=1e-9):
    """Column-level diff of a reproduced frame against the saved artifact."""
    sep = "\t" if str(saved_path).endswith((".tsv", ".tab", ".txt")) else ","
    saved = pd.read_csv(saved_path, sep=sep)
    a, b = reproduced.copy(), saved.copy()
    if key_cols:
        a = a.set_index(list(key_cols)).sort_index()
        b = b.set_index(list(key_cols)).sort_index()
    rows = [{"column": "<row count>", "verdict": "match" if len(a) == len(b) else "MISMATCH",
             "detail": "%d vs %d" % (len(a), len(b))}]
    for col in sorted(set(a.columns) | set(b.columns)):
        if col not in a.columns or col not in b.columns:
            rows.append({"column": col, "verdict": "MISSING",
                         "detail": "only in " + ("reproduced" if col in a.columns else "saved")})
            continue
        x, y = a[col], b[col]
        if len(x) != len(y):
            rows.append({"column": col, "verdict": "MISMATCH", "detail": "length differs"})
            continue
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            d = (x.reset_index(drop=True) - y.reset_index(drop=True)).abs()
            n_bad = int((d > tol).sum())
            rows.append({"column": col,
                         "verdict": "match" if n_bad == 0 else "MISMATCH",
                         "detail": "max|d|=%.3g, %d cells over tol" % (d.max(), n_bad)})
        else:
            n_bad = int((x.reset_index(drop=True).astype(str)
                         != y.reset_index(drop=True).astype(str)).sum())
            rows.append({"column": col,
                         "verdict": "match" if n_bad == 0 else "MISMATCH",
                         "detail": "%d differing values" % n_bad})
    return pd.DataFrame(rows)

def stage_script_artifacts(dest, exts=None, project_id=None, limit=500):
    """Copy code artifacts out of the artifact store into a scannable directory.

    In this runtime the analysis code is often saved as artifacts rather than
    committed to the repo, so a repo-only scan reports every artifact as an
    orphan. Stage the scripts, then pass both roots to scan_producers.
    """
    import shutil
    if exts is None:
        exts = (".py", ".R", ".r", ".ipynb", ".qmd", ".Rmd", ".rmd", ".sh")
    os.makedirs(dest, exist_ok=True)
    kwargs = {"limit": limit}
    if project_id is not None:
        kwargs["project_id"] = project_id
    rows = []
    for art in host.artifacts(**kwargs)["artifacts"]:
        fn = art["filename"]
        if not fn.endswith(tuple(exts)):
            continue
        try:
            src = host.artifact_path(art["latest_version_id"])
            shutil.copyfile(src, os.path.join(dest, fn))
            rows.append({"filename": fn, "vid": art["latest_version_id"],
                         "bytes": art.get("size_bytes")})
        except Exception as exc:
            rows.append({"filename": fn, "vid": art["latest_version_id"],
                         "bytes": None, "error": str(exc)})
    return pd.DataFrame(rows)
