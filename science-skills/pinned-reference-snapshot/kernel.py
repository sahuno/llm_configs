"""Helpers for pinned-reference-snapshot. See SKILL.md."""
import os
import hashlib
import datetime
import pandas as pd

MANIFEST_HEAD = ("file", "source", "n_records", "sha256", "resource_version", "exported_utc")


def sha256_file(path, chunk=1048576):
    """Content hash of a vendored snapshot file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def write_pin_manifest(entries, out_path=None, root=None, resource_version=None):
    """Build a pin manifest. entries: list of dicts with at least file and source.

    sha256 and exported_utc are filled in here; extra keys pass through as
    columns. Returns the frame and writes TSV when out_path is given.
    """
    if root is None:
        root = "."
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = []
    for e in entries:
        rec = dict(e)
        path = os.path.join(root, rec["file"])
        rec["sha256"] = sha256_file(path)
        rec.setdefault("exported_utc", stamp)
        if resource_version is not None:
            rec.setdefault("resource_version", resource_version)
        rows.append(rec)
    df = pd.DataFrame(rows)
    head = [c for c in MANIFEST_HEAD if c in df.columns]
    df = df[head + [c for c in df.columns if c not in head]]
    if out_path is not None:
        df.to_csv(out_path, sep="\t", index=False)
    return df


def verify_pin(manifest_path, root=None, strict=True):
    """Recompute every checksum in a manifest. Call this in the loader, not once."""
    if root is None:
        root = os.path.dirname(os.path.abspath(manifest_path))
    sep = "\t" if str(manifest_path).endswith((".tsv", ".tab", ".txt")) else ","
    man = pd.read_csv(manifest_path, sep=sep)
    rows = []
    for rec in man.to_dict("records"):
        path = os.path.join(root, rec["file"])
        if not os.path.exists(path):
            rows.append({"file": rec["file"], "ok": False, "reason": "missing"})
            continue
        got = sha256_file(path)
        rows.append({"file": rec["file"], "ok": got == rec["sha256"],
                     "reason": "" if got == rec["sha256"] else "sha256 %s != %s"
                     % (got[:12], str(rec["sha256"])[:12])})
    out = pd.DataFrame(rows)
    if strict and not out["ok"].all():
        raise RuntimeError("pin verification failed:\n" + out[~out["ok"]].to_string(index=False))
    return out


def change_ledger(old, new, key_cols, value_cols, call_col=None, tol=1e-12):
    """One row per unit comparing two pins, with a controlled change vocabulary."""
    keys = list(key_cols)
    vals = list(value_cols)
    cols = keys + vals + ([call_col] if call_col else [])
    a = old[[c for c in cols if c in old.columns]].copy()
    b = new[[c for c in cols if c in new.columns]].copy()
    m = a.merge(b, on=keys, how="outer", suffixes=("_old", "_new"), indicator=True)
    for c in vals:
        lo, hi = c + "_old", c + "_new"
        if lo in m.columns and hi in m.columns and pd.api.types.is_numeric_dtype(m[hi]):
            m[c + "_delta"] = m[hi] - m[lo]
    verdicts = []
    for rec in m.to_dict("records"):
        side = rec["_merge"]
        if side == "left_only":
            verdicts.append("DISAPPEARED")
            continue
        if side == "right_only":
            verdicts.append("NEW (absent before)")
            continue
        if call_col:
            co, cn = bool(rec.get(call_col + "_old")), bool(rec.get(call_col + "_new"))
            if cn and not co:
                verdicts.append("call GAINED")
                continue
            if co and not cn:
                verdicts.append("call LOST")
                continue
        moved = False
        for c in vals:
            lo, hi = rec.get(c + "_old"), rec.get(c + "_new")
            if isinstance(lo, float) and isinstance(hi, float):
                if pd.notna(lo) and pd.notna(hi) and abs(hi - lo) > tol:
                    moved = True
            elif lo != hi:
                moved = True
        verdicts.append("moved, call unchanged" if moved else "identical")
    m["change"] = verdicts
    return m.drop(columns=["_merge"])
