#!/usr/bin/env python3
"""extract_chimeric_reads.py — generalized chimeric-read extraction.

Author: Samuel Ahuno
Purpose:
    Per-call extraction of chimeric reads supporting each candidate
    breakpoint. A "chimeric read" here is a read whose primary alignment
    lies near host_chrom:host_pos +/- WINDOW_BP and whose SA
    (supplementary-alignment) tag contains the user-specified target
    contig (viral, fusion partner, mobile element, etc.).

    For each call, this script extracts chimeric reads from the tumor
    BAM (and optionally a matched-normal BAM), parses the host primary
    alignment + target-contig supplementary alignment, computes the
    inferred host breakpoint per read, and emits:

      - <output_dir>/per_integration/<event_id>.chimeric_reads.tumor.tsv
      - <output_dir>/per_integration/<event_id>.chimeric_reads.normal.tsv  (if normal BAM provided)
      - <output_dir>/cohort_chimeric_read_summary.tsv

    Outputs answer:
      1. How many tumor-side chimeric reads support each call?
      2. Do they agree on the host breakpoint within +/- X bp?
      3. What fraction (by read name) also appear in the matched normal?
         (per-call contamination check)
      4. Are target-contig supplementary mapQ values acceptable?

    Generalized from the ATLL HTLV-1 reference impl (May 2026) at
    /data1/greenbab/projects/ont/Project_17424/results/20260503_hg38plusHTLV1EBV_cohort_chimeric_read_evidence/
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")
SAMTOOLS = "samtools"

# Required + optional columns in the calls TSV.
REQUIRED_CALL_COLS = ("event_id", "patient", "host_chrom", "host_pos", "tumor_bam")
OPTIONAL_CALL_COLS = ("normal_bam", "svlen_bp", "provirus_class", "strict_somatic", "caller_vaf", "severus_id")


# ---------------------------------------------------------------------------
# Logging setup (CLAUDE.md §Logging requirements: timestamped log + tee to stdout)
# ---------------------------------------------------------------------------
def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"extract_chimeric_reads_{ts}.log"
    handlers = [logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return log_path


# ---------------------------------------------------------------------------
# CIGAR / SA tag parsing helpers
# ---------------------------------------------------------------------------
def consume_ref(cigar: str) -> int:
    n = 0
    for length, op in CIGAR_RE.findall(cigar):
        if op in ("M", "D", "N", "=", "X"):
            n += int(length)
    return n


def soft_clip_lengths(cigar: str) -> tuple[int, int]:
    """Return (left_clip, right_clip) soft-clip lengths in bases."""
    ops = CIGAR_RE.findall(cigar)
    left = int(ops[0][0]) if ops and ops[0][1] == "S" else 0
    right = int(ops[-1][0]) if ops and ops[-1][1] == "S" else 0
    return left, right


def parse_sa_tag(sa_value: str) -> list[dict]:
    """Parse SA:Z:<rname,pos,strand,CIGAR,mapQ,NM>;... into a list."""
    out: list[dict] = []
    for entry in sa_value.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(",")
        if len(parts) < 6:
            continue
        rname, pos, strand, cigar, mapq, nm = parts[:6]
        try:
            out.append(
                {
                    "rname": rname,
                    "pos": int(pos),
                    "strand": strand,
                    "cigar": cigar,
                    "mapq": int(mapq),
                    "nm": int(nm),
                    "ref_consumed": consume_ref(cigar),
                }
            )
        except ValueError:
            continue
    return out


def infer_host_breakpoint(host_pos: int, host_cigar: str, left_clip: int, right_clip: int) -> int:
    """Infer host-side breakpoint from the primary alignment.

    The breakpoint sits at the soft-clip boundary; pick whichever clip is
    larger. Note: this can disagree with the truth when both clips are
    near-equal, which is why the validation step also runs a bimodality
    check to detect the two-junction case (e.g., LTR-host on both sides
    of an integration).
    """
    if right_clip >= left_clip:
        return host_pos + consume_ref(host_cigar) - 1
    return host_pos


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
def preflight_bam(bam: Path, target_contig: str, log: logging.Logger, strict: bool = False) -> None:
    """Check that the BAM is indexed (and the index is fresher than the BAM),
    that the target contig exists in the @SQ headers, and that the @PG line
    suggests minimap2 was run with -Y so that SA tags carry soft-clipped
    sequence.

    `strict=True` raises on any failure; otherwise warns. The default is
    permissive because some BAMs may be aligned with non-minimap2 tools whose
    @PG lines look different.
    """
    if not bam.exists():
        raise FileNotFoundError(f"BAM not found: {bam}")
    bai = bam.with_suffix(bam.suffix + ".bai")
    if not bai.exists():
        bai = bam.with_suffix(".bai")
    if not bai.exists():
        msg = f"No .bai index for {bam}"
        (log.error if strict else log.warning)(msg)
        if strict:
            raise FileNotFoundError(msg)
    elif bai.stat().st_mtime < bam.stat().st_mtime:
        log.warning(
            "BAI mtime is older than BAM mtime — `samtools view region` may return wrong reads. "
            f"Re-index: samtools index {bam}"
        )

    # Header check.
    proc = subprocess.run([SAMTOOLS, "view", "-H", str(bam)], capture_output=True, text=True, check=True)
    sq_contigs = []
    pg_lines = []
    for line in proc.stdout.splitlines():
        if line.startswith("@SQ"):
            for tok in line.split("\t"):
                if tok.startswith("SN:"):
                    sq_contigs.append(tok[3:])
        elif line.startswith("@PG"):
            pg_lines.append(line)
    if target_contig not in sq_contigs:
        log.error(
            f"target contig '{target_contig}' not found in {bam} @SQ headers. "
            f"Available contigs (first 10): {sq_contigs[:10]}..."
        )
        raise SystemExit(2)

    # @PG -Y check (advisory — minimap2 emits soft-clipped supplementary
    # sequence with -Y; without it, SA tag parsing may break).
    minimap_pg = [pg for pg in pg_lines if "minimap2" in pg or "mm2" in pg.lower()]
    if minimap_pg:
        if not any(" -Y" in pg or "\t-Y" in pg or "-Y\t" in pg for pg in minimap_pg):
            log.warning(
                "minimap2 @PG line found but no '-Y' flag detected — supplementary "
                "alignments may not carry the soft-clipped sequence, and SA-tag "
                f"parsing may produce truncated CIGARs. BAM: {bam}"
            )


def parse_calls_tsv(calls_path: Path) -> list[dict]:
    """Parse the calls samplesheet. Tab-separated, '#'-prefixed header line
    optional. Returns one dict per row with all original columns preserved."""
    rows: list[dict] = []
    with calls_path.open() as fh:
        first = fh.readline()
        header_line = first.lstrip("#").rstrip("\n")
        header = header_line.split("\t")
        missing = [c for c in REQUIRED_CALL_COLS if c not in header]
        if missing:
            raise SystemExit(
                f"calls TSV missing required columns: {missing}\n"
                f"required: {REQUIRED_CALL_COLS}\n"
                f"optional: {OPTIONAL_CALL_COLS}\n"
                f"got header: {header}"
            )
        reader = csv.DictReader(fh, fieldnames=header, delimiter="\t")
        for r in reader:
            if not r.get("event_id"):
                continue
            r["host_pos"] = int(r["host_pos"])
            for col in ("svlen_bp",):
                if col in r and r[col]:
                    try:
                        r[col] = int(r[col])
                    except ValueError:
                        pass
            for col in ("caller_vaf",):
                if col in r and r[col]:
                    try:
                        r[col] = float(r[col])
                    except ValueError:
                        pass
            rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------
def extract_for_bam(
    bam: Path,
    host_chrom: str,
    host_pos: int,
    target_contig: str,
    label: str,
    flanking_bp: int,
) -> tuple[list[dict], dict]:
    """Run `samtools view <bam> chrom:pos-W-pos+W` and parse chimeric reads
    whose SA tag contains the target contig. Returns (per-read rows, summary).
    """
    region = f"{host_chrom}:{max(1, host_pos - flanking_bp)}-{host_pos + flanking_bp}"
    proc = subprocess.run(
        [SAMTOOLS, "view", str(bam), region],
        capture_output=True,
        text=True,
        check=True,
    )
    rows: list[dict] = []
    breakpoints: list[int] = []
    target_mapq: list[int] = []
    target_aligned_len: list[int] = []
    seen_names: set[str] = set()
    for line in proc.stdout.splitlines():
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 11:
            continue
        qname, flag, rname, pos, mapq, cigar = (
            cols[0], int(cols[1]), cols[2], int(cols[3]), int(cols[4]), cols[5],
        )
        # Primary alignments only — secondary/supplementary are the partner
        # ends of the same chimera and would double-count.
        if flag & 0x100 or flag & 0x800:
            continue
        sa_value = ""
        for tag in cols[11:]:
            if tag.startswith("SA:Z:"):
                sa_value = tag[5:]
                break
        if not sa_value:
            continue
        sa_records = parse_sa_tag(sa_value)
        sa_target = [s for s in sa_records if s["rname"] == target_contig]
        if not sa_target:
            continue
        seen_names.add(qname)
        left_clip, right_clip = soft_clip_lengths(cigar)
        bp = infer_host_breakpoint(pos, cigar, left_clip, right_clip)
        breakpoints.append(bp)
        # Largest target-contig SA hit (by aligned length) is most informative.
        sa_top = max(sa_target, key=lambda s: s["ref_consumed"])
        target_mapq.append(sa_top["mapq"])
        target_aligned_len.append(sa_top["ref_consumed"])
        rows.append(
            {
                "read_name": qname,
                "bam_label": label,
                "host_chrom": rname,
                "host_primary_pos": pos,
                "host_strand": "-" if flag & 0x10 else "+",
                "host_mapq": mapq,
                "host_cigar": cigar,
                "host_left_clip_bp": left_clip,
                "host_right_clip_bp": right_clip,
                "host_inferred_breakpoint": bp,
                "target_pos": sa_top["pos"],
                "target_strand": sa_top["strand"],
                "target_cigar": sa_top["cigar"],
                "target_mapq": sa_top["mapq"],
                "target_aligned_len_bp": sa_top["ref_consumed"],
                "n_total_sa_records": len(sa_records),
                "n_sa_records_to_target": len(sa_target),
            }
        )
    summary = {
        "n_chimeric_reads": len(rows),
        "n_unique_read_names": len(seen_names),
        "breakpoint_median": statistics.median(breakpoints) if breakpoints else "",
        "breakpoint_mad_bp": (
            int(statistics.median(abs(b - statistics.median(breakpoints)) for b in breakpoints))
            if breakpoints else ""
        ),
        "target_mapq_median": statistics.median(target_mapq) if target_mapq else "",
        "target_aligned_len_median_bp": (
            statistics.median(target_aligned_len) if target_aligned_len else ""
        ),
        "read_names": seen_names,
    }
    return rows, summary


def write_per_call_tsv(out_path: Path, rows: list[dict]) -> None:
    if not rows:
        out_path.write_text("# no chimeric reads supporting this call\n")
        return
    cols = list(rows[0].keys())
    with out_path.open("w") as fh:
        fh.write("#" + "\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--calls", required=True, type=Path, help="calls TSV (samplesheet)")
    p.add_argument("--target-contig", required=True, type=str, help="target contig name (HTLV1, EBV, BCR, etc.)")
    p.add_argument("--output-dir", required=True, type=Path, help="run directory; per-call TSVs land in <output-dir>/per_integration")
    p.add_argument("--bam-dir", type=Path, default=None, help="optional dir to resolve relative BAM paths in calls TSV")
    p.add_argument("--flanking-bp", type=int, default=1000, help="half-window around host_pos for samtools view region")
    p.add_argument("--strict-preflight", action="store_true", help="fail (rather than warn) on missing -Y / stale .bai")
    p.add_argument("--log-dir", type=Path, default=None, help="log directory (default: <output-dir>/../logs)")
    args = p.parse_args()

    log_dir = args.log_dir or (args.output_dir.parent / "logs")
    log_path = setup_logging(log_dir)
    log = logging.getLogger(__name__)
    t0 = time.time()
    log.info(f"=== extract_chimeric_reads.py | log: {log_path} ===")
    log.info(f"target_contig={args.target_contig} flanking_bp={args.flanking_bp} calls={args.calls}")

    out_dir = args.output_dir
    per_int_dir = out_dir / "per_integration"
    summary_tsv = out_dir / "cohort_chimeric_read_summary.tsv"
    per_int_dir.mkdir(parents=True, exist_ok=True)

    calls = parse_calls_tsv(args.calls)
    log.info(f"Loaded {len(calls)} calls from {args.calls}")
    if not calls:
        log.error("No calls parsed — abort.")
        sys.exit(1)

    # Preflight every distinct BAM once to fail fast on misconfiguration.
    seen_bams: set[Path] = set()
    for c in calls:
        for key in ("tumor_bam", "normal_bam"):
            v = c.get(key)
            if not v:
                continue
            bam = Path(v)
            if not bam.is_absolute() and args.bam_dir:
                bam = args.bam_dir / v
            if bam in seen_bams:
                continue
            seen_bams.add(bam)
            preflight_bam(bam, args.target_contig, log, strict=args.strict_preflight)

    summary_rows: list[dict] = []
    for ig in calls:
        eid = ig["event_id"]
        chrom = ig["host_chrom"]
        pos = ig["host_pos"]
        log.info(f"=== {eid} {chrom}:{pos} (patient={ig['patient']}) ===")

        tumor_bam = Path(ig["tumor_bam"])
        if not tumor_bam.is_absolute() and args.bam_dir:
            tumor_bam = args.bam_dir / ig["tumor_bam"]
        normal_bam_str = ig.get("normal_bam") or ""
        normal_bam = Path(normal_bam_str) if normal_bam_str else None
        if normal_bam and not normal_bam.is_absolute() and args.bam_dir:
            normal_bam = args.bam_dir / normal_bam_str

        t_rows, t_sum = extract_for_bam(
            tumor_bam, chrom, pos, args.target_contig, "tumor", args.flanking_bp
        )
        log.info(
            f"  tumor: {t_sum['n_chimeric_reads']} chimeric reads | "
            f"breakpoint median={t_sum['breakpoint_median']}, MAD={t_sum['breakpoint_mad_bp']} bp"
        )
        write_per_call_tsv(per_int_dir / f"{eid}.chimeric_reads.tumor.tsv", t_rows)

        n_sum = {"n_chimeric_reads": 0, "read_names": set(), "breakpoint_median": "", "breakpoint_mad_bp": ""}
        if normal_bam is not None:
            n_rows, n_sum = extract_for_bam(
                normal_bam, chrom, pos, args.target_contig, "normal", args.flanking_bp
            )
            log.info(
                f"  normal: {n_sum['n_chimeric_reads']} chimeric reads | "
                f"breakpoint median={n_sum['breakpoint_median']}, MAD={n_sum['breakpoint_mad_bp']} bp"
            )
            write_per_call_tsv(per_int_dir / f"{eid}.chimeric_reads.normal.tsv", n_rows)

        # Per-call T/N read-name overlap.
        t_names = t_sum["read_names"]
        n_names = n_sum["read_names"] if normal_bam is not None else set()
        overlap = t_names & n_names
        overlap_frac_of_t = (len(overlap) / len(t_names)) if t_names else 0.0
        if normal_bam is not None:
            log.info(
                f"  T/N read-name overlap: {len(overlap)} reads "
                f"({overlap_frac_of_t:.3f} of tumor chimeric reads also in normal)"
            )

        summary_rows.append(
            {
                "event_id": eid,
                "patient": ig["patient"],
                "host_chrom": chrom,
                "host_pos": pos,
                "svlen_bp": ig.get("svlen_bp", ""),
                "provirus_class": ig.get("provirus_class", ""),
                "strict_somatic": ig.get("strict_somatic", ""),
                "caller_vaf": ig.get("caller_vaf", ""),
                "tumor_chimeric_reads": t_sum["n_chimeric_reads"],
                "tumor_breakpoint_median": t_sum["breakpoint_median"],
                "tumor_breakpoint_mad_bp": t_sum["breakpoint_mad_bp"],
                "tumor_target_mapq_median": t_sum["target_mapq_median"],
                "tumor_target_aligned_len_median_bp": t_sum["target_aligned_len_median_bp"],
                "normal_chimeric_reads": n_sum["n_chimeric_reads"] if normal_bam else "",
                "normal_breakpoint_median": n_sum.get("breakpoint_median", "") if normal_bam else "",
                "normal_breakpoint_mad_bp": n_sum.get("breakpoint_mad_bp", "") if normal_bam else "",
                "tn_overlap_reads": len(overlap) if normal_bam else "",
                "tn_overlap_frac_of_tumor": (
                    f"{overlap_frac_of_t:.3f}" if (normal_bam and t_names) else ""
                ),
            }
        )

    cols = list(summary_rows[0].keys())
    with summary_tsv.open("w") as fh:
        fh.write("#" + "\t".join(cols) + "\n")
        for r in summary_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
    log.info(f"Wrote cohort summary: {summary_tsv}")

    elapsed = time.time() - t0
    log.info(f"Completed in {elapsed:.1f} s")
    log.info(f"=== DONE: {Path(__file__).name} completed successfully ===")


if __name__ == "__main__":
    main()
