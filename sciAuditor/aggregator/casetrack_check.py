#!/usr/bin/env python3
"""sciAuditor — casetrack-integration checker (ROADMAP #1, round 1).

Reads a casetrack project (``casetrack.toml`` + ``provenance.jsonl``) and
an inferred-script YAML; emits 4-tuple findings the aggregator can append
to that script's ``audit_findings.tsv``.

See ``sciAuditor/05_casetrack_integration_plan.md`` for the design.

Author: Samuel Ahuno / sciAuditor
Date:   2026-05-17
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

import yaml


# ----- data model ---------------------------------------------------------

@dataclass
class LevelDecl:
    name: str            # "patient" | "specimen" | "assay"
    key: str             # e.g. "assay_id"
    parent: str | None
    parent_key: str | None
    columns: dict[str, dict]   # col_name -> {type, required?, unique?, enum?}


@dataclass
class AnalysisDecl:
    name: str                  # the [analyses.X] section name
    level: str                 # "patient" | "specimen" | "assay"
    column_prefix: str         # e.g. "modkit"
    summary_tsv: str           # e.g. "modkit_summary.tsv"
    extras: dict = field(default_factory=dict)   # nf_process, etc.


@dataclass
class AppendRecord:
    analysis: str
    level: str
    results_file: str
    results_checksum: str
    timestamp: str
    columns_registered: list[str]   # column names INSERTED (after prefix_rename)
    raw_columns: list[str]          # column names BEFORE prefix_rename (i.e. TSV cols)


@dataclass
class CasetrackIndex:
    project_dir: Path
    schema_v: int                                # per-project revision counter (see feature_supported)
    project_id: str | None
    levels: dict[str, LevelDecl]                 # by level name
    analyses: dict[str, AnalysisDecl]            # by analysis name
    appends_latest: dict[tuple[str, str], AppendRecord]   # (analysis, results_file) -> latest
    analyses_seen: set[str]                      # union of declared + registered names
    features: set[str] = field(default_factory=set)       # detected via TOML section presence


# Feature → minimum casetrack tool version it implies (informational only).
# The CHECK is always TOML-section presence, never schema_v.
KNOWN_FEATURES = {
    "qc":          "0.4+",   # [qc] section (QC/censoring subsystem)
    "layout":      "0.5+",   # [layout] / [layout.path_templates] (tool-first results)
    "project_id":  "0.6+",   # [project].project_id (project identity layer)
    "id_pattern":  "0.6+",   # per-level [levels.<level>].id_pattern (regex validation)
}


def feature_supported(index: CasetrackIndex, feature: str) -> bool:
    """True iff the casetrack project at `index` declares this feature in its
    TOML. Use this for rule dispatch instead of `schema_v` — schema_v is a
    per-project revision counter (bumps on every `schema apply`), not a
    casetrack tool-version stamp. Two projects on the same casetrack version
    can have wildly different schema_v values.

    Feature names are in KNOWN_FEATURES. Future rules that only make sense
    against e.g. v0.6+ id-pattern validation should gate on
    `feature_supported(index, "id_pattern")`, not `index.schema_v >= 3`.
    """
    return feature in index.features


def _detect_features(toml_data: dict, levels: dict[str, LevelDecl]) -> set[str]:
    """Inspect a parsed casetrack.toml dict and return the set of feature
    flags it implies (via section presence)."""
    feats: set[str] = set()
    if "qc" in toml_data:
        feats.add("qc")
    layout = toml_data.get("layout") or {}
    if layout or layout.get("path_templates"):
        feats.add("layout")
    project = toml_data.get("project") or {}
    if project.get("project_id"):
        feats.add("project_id")
    # id_pattern is per-level; trigger if ANY level declares one
    for lname, ldata in (toml_data.get("levels") or {}).items():
        if isinstance(ldata, dict) and ldata.get("id_pattern"):
            feats.add("id_pattern")
            break
    return feats


# ----- loader -------------------------------------------------------------

def load_index(project_dir: Path) -> CasetrackIndex:
    """Parse casetrack.toml + stream provenance.jsonl into a CasetrackIndex."""
    project_dir = project_dir.resolve()
    toml_path = project_dir / "casetrack.toml"
    prov_path = project_dir / "provenance.jsonl"
    if not toml_path.exists():
        raise FileNotFoundError(f"casetrack.toml not found in {project_dir}")

    with toml_path.open("rb") as f:
        toml_data = tomllib.load(f)

    project = toml_data.get("project", {})
    schema_v = int(project.get("schema_v", 0))
    project_id = project.get("project_id")

    levels: dict[str, LevelDecl] = {}
    for lname, ldata in (toml_data.get("levels") or {}).items():
        cols_section = ldata.get("columns") or {}
        # ldata may also contain {key, parent, parent_key} as siblings of [columns]
        # but tomllib gives the columns subtable under "columns" key
        levels[lname] = LevelDecl(
            name=lname,
            key=ldata.get("key", f"{lname}_id"),
            parent=ldata.get("parent"),
            parent_key=ldata.get("parent_key"),
            columns=dict(cols_section),
        )

    analyses: dict[str, AnalysisDecl] = {}
    for aname, adata in (toml_data.get("analyses") or {}).items():
        analyses[aname] = AnalysisDecl(
            name=aname,
            level=adata.get("level", "assay"),
            column_prefix=adata.get("column_prefix", ""),
            summary_tsv=adata.get("summary_tsv", ""),
            extras={k: v for k, v in adata.items()
                    if k not in ("level", "column_prefix", "summary_tsv")},
        )

    appends_latest: dict[tuple[str, str], AppendRecord] = {}
    registered_names: set[str] = set()
    if prov_path.exists():
        with prov_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("action") != "append":
                    continue
                analysis = entry.get("analysis")
                results_file = entry.get("results_file")
                checksum = entry.get("results_checksum") or ""
                timestamp = entry.get("timestamp") or ""
                if not analysis or not results_file:
                    continue
                registered_names.add(analysis)
                prefix_rename = entry.get("prefix_rename") or {}
                # raw_columns = keys of prefix_rename; columns_registered = values
                raw_cols = list(prefix_rename.keys())
                reg_cols = list(prefix_rename.values())
                # later entries overwrite earlier ones (we want LATEST per pair)
                rec = AppendRecord(
                    analysis=analysis, level=entry.get("level") or "",
                    results_file=results_file,
                    results_checksum=checksum, timestamp=timestamp,
                    columns_registered=reg_cols, raw_columns=raw_cols,
                )
                key = (analysis, results_file)
                prev = appends_latest.get(key)
                if (prev is None) or (timestamp > prev.timestamp):
                    appends_latest[key] = rec

    analyses_seen = set(analyses.keys()) | registered_names
    features = _detect_features(toml_data, levels)

    return CasetrackIndex(
        project_dir=project_dir,
        schema_v=schema_v,
        project_id=project_id,
        levels=levels,
        analyses=analyses,
        appends_latest=appends_latest,
        analyses_seen=analyses_seen,
        features=features,
    )


# ----- finding type -------------------------------------------------------

@dataclass
class Finding:
    severity: str   # "BLOCKER" | "WARNING" | "NOTE"
    rule:     str
    sites:    str   # comma-sep sites: "site:42" or "results:path" or analysis name
    note:     str

    def as_tsv_row(self) -> str:
        return "\t".join((self.severity, self.rule, self.sites, self.note))


# ----- rules --------------------------------------------------------------

def rule_fk_mismatch(append_info: dict, index: CasetrackIndex,
                     matched_output: dict | None,
                     resolved_results_cols: list[str] | None) -> list[Finding]:
    """C2 BLOCKER: summary TSV col 1 must equal the level's key.
    Resolved when we can recover the TSV's written columns from the
    inferred YAML (resolved_results_cols).

    Round-2: when an output for this --results IS found but the column
    list can't be inferred (most non-trivial cases), emit NOTE rather than
    silent-skip — that way the rule isn't invisible on un-resolvable cases.
    """
    out: list[Finding] = []
    analysis = append_info.get("analysis") or ""
    if analysis not in index.analyses:
        return out  # orphan-analysis handles this separately
    decl = index.analyses[analysis]
    level = index.levels.get(decl.level)
    if level is None:
        return out
    if resolved_results_cols:
        col1 = resolved_results_cols[0]
        if col1 != level.key:
            out.append(Finding(
                severity="BLOCKER",
                rule="casetrack-fk-mismatch",
                sites=f"analysis:{analysis}",
                note=(f"Summary TSV first column '{col1}' != level key "
                      f"'{level.key}' for level '{decl.level}'. "
                      f"casetrack append will refuse the INSERT."),
            ))
        return out
    # Cols unresolved. Emit NOTE only if we know the script does write to
    # this --results file (matched_output is not None) — otherwise we have
    # no business commenting on an unrelated --analysis.
    if matched_output is not None:
        out.append(Finding(
            severity="NOTE",
            rule="casetrack-fk-mismatch",
            sites=f"analysis:{analysis}",
            note=(f"Couldn't infer column list for the summary TSV written "
                  f"by this script. casetrack expects col 1 = "
                  f"'{level.key}' (level '{decl.level}'); the auditor can't "
                  f"verify that statically. Round-3 will tighten this when "
                  f"more dataframe-write patterns are recognised."),
        ))
    return out


def rule_filename_mismatch(append_info: dict, index: CasetrackIndex) -> list[Finding]:
    """C2 WARNING: --results basename must match [analyses.X].summary_tsv."""
    out: list[Finding] = []
    analysis = append_info.get("analysis") or ""
    results = append_info.get("results") or ""
    if not analysis or not results:
        return out
    if analysis not in index.analyses:
        return out
    decl = index.analyses[analysis]
    if not decl.summary_tsv:
        return out  # nothing declared; skip
    got = Path(results).name
    if got != decl.summary_tsv:
        out.append(Finding(
            severity="WARNING",
            rule="casetrack-filename-mismatch",
            sites=f"analysis:{analysis}",
            note=(f"--results basename '{got}' != declared "
                  f"[analyses.{analysis}].summary_tsv = '{decl.summary_tsv}'"),
        ))
    return out


def rule_prefix_collision(append_info: dict, index: CasetrackIndex,
                          resolved_results_cols: list[str] | None) -> list[Finding]:
    """C2 WARNING: <column_prefix>_<col> must not collide with a
    pre-declared column at the analysis's level."""
    out: list[Finding] = []
    analysis = append_info.get("analysis") or ""
    if analysis not in index.analyses or not resolved_results_cols:
        return out
    decl = index.analyses[analysis]
    level = index.levels.get(decl.level)
    if level is None:
        return out
    prefix = decl.column_prefix or ""
    declared_cols = set(level.columns.keys())
    for raw_col in resolved_results_cols[1:]:   # skip col 1 (level key)
        if not raw_col:
            continue
        # casetrack only prefix-renames cols whose name doesn't already start with prefix
        # (heuristic — exact rule lives in casetrack itself; this catches the common case)
        prefixed = (f"{prefix}_{raw_col}"
                    if prefix and not raw_col.startswith(f"{prefix}_")
                    else raw_col)
        if prefixed in declared_cols and prefixed != level.key:
            out.append(Finding(
                severity="WARNING",
                rule="casetrack-prefix-collision",
                sites=f"analysis:{analysis}",
                note=(f"Resulting column '{prefixed}' (from raw '{raw_col}') "
                      f"collides with a pre-declared column at "
                      f"[levels.{decl.level}].columns"),
            ))
    return out


def rule_results_drift(append_info: dict, index: CasetrackIndex) -> list[Finding]:
    """provenance WARNING: disk md5 of --results differs from the
    results_checksum stored in the latest append entry for this pair."""
    out: list[Finding] = []
    analysis = append_info.get("analysis") or ""
    results = append_info.get("results") or ""
    if not analysis or not results:
        return out
    rec = index.appends_latest.get((analysis, results))
    if rec is None:
        return out  # never registered yet; nothing to drift from
    p = Path(results)
    if not p.exists():
        out.append(Finding(
            severity="NOTE",
            rule="casetrack-results-missing",
            sites=f"results:{results}",
            note=(f"--results file does not exist on disk; last registered "
                  f"checksum was {rec.results_checksum} at {rec.timestamp}"),
        ))
        return out
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    disk = h.hexdigest()
    if disk != rec.results_checksum:
        out.append(Finding(
            severity="WARNING",
            rule="casetrack-results-drift",
            sites=f"results:{results}",
            note=(f"Disk md5 {disk} != last-registered "
                  f"{rec.results_checksum} (registered {rec.timestamp}). "
                  f"DB row for analysis '{analysis}' is stale w.r.t. the "
                  f"summary TSV on disk."),
        ))
    return out


def rule_orphan_analysis(append_info: dict, index: CasetrackIndex) -> list[Finding]:
    """NOTE: --analysis X used by a script but X is neither declared in
    [analyses.X] nor seen in provenance.jsonl. Likely typo."""
    out: list[Finding] = []
    analysis = append_info.get("analysis") or ""
    if not analysis:
        return out
    if analysis in index.analyses_seen:
        return out
    declared_names = ", ".join(sorted(index.analyses.keys())) or "(none)"
    out.append(Finding(
        severity="NOTE",
        rule="casetrack-orphan-analysis",
        sites=f"analysis:{analysis}",
        note=(f"--analysis '{analysis}' is not declared in "
              f"[analyses.X] and has never been registered. "
              f"Declared analyses: {declared_names}"),
    ))
    return out


# ----- per-script glue ----------------------------------------------------

def find_output_for_append(append_info: dict, inferred_yaml: dict) -> dict | None:
    """Return the inferred output whose path_template's basename matches the
    append's --results, or None when no output matches."""
    results = append_info.get("results") or ""
    if not results:
        return None
    target_basename = Path(results).name
    for o in (inferred_yaml.get("outputs") or []):
        path_template = (o.get("path_template") or o.get("path") or "")
        if not path_template:
            continue
        if Path(path_template).name == target_basename:
            return o
        if path_template.endswith(target_basename):
            return o
    return None


def resolve_results_cols(matched_output: dict | None,
                         inferred_yaml: dict) -> list[str] | None:
    """Return the columns of the dataframe that fed `matched_output`, or None
    when the link or columns can't be confidently inferred.

    Round-2: relies on the parser-emitted `written_by` field linking each
    output to a dataframe id. The dataframe must also carry a `columns`
    field (set in the parser only where statically resolvable). When
    `columns` is missing or `written_by` is None/missing, return None and
    rule_fk_mismatch will emit NOTE instead of BLOCKER.
    """
    if matched_output is None:
        return None
    df_id = matched_output.get("written_by")
    if not df_id:
        return None
    for df in (inferred_yaml.get("dataframes") or []):
        if df.get("id") == df_id:
            cols = df.get("columns")
            if cols:
                return [str(c) for c in cols]
            return None
    return None


def check_script(inferred_yaml: dict, index: CasetrackIndex) -> list[Finding]:
    """Apply all casetrack rules to one script's inferred YAML."""
    findings: list[Finding] = []
    appends = (inferred_yaml.get("casetrack_appends") or [])
    for ap in appends:
        matched_output = find_output_for_append(ap, inferred_yaml)
        cols = resolve_results_cols(matched_output, inferred_yaml)
        findings.extend(rule_orphan_analysis(ap, index))
        findings.extend(rule_filename_mismatch(ap, index))
        findings.extend(rule_fk_mismatch(ap, index, matched_output, cols))
        findings.extend(rule_prefix_collision(ap, index, cols))
        findings.extend(rule_results_drift(ap, index))
    return findings


# ----- standalone CLI (testing) -------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="sciAuditor casetrack-integration checker (standalone test mode).")
    ap.add_argument("--casetrack-project", required=True, type=Path,
                    help="path to a casetrack project directory")
    ap.add_argument("--inferred-yaml", required=True, type=Path,
                    help="path to one script's analysis.inferred.yaml")
    ap.add_argument("--output", "-o", default="-",
                    help="findings TSV (4 cols, no header). '-' for stdout.")
    args = ap.parse_args()

    if not args.inferred_yaml.exists():
        print(f"inferred-yaml not found: {args.inferred_yaml}", file=sys.stderr)
        return 2
    try:
        index = load_index(args.casetrack_project)
    except FileNotFoundError as e:
        print(f"casetrack load failed: {e}", file=sys.stderr)
        return 2

    with args.inferred_yaml.open() as f:
        inferred = yaml.safe_load(f) or {}

    findings = check_script(inferred, index)
    out_lines = [f.as_tsv_row() for f in findings]

    if args.output == "-":
        for line in out_lines:
            print(line)
    else:
        Path(args.output).write_text("\n".join(out_lines) + ("\n" if out_lines else ""))

    # exit 1 if any BLOCKER, 0 otherwise (for ad-hoc CI)
    return 1 if any(f.severity == "BLOCKER" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
