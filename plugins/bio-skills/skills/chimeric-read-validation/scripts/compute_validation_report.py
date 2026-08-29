#!/usr/bin/env python3
"""compute_validation_report.py — apply the verdict rubric.

Author: Samuel Ahuno
Purpose:
    Replace the manual "open IGV-reports HTML and look at it" step with
    a deterministic per-call validation report. Each candidate
    breakpoint gets one row of metrics + a verdict (pass / needs_review
    / fail) driven by an explicit rubric. The TSV is the candidate
    Supplementary Table.

    Inputs (all already on disk):
      - calls TSV (the samplesheet that drove `extract_chimeric_reads.py`)
      - <run>/per_integration/<event_id>.chimeric_reads.tumor.tsv
      - <run>/cohort_chimeric_read_summary.tsv (from the extract step)
      - optional: RepeatMasker BED (for host-flank repeat overlap)
      - optional: mosdepth summary (for target-contig coverage)

    Output:
      <run>/cohort_validation_report.tsv

    Verdict rubric (any FAIL trumps; otherwise NEEDS_REVIEW if any
    review-flag fires; otherwise PASS). The exact thresholds are
    rubric-dependent — viral_integration / gene_fusion / mobile_element
    / generic_sv. See references/rubrics.md.

    The bimodality test is the highest-leverage check. It splits chimeric
    reads by dominant soft-clip side and asks whether the two cluster
    medians are separated by ~SVLEN bp (i.e., the read population is
    sampling both junctions of the integration). When yes, a high
    overall stdev is real biology, not an inference artefact, and the
    call passes review.

    Generalized from the ATLL HTLV-1 reference impl (May 2026).
"""

from __future__ import annotations

import argparse
import csv
import logging
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Named rubrics — the reason the skill exists. See references/rubrics.md.
# ---------------------------------------------------------------------------
RUBRICS: dict[str, dict] = {
    "viral_integration": {
        "min_chimeric_reads_pass": 8,
        "min_chimeric_reads_fail": 5,
        "max_caller_vs_consensus_pass_bp": 50,
        "max_caller_vs_consensus_fail_bp": 1000,
        "min_concordance_frac": 0.7,
        "concordance_window_bp": 10,
        # Repeat-overlap is informational; only flag when paired with
        # poor host primary mapping. HTLV-1 / HBV / HHV preferentially
        # integrate into AT-rich/repeat-dense regions by biology.
        "review_repeat_pct_min": 85,
        "review_host_mapq_max": 30,
        # Defective-provirus aligned-length threshold relaxed for partial
        # / deleted proviruses (Matsuoka-style ATLL ~50% defective).
        "min_target_aligned_len_intact_bp": 500,
        "min_target_aligned_len_defective_bp": 100,
    },
    "gene_fusion": {
        "min_chimeric_reads_pass": 5,  # fusions often have fewer reads
        "min_chimeric_reads_fail": 3,
        "max_caller_vs_consensus_pass_bp": 50,
        "max_caller_vs_consensus_fail_bp": 500,  # exon boundaries are tight
        "min_concordance_frac": 0.8,  # fusions tighter than viral
        "concordance_window_bp": 10,
        "review_repeat_pct_min": 100,  # don't flag repeats — fusions in clean genes
        "review_host_mapq_max": 0,
        "min_target_aligned_len_intact_bp": 100,  # partner read can be short
        "min_target_aligned_len_defective_bp": 50,
    },
    "mobile_element": {
        "min_chimeric_reads_pass": 5,  # heterozygous insertions in normal samples
        "min_chimeric_reads_fail": 3,
        "max_caller_vs_consensus_pass_bp": 100,  # MEI breakpoints are noisier
        "max_caller_vs_consensus_fail_bp": 1000,
        "min_concordance_frac": 0.6,
        "concordance_window_bp": 20,
        # Mobile elements integrate via reverse transcriptase and have a
        # strong AT-rich preference — repeat-overlap is biology.
        "review_repeat_pct_min": 100,
        "review_host_mapq_max": 0,
        "min_target_aligned_len_intact_bp": 100,
        "min_target_aligned_len_defective_bp": 50,
    },
    "generic_sv": {
        "min_chimeric_reads_pass": 10,
        "min_chimeric_reads_fail": 5,
        "max_caller_vs_consensus_pass_bp": 30,
        "max_caller_vs_consensus_fail_bp": 500,
        "min_concordance_frac": 0.8,
        "concordance_window_bp": 10,
        # Generic SV: repeats DO matter — flag them directly.
        "review_repeat_pct_min": 50,
        "review_host_mapq_max": 40,
        "min_target_aligned_len_intact_bp": 500,
        "min_target_aligned_len_defective_bp": 200,
    },
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"compute_validation_report_{ts}.log"
    handlers = [logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return log_path


# ---------------------------------------------------------------------------
# Stat helpers
# ---------------------------------------------------------------------------
def median_or_none(xs):
    return statistics.median(xs) if xs else None


def mad(xs, med):
    return statistics.median(abs(x - med) for x in xs) if xs and med is not None else None


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def load_calls(calls_path: Path) -> list[dict]:
    rows: list[dict] = []
    with calls_path.open() as fh:
        first = fh.readline()
        header = first.lstrip("#").rstrip("\n").split("\t")
        reader = csv.DictReader(fh, fieldnames=header, delimiter="\t")
        for r in reader:
            if not r.get("event_id"):
                continue
            rows.append(r)
    return rows


def load_chimeric(per_call_path: Path) -> list[dict]:
    if not per_call_path.exists():
        return []
    text = per_call_path.read_text()
    if text.startswith("# no chimeric"):
        return []
    rows: list[dict] = []
    lines = text.splitlines()
    if not lines:
        return rows
    header = lines[0].lstrip("#").split("\t")
    for ln in lines[1:]:
        if not ln:
            continue
        rows.append(dict(zip(header, ln.split("\t"))))
    return rows


def load_summary(summary_tsv: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not summary_tsv.exists():
        return out
    with summary_tsv.open() as fh:
        header = fh.readline().lstrip("#").rstrip("\n").split("\t")
        for ln in fh:
            r = dict(zip(header, ln.rstrip("\n").split("\t")))
            out[r["event_id"]] = r
    return out


# ---------------------------------------------------------------------------
# Bimodality — the highest-leverage check
# ---------------------------------------------------------------------------
def bimodality(chimeric_rows: list[dict]) -> dict:
    """Split inferred breakpoints by dominant soft-clip side; return cluster
    medians and the distance between them. When the two cluster medians are
    separated by ~SVLEN bp, the chimeric-read population is sampling both
    junctions of the event — high overall breakpoint stdev is real biology
    and the call passes review even if the global concordance is poor."""
    bps_left: list[int] = []
    bps_right: list[int] = []
    for r in chimeric_rows:
        lc = int(r["host_left_clip_bp"])
        rc = int(r["host_right_clip_bp"])
        bp = int(r["host_inferred_breakpoint"])
        (bps_left if lc > rc else bps_right).append(bp)
    out = {
        "n_left": len(bps_left),
        "n_right": len(bps_right),
        "left_median": median_or_none(bps_left),
        "right_median": median_or_none(bps_right),
        "split_distance_bp": None,
    }
    if bps_left and bps_right:
        out["split_distance_bp"] = abs(out["right_median"] - out["left_median"])
    return out


# ---------------------------------------------------------------------------
# Repeat overlap (informational by default — biology, not artifact)
# ---------------------------------------------------------------------------
def host_flank_repeats(chrom: str, pos: int, rmsk_bed: Path | None, flank_bp: int = 300) -> tuple[int, str]:
    """bedtools intersect of <chrom> <pos-flank> <pos+flank> with RepeatMasker.
    Returns (overlap_bp, top_repeat_class). Returns (0, '') if rmsk_bed is None."""
    if rmsk_bed is None:
        return 0, ""
    region_bed = f"{chrom}\t{max(1, pos - flank_bp)}\t{pos + flank_bp}\n"
    proc = subprocess.run(
        ["bedtools", "intersect", "-a", "/dev/stdin", "-b", str(rmsk_bed), "-wa", "-wb"],
        input=region_bed,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        logging.warning(f"bedtools intersect failed for {chrom}:{pos}: {proc.stderr.strip()}")
        return 0, ""
    overlap_bp = 0
    classes: Counter = Counter()
    for line in proc.stdout.splitlines():
        cols = line.split("\t")
        if len(cols) < 7:
            continue
        a_start, a_end = int(cols[1]), int(cols[2])
        b_start, b_end = int(cols[4]), int(cols[5])
        b_name = cols[6]
        ov = max(0, min(a_end, b_end) - max(a_start, b_start))
        overlap_bp += ov
        cls = b_name.split("_")[0] or b_name
        classes[cls] += ov
    top_class = classes.most_common(1)[0][0] if classes else ""
    return overlap_bp, top_class


# ---------------------------------------------------------------------------
# Optional: target-contig coverage from mosdepth summary
# ---------------------------------------------------------------------------
def target_mean_coverage(mosdepth_summary: Path | None, target_contig: str) -> float | None:
    if mosdepth_summary is None or not mosdepth_summary.exists():
        return None
    for ln in mosdepth_summary.read_text().splitlines():
        toks = ln.split("\t")
        if toks and toks[0] == target_contig:
            try:
                return float(toks[3])
            except (IndexError, ValueError):
                return None
    return None


# ---------------------------------------------------------------------------
# Verdict assignment
# ---------------------------------------------------------------------------
def assess(m: dict, rubric: dict) -> tuple[str, str]:
    """Apply the rubric. Returns (verdict, '; '.join(reasons))."""
    n = m["n_chimeric_reads_tumor"]
    tn = m.get("tn_overlap_reads")
    sev_off = m["caller_vs_chimeric_median_bp"]

    # FAIL (any one trumps)
    if n < rubric["min_chimeric_reads_fail"]:
        return "fail", f"<{rubric['min_chimeric_reads_fail']} tumor chimeric reads ({n})"
    if isinstance(tn, int) and tn > 0:
        return "fail", f"T/N read-name overlap > 0 ({tn})"
    if isinstance(sev_off, (int, float)) and sev_off > rubric["max_caller_vs_consensus_fail_bp"]:
        return "fail", f"caller call {sev_off:.0f} bp from chimeric median"

    reasons: list[str] = []
    if n < rubric["min_chimeric_reads_pass"]:
        reasons.append(f"low tumor chimeric reads ({n})")
    if isinstance(sev_off, (int, float)) and sev_off > rubric["max_caller_vs_consensus_pass_bp"]:
        reasons.append(f"caller call {sev_off:.0f} bp from chimeric median")
    frac = m["frac_chimeric_within_window_of_median"]
    if frac < rubric["min_concordance_frac"] and m["bim_match_to_svlen"] != "yes":
        reasons.append(
            f"breakpoint concordance {frac:.2f} < {rubric['min_concordance_frac']:.1f} "
            f"and not bimodal-matching-SVLEN"
        )
    # Repeat-overlap: only fires as a flag when paired with low host mapQ.
    # For viral_integration / gene_fusion / mobile_element rubrics the
    # thresholds are tuned to never fire on biology — see references/rubrics.md.
    if (
        m["host_flank_repeat_pct"] >= rubric["review_repeat_pct_min"]
        and m["tumor_host_mapq_median"] < rubric["review_host_mapq_max"]
    ):
        reasons.append(
            f"host flank {m['host_flank_repeat_pct']:.0f}% repeat-overlapping "
            f"({m['host_flank_repeat_top_class']}) AND host mapq {m['tumor_host_mapq_median']:.0f} "
            f"< {rubric['review_host_mapq_max']}"
        )
    # Aligned-length threshold (defective-aware).
    pclass = (m.get("provirus_class") or "").lower()
    aligned_len = m.get("tumor_target_aligned_len_median_bp", "")
    if isinstance(aligned_len, (int, float)) and aligned_len:
        if pclass == "defective":
            min_len = rubric["min_target_aligned_len_defective_bp"]
        else:
            min_len = rubric["min_target_aligned_len_intact_bp"]
        if aligned_len < min_len:
            reasons.append(
                f"target supplementary aligned length {aligned_len:.0f} bp < "
                f"{min_len} bp ({pclass or 'intact'} threshold)"
            )

    return ("needs_review", "; ".join(reasons)) if reasons else ("pass", "")


# ---------------------------------------------------------------------------
# Per-patient VAF concordance — gotcha #3 in DESIGN.md
# ---------------------------------------------------------------------------
def vaf_concordance_per_patient(out_rows: list[dict]) -> dict[str, float]:
    """For each patient, compute max(VAF) − min(VAF) across all calls.
    Truncal events have similar VAFs across the patient's calls; subclonal
    events have differing VAFs. Informational metric for downstream
    interpretation (manuscript / clonality discussion)."""
    by_patient: dict[str, list[float]] = defaultdict(list)
    for r in out_rows:
        v = r.get("caller_vaf")
        if v == "" or v is None:
            continue
        try:
            by_patient[r["patient"]].append(float(v))
        except ValueError:
            continue
    return {p: (max(vs) - min(vs)) for p, vs in by_patient.items() if len(vs) >= 2}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--calls", required=True, type=Path, help="calls TSV (the same one used by extract)")
    p.add_argument(
        "--per-int-dir",
        required=True,
        type=Path,
        help="<run>/per_integration directory (output of extract step)",
    )
    p.add_argument(
        "--summary-tsv",
        type=Path,
        default=None,
        help="<run>/cohort_chimeric_read_summary.tsv (defaults to sibling of --per-int-dir)",
    )
    p.add_argument(
        "--rubric",
        choices=list(RUBRICS.keys()),
        default="viral_integration",
        help="named rubric — see references/rubrics.md",
    )
    p.add_argument("--target-contig", required=True, type=str, help="target contig name (for coverage lookup)")
    p.add_argument("--output", required=True, type=Path, help="output validation TSV")
    p.add_argument("--rmsk-bed", type=Path, default=None, help="RepeatMasker BED for host-flank repeat overlap")
    p.add_argument(
        "--mosdepth-summary-pattern",
        type=str,
        default=None,
        help="path pattern for mosdepth summary, with {patient} substitution. "
        "e.g. results/.../mosdepth/{patient}_tumor.mosdepth.summary.txt",
    )
    p.add_argument("--flank-bp", type=int, default=300, help="host-flank window for repeat overlap (bp)")
    p.add_argument("--log-dir", type=Path, default=None)
    args = p.parse_args()

    rubric = RUBRICS[args.rubric]
    log_dir = args.log_dir or (args.output.parent / "logs")
    log_path = setup_logging(log_dir)
    log = logging.getLogger(__name__)
    t0 = time.time()
    log.info(f"=== compute_validation_report.py | log: {log_path} ===")
    log.info(f"rubric={args.rubric} target_contig={args.target_contig}")
    log.info(f"thresholds: {rubric}")

    summary_tsv = args.summary_tsv or (args.per_int_dir.parent / "cohort_chimeric_read_summary.tsv")
    summary_by_event = load_summary(summary_tsv)
    log.info(f"Loaded {len(summary_by_event)} rows from summary {summary_tsv}")
    if not summary_by_event:
        log.warning(
            "Summary TSV missing or empty — T/N overlap and target mapQ medians "
            "will be blank. Make sure the extract step ran first."
        )

    calls = load_calls(args.calls)
    log.info(f"Loaded {len(calls)} calls from {args.calls}")
    if not calls:
        log.error("No calls parsed — abort.")
        sys.exit(1)

    out_rows: list[dict] = []
    for ig in calls:
        eid = ig["event_id"]
        chrom = ig["host_chrom"]
        try:
            pos = int(ig["host_pos"])
        except ValueError:
            log.error(f"  bad host_pos for {eid}: {ig['host_pos']}")
            continue
        try:
            svlen = int(ig.get("svlen_bp", 0) or 0)
        except ValueError:
            svlen = 0
        log.info(f"=== {eid} {chrom}:{pos} (SVLEN={svlen}) ===")

        per_int = args.per_int_dir / f"{eid}.chimeric_reads.tumor.tsv"
        chimeric = load_chimeric(per_int)
        bps = [int(r["host_inferred_breakpoint"]) for r in chimeric]
        host_mapqs = [int(r["host_mapq"]) for r in chimeric]
        med = median_or_none(bps)
        host_mapq_med = median_or_none(host_mapqs) or 0
        bp_mad = mad(bps, med)
        win = rubric["concordance_window_bp"]
        frac_in_win = (sum(1 for b in bps if abs(b - med) <= win) / len(bps)) if bps else 0.0
        sev_off = abs(pos - med) if med is not None else None

        bim = bimodality(chimeric)
        # Bimodality match: when the two clusters are separated by ~SVLEN,
        # the chimeric-read population is sampling both junctions and the
        # high overall breakpoint stdev is real biology.
        bim_match = (
            bim["split_distance_bp"] is not None
            and svlen > 100
            and abs(bim["split_distance_bp"] - svlen) <= max(50, 0.10 * svlen)
        )

        rep_bp, rep_class = host_flank_repeats(chrom, pos, args.rmsk_bed, flank_bp=args.flank_bp)
        rep_pct = 100.0 * rep_bp / (2 * args.flank_bp) if args.flank_bp else 0.0

        cov = None
        if args.mosdepth_summary_pattern:
            mp = Path(args.mosdepth_summary_pattern.format(patient=ig["patient"]))
            cov = target_mean_coverage(mp, args.target_contig)

        sum_row = summary_by_event.get(eid, {})
        try:
            tn_overlap = int(sum_row.get("tn_overlap_reads", 0) or 0)
        except ValueError:
            tn_overlap = 0
        try:
            target_mapq_med = float(sum_row.get("tumor_target_mapq_median", 0) or 0)
        except ValueError:
            target_mapq_med = 0.0
        try:
            target_aligned_len_med = (
                float(sum_row["tumor_target_aligned_len_median_bp"])
                if sum_row.get("tumor_target_aligned_len_median_bp")
                else ""
            )
        except ValueError:
            target_aligned_len_med = ""

        m = {
            "event_id": eid,
            "patient": ig["patient"],
            "host_chrom": chrom,
            "host_pos": pos,
            "svlen_bp": svlen,
            "provirus_class": ig.get("provirus_class", ""),
            "strict_somatic": ig.get("strict_somatic", ""),
            "caller_vaf": ig.get("caller_vaf", ""),
            "rubric": args.rubric,
            "n_chimeric_reads_tumor": len(chimeric),
            "tumor_host_mapq_median": host_mapq_med,
            "tumor_target_mapq_median": target_mapq_med,
            "tumor_target_aligned_len_median_bp": target_aligned_len_med,
            "chimeric_breakpoint_median": med if med is not None else "",
            "chimeric_breakpoint_mad_bp": int(bp_mad) if bp_mad is not None else "",
            "concordance_window_bp": win,
            "frac_chimeric_within_window_of_median": round(frac_in_win, 3),
            "caller_vs_chimeric_median_bp": sev_off if sev_off is not None else "",
            "bim_n_left_clip_dominant": bim["n_left"],
            "bim_n_right_clip_dominant": bim["n_right"],
            "bim_left_cluster_median": bim["left_median"] if bim["left_median"] is not None else "",
            "bim_right_cluster_median": bim["right_median"] if bim["right_median"] is not None else "",
            "bim_split_distance_bp": (
                int(bim["split_distance_bp"]) if bim["split_distance_bp"] is not None else ""
            ),
            "bim_match_to_svlen": "yes" if bim_match else "no",
            "host_flank_repeat_overlap_bp": rep_bp,
            "host_flank_repeat_pct": round(rep_pct, 1),
            "host_flank_repeat_top_class": rep_class,
            "tumor_target_mean_coverage_x": cov if cov is not None else "",
            "tn_overlap_reads": tn_overlap,
        }
        verdict, reasons = assess(m, rubric)
        m["verdict"] = verdict
        m["verdict_reasons"] = reasons
        log.info(f"  verdict: {verdict}{' — ' + reasons if reasons else ''}")
        out_rows.append(m)

    # Per-patient VAF concordance is informational, written to a sibling TSV
    # so the main validation table stays one-row-per-event.
    vaf_conc = vaf_concordance_per_patient(out_rows)
    if vaf_conc:
        vaf_path = args.output.with_name(args.output.stem + "_vaf_concordance.tsv")
        with vaf_path.open("w") as fh:
            fh.write("#patient\tn_calls\tvaf_max_minus_min\n")
            counts: dict[str, int] = defaultdict(int)
            for r in out_rows:
                counts[r["patient"]] += 1
            for patient, delta in sorted(vaf_conc.items()):
                fh.write(f"{patient}\t{counts[patient]}\t{delta:.3f}\n")
        log.info(f"Wrote per-patient VAF concordance: {vaf_path}")

    cols = list(out_rows[0].keys())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as fh:
        fh.write("#" + "\t".join(cols) + "\n")
        for r in out_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
    log.info(f"Wrote {args.output}")

    n_pass = sum(1 for r in out_rows if r["verdict"] == "pass")
    n_review = sum(1 for r in out_rows if r["verdict"] == "needs_review")
    n_fail = sum(1 for r in out_rows if r["verdict"] == "fail")
    log.info(f"Verdict summary: pass={n_pass}  needs_review={n_review}  fail={n_fail}  (total={len(out_rows)})")
    log.info(f"Completed in {time.time() - t0:.1f} s")
    log.info(f"=== DONE: {Path(__file__).name} completed successfully ===")


if __name__ == "__main__":
    main()
