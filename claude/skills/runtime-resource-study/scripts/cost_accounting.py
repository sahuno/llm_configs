#!/usr/bin/env python3
# Author: claude (skill bundled)
# Date: 2026-04-29
# Purpose: Convert wall_s × threads × $/core-hour into per-condition CPU-hours and
# dollar cost. Identify the cost-Pareto frontier (configs that aren't dominated by
# any cheaper-AND-faster alternative). Default rate: $0.05/core-hour.
#
# Usage:
#   python cost_accounting.py --csv <benchmark.csv> [--rate 0.05] --output cost_pareto.csv

import argparse
import csv
from pathlib import Path
from statistics import median


def read_csv_dict(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def aggregate_by_condition(rows, factor_keys):
    """Group rows by (factor_keys) tuple; aggregate to median wall, min/max, threads."""
    groups = {}
    for r in rows:
        try:
            wall = float(r["wall_s"])
            threads = int(r["threads"])
        except (KeyError, ValueError):
            continue
        key = tuple(r.get(k, "") for k in factor_keys)
        groups.setdefault(key, []).append((wall, threads))
    out = []
    for key, vals in groups.items():
        walls = [w for w, _ in vals]
        threads = vals[0][1]    # threads is part of the key; same for the group
        out.append({
            **dict(zip(factor_keys, key)),
            "n": len(vals),
            "wall_med": median(walls),
            "wall_min": min(walls),
            "wall_max": max(walls),
            "threads": threads,
        })
    return out


def add_cost(conditions, rate_per_core_hour):
    for c in conditions:
        cpu_hours = c["wall_med"] / 3600 * c["threads"]
        c["cpu_hours_med"] = cpu_hours
        c["cost_med_usd"] = cpu_hours * rate_per_core_hour
        # Range from min/max wall
        c["cost_lo_usd"] = c["wall_min"] / 3600 * c["threads"] * rate_per_core_hour
        c["cost_hi_usd"] = c["wall_max"] / 3600 * c["threads"] * rate_per_core_hour
    return conditions


def pareto_frontier(conditions):
    """A condition is on the cost-Pareto frontier if no other is both cheaper and faster.
    Returns the subset on the frontier, in order of increasing wall."""
    sorted_c = sorted(conditions, key=lambda c: c["wall_med"])
    frontier = []
    min_cost = float("inf")
    # Walk slowest-first; keep points where cost is strictly less than the running min
    for c in sorted_c[::-1]:
        if c["cost_med_usd"] < min_cost:
            frontier.append(c)
            min_cost = c["cost_med_usd"]
    return frontier[::-1]   # back to fastest-first


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--rate", type=float, default=0.05,
                   help="Cost per core-hour in USD (default: 0.05)")
    p.add_argument("--factor-keys", default="threads,mem_per_thread,compression_level",
                   help="Comma-separated columns that define a 'condition' (default: threads,mem_per_thread,compression_level)")
    p.add_argument("--output", default="cost_pareto.csv")
    args = p.parse_args()

    rows = read_csv_dict(args.csv)
    factor_keys = args.factor_keys.split(",")
    print(f"Loaded {len(rows)} rows from {args.csv}")
    print(f"Cost rate: ${args.rate}/core-hour")
    print(f"Grouping by: {factor_keys}\n")

    conditions = aggregate_by_condition(rows, factor_keys)
    conditions = add_cost(conditions, args.rate)

    # Print sorted by cost
    conditions.sort(key=lambda c: c["cost_med_usd"])
    print(f"=== {len(conditions)} unique conditions (sorted by cost) ===")
    print(f"{'#':>3}  " + "  ".join(f"{k:>14}" for k in factor_keys) +
          f"  {'wall_s':>8}  {'cpu-hr':>8}  {'$/sample':>9}  {'on_pareto':>10}")
    pareto = set(id(c) for c in pareto_frontier(conditions))
    for i, c in enumerate(conditions, 1):
        is_pareto = "*" if id(c) in pareto else ""
        line = f"{i:>3}  " + "  ".join(f"{c[k]:>14}" for k in factor_keys)
        line += f"  {c['wall_med']:>8.2f}  {c['cpu_hours_med']:>8.4f}  ${c['cost_med_usd']:>8.4f}  {is_pareto:>10}"
        print(line)

    print(f"\nCost-Pareto frontier ({sum(1 for _ in pareto_frontier(conditions))} configs):")
    for c in pareto_frontier(conditions):
        msg = ", ".join(f"{k}={c[k]}" for k in factor_keys)
        print(f"  {msg}  ->  {c['wall_med']:.2f}s  ${c['cost_med_usd']:.4f}")

    # Write CSV
    out_keys = factor_keys + ["n", "wall_med", "wall_min", "wall_max",
                              "threads", "cpu_hours_med", "cost_med_usd",
                              "cost_lo_usd", "cost_hi_usd", "on_pareto"]
    pareto_ids = pareto
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_keys)
        w.writeheader()
        for c in conditions:
            row = {k: c.get(k, "") for k in out_keys}
            row["on_pareto"] = "yes" if id(c) in pareto_ids else "no"
            w.writerow(row)
    print(f"\nSaved: {args.output}")
    print(f"\nUSAGE NOTE: a config on the Pareto frontier is the optimum for *some* user.")
    print("If $/sample matters, pick a frontier point with low cost and acceptable wall.")
    print("If wall matters, pick the fastest frontier point regardless of cost.")


if __name__ == "__main__":
    main()
