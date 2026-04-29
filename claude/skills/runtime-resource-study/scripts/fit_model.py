#!/usr/bin/env python3
# Author: claude (skill bundled)
# Date: 2026-04-29
# Purpose: Fit wall_s ~ N (and optionally + file_size) and peak_rss ~ N. Run variance
# partitioning (between-host vs within-condition vs residual). If a separate validation
# CSV is supplied, compute out-of-sample prediction error and decide whether to recommend
# the 1-term or 2-term model. Output: model.yaml.
#
# Usage:
#   python fit_model.py --csv <stage5/benchmark.csv> [--validation-csv <stage6/benchmark.csv>] --output model.yaml
#
# Optional: --variance-partition --rss-cap <GB>

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


def read_csv_dict(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def fit_linear(X, y):
    """Least-squares fit y = X @ coefs. Returns coefs, predicted, R²."""
    coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coefs
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return coefs, pred, r2


def variance_partition(rows):
    """Crude variance partition: between-condition, between-host, residual.
    Without statsmodels we approximate with sum-of-squares decomposition.
    For a proper mixed-effects fit, use the R recipe in references/analysis_recipes.md."""
    walls = np.array([float(r["wall_s"]) for r in rows])
    grand = walls.mean()
    total_ss = np.sum((walls - grand) ** 2)

    # Group by condition (a tuple of factor levels) — pull from common samtools-sort columns
    factor_keys = ["threads", "mem_per_thread", "compression_level"]
    cond_keys = [tuple(r.get(k, "") for k in factor_keys) for r in rows]
    unique_conds = list(set(cond_keys))
    cond_means = {c: np.mean([float(r["wall_s"]) for r, ck in zip(rows, cond_keys) if ck == c])
                  for c in unique_conds}
    cond_ss = sum((cond_means[ck] - grand) ** 2 for ck in cond_keys)

    # Group by host
    host_keys = [r.get("host", "") for r in rows]
    unique_hosts = list(set(host_keys))
    host_means = {h: np.mean([float(r["wall_s"]) for r, hk in zip(rows, host_keys) if hk == h])
                  for h in unique_hosts}
    host_ss = sum((host_means[hk] - grand) ** 2 for hk in host_keys)

    residual_ss = total_ss - cond_ss - host_ss
    if residual_ss < 0:
        residual_ss = 0    # numerical artefact when groups overlap
    return {
        "condition_pct": 100 * cond_ss / total_ss if total_ss > 0 else 0,
        "host_pct":      100 * host_ss / total_ss if total_ss > 0 else 0,
        "residual_pct":  100 * residual_ss / total_ss if total_ss > 0 else 0,
        "n_obs":         len(rows),
        "n_conditions":  len(unique_conds),
        "n_hosts":       len(unique_hosts),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Calibration benchmark.csv (Stage 5)")
    p.add_argument("--validation-csv", default=None, help="Held-out benchmark.csv (Stage 6)")
    p.add_argument("--manifest", default=None,
                   help="Optional manifest.tsv with primary_records column to merge")
    p.add_argument("--output", default="model.yaml")
    p.add_argument("--rss-cap", type=float, default=None,
                   help="Optional RSS saturation cap in GB")
    p.add_argument("--variance-partition", action="store_true")
    p.add_argument("--threads-calibrated", type=int, default=32)
    args = p.parse_args()

    rows = read_csv_dict(args.csv)
    if args.manifest:
        # Merge primary_records from manifest into rows by run_id
        man = {r["run_id"]: r for r in read_csv_dict(args.manifest)}
        for r in rows:
            if r["run_id"] in man and "primary_records" not in r:
                r["primary_records"] = man[r["run_id"]].get("primary_records", "0")

    # Filter to rows with valid wall_s and primary_records
    valid = []
    for r in rows:
        try:
            r["wall_s_f"] = float(r["wall_s"])
            r["primary_records_f"] = float(r.get("primary_records", r.get("n_records", 0)))
            r["file_size_bytes_f"] = float(r.get("file_size_bytes", r.get("output_bytes", 0)))
            r["peak_rss_kb_f"] = float(r["peak_rss_kb"])
            valid.append(r)
        except (KeyError, ValueError):
            continue
    if not valid:
        print("ERROR: no valid rows with wall_s + primary_records", file=sys.stderr)
        sys.exit(1)

    N = np.array([r["primary_records_f"] for r in valid])
    F = np.array([r["file_size_bytes_f"] for r in valid])
    T = np.array([r["wall_s_f"] for r in valid])
    R = np.array([r["peak_rss_kb_f"] for r in valid]) / (1024 ** 2)   # GB

    # 1-term: wall = a + b*N
    A1 = np.vstack([np.ones_like(N), N]).T
    c1, _, r2_1 = fit_linear(A1, T)
    # 2-term: wall = a + b*N + c*F
    if F.sum() > 0:
        A2 = np.vstack([np.ones_like(N), N, F]).T
        c2, _, r2_2 = fit_linear(A2, T)
    else:
        c2, r2_2 = (None, None)
    # RSS = a + b*N
    cR, _, r2_R = fit_linear(A1, R)

    print(f"1-term wall: a={c1[0]:.3f}, b={c1[1]*1e6:.3f} us/record, R^2={r2_1:.4f}")
    if c2 is not None:
        print(f"2-term wall: a={c2[0]:.3f}, b={c2[1]*1e6:.3f} us/record, c={c2[2]*1e9:.3f} ns/byte, R^2={r2_2:.4f}")
    print(f"RSS:         a={cR[0]:.3f} GB, b/record={cR[1]*1024**3:.0f} bytes, R^2={r2_R:.4f}")

    # Out-of-sample validation
    val_residuals = None
    chosen_model = "wall_model_v1"
    if args.validation_csv:
        val_rows = read_csv_dict(args.validation_csv)
        val_residuals = []
        for r in val_rows:
            try:
                Tv = float(r["wall_s"])
                Nv = float(r.get("primary_records", 0))
                Fv = float(r.get("file_size_bytes", r.get("output_bytes", 0)))
            except (KeyError, ValueError):
                continue
            pred1 = c1[0] + c1[1] * Nv
            pred2 = c2[0] + c2[1] * Nv + c2[2] * Fv if c2 is not None else None
            err1 = 100 * (Tv - pred1) / pred1 if pred1 else float("nan")
            err2 = 100 * (Tv - pred2) / pred2 if pred2 else float("nan")
            val_residuals.append({
                "run_id": r["run_id"],
                "n_primary": Nv, "file_size_bytes": Fv, "obs": Tv,
                "pred_1term": pred1, "err_1term_pct": err1,
                "pred_2term": pred2, "err_2term_pct": err2,
            })
        if val_residuals:
            max_err1 = max(abs(v["err_1term_pct"]) for v in val_residuals)
            max_err2 = max(abs(v["err_2term_pct"]) for v in val_residuals if v["err_2term_pct"] is not None) if c2 is not None else float("inf")
            print(f"\nValidation max abs error: 1-term={max_err1:.1f}%, 2-term={max_err2:.1f}%")
            if max_err1 > 20 and (c2 is not None) and max_err2 < max_err1:
                chosen_model = "wall_model_v2"
                print(f"-> Recommending 2-term model (1-term error > 20%)")

    var_part = variance_partition(valid) if args.variance_partition else None

    # ============================================================
    # Write model.yaml
    # ============================================================
    out_yaml = []
    out_yaml.append(f"# Predictive model")
    out_yaml.append(f"# Calibration: {args.csv}")
    out_yaml.append(f"# Threads:     {args.threads_calibrated}")
    out_yaml.append(f"# n_observations: {len(valid)}")
    out_yaml.append("")
    out_yaml.append("wall_model_v1:")
    out_yaml.append(f'  formula:        "wall_s = a + b * N_primary_records"')
    out_yaml.append(f"  a_seconds:      {c1[0]:.4f}")
    out_yaml.append(f"  b_us_per_record: {c1[1]*1e6:.4f}")
    out_yaml.append(f"  r_squared:      {r2_1:.5f}")
    if c2 is not None:
        out_yaml.append("")
        out_yaml.append("wall_model_v2:")
        out_yaml.append(f'  formula: |')
        out_yaml.append(f"    wall_s = a + b * N_primary_records + c * file_size_bytes")
        out_yaml.append(f"  a_seconds:      {c2[0]:.4f}")
        out_yaml.append(f"  b_us_per_record:  {c2[1]*1e6:.4f}")
        out_yaml.append(f"  c_seconds_per_GB:  {c2[2]*1024**3:.4f}")
        out_yaml.append(f"  r_squared:      {r2_2:.5f}")
    out_yaml.append("")
    out_yaml.append("rss_model:")
    out_yaml.append(f'  formula:        "rss_GB = a + b * N_primary_records"')
    out_yaml.append(f"  a_GB:           {cR[0]:.4f}")
    out_yaml.append(f"  b_bytes_per_record: {cR[1]*1024**3:.0f}")
    out_yaml.append(f"  r_squared:      {r2_R:.5f}")
    if args.rss_cap:
        out_yaml.append(f"  saturation_cap_GB: {args.rss_cap}")
    out_yaml.append("")
    out_yaml.append(f"recommended_model: {chosen_model}")
    if val_residuals:
        out_yaml.append("")
        out_yaml.append("validation:")
        out_yaml.append(f"  source_csv: \"{args.validation_csv}\"")
        out_yaml.append("  observations:")
        for v in val_residuals:
            out_yaml.append(f"    - run_id: \"{v['run_id']}\"")
            out_yaml.append(f"      n_primary: {v['n_primary']}")
            out_yaml.append(f"      file_size_bytes: {v['file_size_bytes']}")
            out_yaml.append(f"      observed_wall_s: {v['obs']:.3f}")
            out_yaml.append(f"      pred_1term_s: {v['pred_1term']:.3f}")
            out_yaml.append(f"      err_1term_pct: {v['err_1term_pct']:.2f}")
            if v['pred_2term'] is not None:
                out_yaml.append(f"      pred_2term_s: {v['pred_2term']:.3f}")
                out_yaml.append(f"      err_2term_pct: {v['err_2term_pct']:.2f}")
    if var_part:
        out_yaml.append("")
        out_yaml.append("variance_partition:")
        for k, v in var_part.items():
            out_yaml.append(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
        if var_part["host_pct"] > 25:
            out_yaml.append("  warning: \"Host effect > 25% — partition is heterogeneous; identify outlier nodes via R: residuals(lmer(...)) and exclude.\"")

    out_yaml.append("")
    out_yaml.append("caveats:")
    out_yaml.append("  - \"Calibrated on Intel Xeon Gold 6348 (Ice Lake-SP) only\"")
    out_yaml.append("  - \"Valid only when -m * threads >= rss_GB prediction (in-memory regime)\"")
    out_yaml.append("  - \"For inputs ~30x beyond calibration range, validate before trusting\"")

    Path(args.output).write_text("\n".join(out_yaml) + "\n")
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
