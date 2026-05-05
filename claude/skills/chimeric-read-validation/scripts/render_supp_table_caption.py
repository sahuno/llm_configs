#!/usr/bin/env python3
"""render_supp_table_caption.py — manuscript-ready output.

Author: Samuel Ahuno
Purpose:
    Render a one-page Markdown summary of the validation table for
    inclusion in a manuscript Methods section, plus a
    supplementary-table caption. Reads the validation TSV produced by
    compute_validation_report.py and writes:

      <output>            — one-page Markdown summary (Methods + caption)
      <output>.summary.tsv  — per-rubric one-line numerical summary

    Driven by the rubric named in the input row's `rubric` column. If
    multiple rubrics appear in the same TSV, each gets its own section.
"""

from __future__ import annotations

import argparse
import csv
import logging
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Rubric thresholds are the source of truth — import them from the validation
# script rather than hard-coding so they can never drift out of sync.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compute_validation_report import RUBRICS  # noqa: E402

RUBRIC_LABELS = {
    "viral_integration": "viral integration",
    "gene_fusion": "gene fusion",
    "mobile_element": "mobile element insertion",
    "generic_sv": "generic SV",
}


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"render_supp_table_caption_{ts}.log"
    handlers = [logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return log_path


def load_validation_tsv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as fh:
        first = fh.readline()
        header = first.lstrip("#").rstrip("\n").split("\t")
        reader = csv.DictReader(fh, fieldnames=header, delimiter="\t")
        for r in reader:
            if not r.get("event_id"):
                continue
            rows.append(r)
    return rows


def median_str(values: list[float]) -> str:
    if not values:
        return "n/a"
    return f"{statistics.median(values):.0f}"


def render_section(rubric: str, rows: list[dict]) -> str:
    label = RUBRIC_LABELS.get(rubric, rubric)
    n = len(rows)
    counter = Counter(r["verdict"] for r in rows)
    n_pass = counter.get("pass", 0)
    n_review = counter.get("needs_review", 0)
    n_fail = counter.get("fail", 0)

    chim_counts = [int(r["n_chimeric_reads_tumor"]) for r in rows if r.get("n_chimeric_reads_tumor")]
    host_mapqs = [float(r["tumor_host_mapq_median"]) for r in rows if r.get("tumor_host_mapq_median")]
    target_mapqs = [
        float(r["tumor_target_mapq_median"])
        for r in rows
        if r.get("tumor_target_mapq_median") not in (None, "", "0", "0.0")
    ]
    fracs = [float(r["frac_chimeric_within_window_of_median"]) for r in rows if r.get("frac_chimeric_within_window_of_median")]
    win = rows[0].get("concordance_window_bp", "10") if rows else "10"

    # Pull rubric thresholds for the Methods description (the actual policy,
    # not what the data happened to satisfy).
    thresholds = RUBRICS.get(rubric, {})
    min_pass_reads = thresholds.get("min_chimeric_reads_pass", "n")
    min_concord = thresholds.get("min_concordance_frac", 0.7)

    md = []
    md.append(f"## {label.title()} validation ({n} call{'s' if n != 1 else ''})")
    md.append("")
    md.append(f"**Verdict summary:** {n_pass} pass, {n_review} needs_review, {n_fail} fail.")
    md.append("")
    md.append("**Methods paragraph (paste-ready):**")
    md.append("")
    md.append(
        f"> For each candidate {label}, we extracted chimeric reads from the "
        f"tumor BAM whose primary alignment lay within ±1 kb of the called "
        f"host breakpoint and whose SA tag contained the target contig. To "
        f"PASS, calls were required to have ≥ {min_pass_reads} chimeric "
        f"reads with ≥ {min_concord:.0%} of those reads agreeing on the "
        f"host breakpoint within ±{win} bp of the chimeric-read median "
        f"(or, equivalently, with the chimeric-read population sampling "
        f"both junctions of the event at a separation of ≈ SVLEN, detected "
        f"by a bimodality test on dominant soft-clip side). Per-call "
        f"read-name overlap with the matched-normal BAM was computed as a "
        f"contamination check. Verdicts (pass / needs_review / fail) were "
        f"assigned under the `{rubric}` rubric (see Supplementary Table)."
    )
    md.append("")
    md.append("**Cohort summary statistics:**")
    md.append("")
    md.append(f"- Tumor chimeric reads per call: median {median_str(chim_counts)}, "
              f"range {min(chim_counts) if chim_counts else 'n/a'}–{max(chim_counts) if chim_counts else 'n/a'}")
    md.append(f"- Host primary mapQ (median across calls): {median_str(host_mapqs)}")
    md.append(f"- Target supplementary mapQ (median across calls): {median_str(target_mapqs)}")
    md.append(f"- Fraction of chimeric reads within ±{win} bp of breakpoint median: "
              f"median {(statistics.median(fracs) if fracs else 0):.2f}")
    md.append("")

    md.append("**Supplementary Table caption:**")
    md.append("")
    md.append(
        f"> **Supplementary Table.** Read-level validation of {n} candidate "
        f"{label} call{'s' if n != 1 else ''}. For each call we report the "
        f"number of tumor-side chimeric reads, the median host primary mapQ, "
        f"the median target-contig supplementary mapQ, the chimeric-read "
        f"breakpoint median + median-absolute-deviation (MAD), the fraction "
        f"of chimeric reads within ±{win} bp of the breakpoint median, the "
        f"caller-vs-chimeric-median offset (bp), the bimodality split "
        f"distance (bp; non-empty when reads cluster at two host positions, "
        f"indicating both junctions are sampled), the host-flank "
        f"RepeatMasker overlap (bp / class), the per-call tumor-vs-normal "
        f"read-name overlap (contamination check), and the verdict under "
        f"the `{rubric}` rubric (pass / needs_review / fail). Verdict "
        f"reasons are tabulated for any call below pass."
    )
    md.append("")

    md.append("**Per-call verdicts:**")
    md.append("")
    md.append("| event_id | patient | host | n reads | mapQ host | mapQ target | bp median | MAD | frac in window | verdict |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        md.append(
            f"| {r['event_id']} | {r['patient']} | {r['host_chrom']}:{r['host_pos']} | "
            f"{r['n_chimeric_reads_tumor']} | {r.get('tumor_host_mapq_median','')} | "
            f"{r.get('tumor_target_mapq_median','')} | {r.get('chimeric_breakpoint_median','')} | "
            f"{r.get('chimeric_breakpoint_mad_bp','')} | "
            f"{r.get('frac_chimeric_within_window_of_median','')} | {r['verdict']} |"
        )
    md.append("")
    return "\n".join(md)


def write_summary_tsv(rows: list[dict], path: Path) -> None:
    by_rubric: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_rubric[r.get("rubric", "unspecified")].append(r)
    with path.open("w") as fh:
        fh.write("#rubric\tn_calls\tn_pass\tn_needs_review\tn_fail\tmedian_chimeric_reads\n")
        for rubric, rrows in by_rubric.items():
            counter = Counter(r["verdict"] for r in rrows)
            chim = [int(r["n_chimeric_reads_tumor"]) for r in rrows if r.get("n_chimeric_reads_tumor")]
            fh.write(
                f"{rubric}\t{len(rrows)}\t{counter.get('pass',0)}\t{counter.get('needs_review',0)}\t"
                f"{counter.get('fail',0)}\t{statistics.median(chim) if chim else ''}\n"
            )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--validation-tsv", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path, help="output Markdown file")
    p.add_argument("--log-dir", type=Path, default=None)
    args = p.parse_args()

    log_dir = args.log_dir or (args.output.parent / "logs")
    log_path = setup_logging(log_dir)
    log = logging.getLogger(__name__)
    t0 = time.time()
    log.info(f"=== render_supp_table_caption.py | log: {log_path} ===")

    rows = load_validation_tsv(args.validation_tsv)
    log.info(f"Loaded {len(rows)} rows from {args.validation_tsv}")
    if not rows:
        log.error("No rows in validation TSV — abort.")
        sys.exit(1)

    by_rubric: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_rubric[r.get("rubric", "unspecified")].append(r)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as fh:
        fh.write(f"# Validation report — generated {datetime.now().strftime('%Y-%m-%d')}\n\n")
        fh.write(f"Source: `{args.validation_tsv}`\n\n")
        for rubric, rrows in by_rubric.items():
            fh.write(render_section(rubric, rrows))
            fh.write("\n---\n\n")
    log.info(f"Wrote Markdown summary: {args.output}")

    summary_path = args.output.with_suffix(args.output.suffix + ".summary.tsv")
    write_summary_tsv(rows, summary_path)
    log.info(f"Wrote summary TSV: {summary_path}")

    log.info(f"Completed in {time.time() - t0:.1f} s")
    log.info(f"=== DONE: {Path(__file__).name} completed successfully ===")


if __name__ == "__main__":
    main()
